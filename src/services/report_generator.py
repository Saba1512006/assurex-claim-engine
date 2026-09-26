"""Downloadable claim report (SRS xliv).

Contains the claim details, uploaded evidence, warranty status, Python result,
Teachable Machine result, confidence comparison, rule results, contradictions,
duplicate indicators, final recommendation and reviewer comments. Only stored
facts are printed - an absent value is shown as "not available", never invented.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

from src.core.vocab import DOCUMENT_LABELS

FONT_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "fonts"
INK, MUTED, LINE, SOFT = (colors.HexColor(c) for c in ("#0f172a", "#64748b", "#e2e8f0", "#f8fafc"))
TONE = {"Likely Valid": "#047857", "Likely Invalid": "#b91c1c", "Manual Review Required": "#b45309"}

_fonts_ready = False


def _fonts():
    global _fonts_ready
    if not _fonts_ready:
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
        _fonts_ready = True


def _styles():
    base = dict(fontName="DejaVu", textColor=INK, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("t", fontSize=17, leading=21, fontName="DejaVu-Bold", textColor=INK),
        "sub": ParagraphStyle("s", fontSize=9, leading=12, fontName="DejaVu", textColor=MUTED),
        "h": ParagraphStyle("h", fontSize=11, leading=14, fontName="DejaVu-Bold", textColor=INK, spaceBefore=10, spaceAfter=5),
        "b": ParagraphStyle("b", fontSize=8.5, leading=11.5, **base),
        "bb": ParagraphStyle("bb", fontSize=8.5, leading=11.5, fontName="DejaVu-Bold", textColor=INK),
        "m": ParagraphStyle("m", fontSize=7.5, leading=10, fontName="DejaVu", textColor=MUTED),
    }


def _p(text, style):
    return Paragraph(escape("" if text is None else str(text)), style)


def _table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), SOFT))
    t.setStyle(TableStyle(style))
    return t


def _pct(v):
    return "not available" if v is None else f"{v:.1%}"


def build_pdf(claim, upload_dir: Path) -> bytes:
    _fonts()
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=f"Claim report {claim.claim_id}", author="AssureX Claim Engine")
    W = doc.width
    ev, log, product, warranty = claim.model_evaluation, claim.rule_validation, claim.product, claim.warranty
    out = [Paragraph("AssureX claim report", s["title"]),
           Paragraph(escape(f"{claim.claim_id} · generated {datetime.now(timezone.utc):%d %b %Y %H:%M} UTC"), s["sub"]),
           Spacer(1, 6)]

    decision = claim.final_decision or "Not evaluated"
    tone = TONE.get(decision, "#334155")
    out.append(_table([[Paragraph(f'<font color="{tone}"><b>{escape(decision)}</b></font>', s["bb"]),
                        _p(f"Status: {claim.status}", s["b"]), _p(f"Risk: {claim.risk_level or '—'}", s["b"]),
                        _p(f"Rule {claim.decision_rule_id or '—'}: {claim.decision_reason or ''}", s["b"])]],
                       [W * .22, W * .2, W * .13, W * .45], header=False))

    out.append(Paragraph("1. Claim and product", s["h"]))
    rows = [("Customer", claim.claimant.full_name), ("Product", f"{product.product_name} ({product.product_id})"),
            ("Category", product.category), ("Brand / model", f"{product.brand} / {product.model_number}"),
            ("Serial number", product.serial_number), ("Purchase", f"{product.purchase_date:%d %b %Y} · {product.retailer} · {product.purchase_price:,.2f}"),
            ("Invoice", product.invoice_number or "—"), ("Fault", f"{claim.fault_category} — {claim.fault_description}"),
            ("Damage cause", claim.damage_type), ("Fault date", f"{claim.fault_occurrence_date:%d %b %Y}"),
            ("Submitted", f"{claim.claim_submission_date:%d %b %Y}" if claim.claim_submission_date else "Draft"),
            ("Diagnostic confidence", f"{claim.diagnostic_confidence:.2f} ({claim.diagnosis_source})")]
    out.append(_table([[_p(k, s["bb"]), _p(v, s["b"])] for k, v in rows], [W * .25, W * .75], header=False))

    out.append(Paragraph("2. Warranty", s["h"]))
    if warranty:
        out.append(_table([[_p(k, s["bb"]), _p(v, s["b"])] for k, v in (
            ("Provider", warranty.warranty_provider), ("Period", f"{warranty.start_date:%d %b %Y} – {warranty.expiry_date:%d %b %Y}"),
            ("Term", f"{warranty.duration_months} months{' (extended)' if warranty.is_extended else ''}"),
            ("Status today", f"{warranty.status}, {warranty.remaining_days()} days left"))], [W * .25, W * .75], header=False))
    else:
        out.append(_p("No warranty record.", s["b"]))

    out.append(Paragraph("3. Model predictions and comparison", s["h"]))
    if ev:
        def col(avail, cls, scores, version, err):
            if not avail:
                return ["unavailable", "—", "—", "—", err or "—"]
            return [cls, _pct(scores["Valid Claim"]), _pct(scores["Invalid Claim"]), _pct(scores["Manual Review"]), version]
        py = col(ev.python_available, ev.python_predicted_class, ev.python_scores(), ev.python_model_version, ev.model_errors.get("python"))
        gt = col(ev.gtm_available, ev.gtm_predicted_class, ev.gtm_scores(), ev.gtm_model_version, ev.model_errors.get("gtm"))
        labels = ["Predicted class", "P(Valid Claim)", "P(Invalid Claim)", "P(Manual Review)", "Model version"]
        rows = [[_p("", s["bb"]), _p("Python model", s["bb"]), _p("Teachable Machine", s["bb"])]]
        rows += [[_p(l, s["bb"]), _p(a, s["b"]), _p(b, s["b"])] for l, a, b in zip(labels, py, gt)]
        out.append(_table(rows, [W * .26, W * .37, W * .37]))
        diff = "not available" if ev.top_confidence_difference is None else f"{ev.top_confidence_difference:.4f}"
        match = "not available" if ev.is_class_match is None else ("yes" if ev.is_class_match else "no")
        out.append(Spacer(1, 4))
        out.append(_p(f"Classes match: {match} · |top-confidence difference| = {diff} · status: "
                      f"{ev.model_consistency_status} · {ev.thresholds.get('explanation', '')}", s["b"]))
        card = upload_dir / (ev.summary_card_image_path or "")
        if ev.summary_card_image_path and card.exists():
            out.append(Spacer(1, 4))
            out.append(KeepTogether([_p("Claim Summary Card given to the Teachable Machine model:", s["m"]),
                                     Image(str(card), width=62 * mm, height=62 * mm)]))
    else:
        out.append(_p("The claim has not been evaluated yet.", s["b"]))

    out.append(Paragraph("4. Warranty rules", s["h"]))
    if log:
        rows = [[_p(h, s["bb"]) for h in ("Rule", "Severity", "Result", "Detail")]]
        for r in log.rules:
            rows.append([_p(r["title"], s["b"]), _p(r["severity"].replace("_", " "), s["b"]),
                         _p("TRIGGERED" if r["fired"] else "passed", s["bb"] if r["fired"] else s["b"]), _p(r["message"], s["m"])])
        out.append(_table(rows, [W * .3, W * .14, W * .12, W * .44]))
        out.append(Paragraph("5. Contradictions, duplicates and missing documents", s["h"]))
        items = ([f"Contradiction: {c['message']}" for c in log.contradictions] +
                 [f"Duplicate indicator: {d['message']}" for d in log.duplicate_flags] +
                 [f"Missing document: {DOCUMENT_LABELS.get(m, m)}" for m in log.missing_documents])
        out.append(_table([[_p(i, s["b"])] for i in items], [W], header=False) if items else _p("None found.", s["b"]))
    else:
        out.append(_p("Rules have not run yet.", s["b"]))

    out.append(Paragraph("6. Evidence", s["h"]))
    docs = list(claim.documents) + [d for d in product.documents if d.claim_id is None]
    if docs:
        rows = [[_p(h, s["bb"]) for h in ("Type", "File", "SHA-256", "OCR")]]
        rows += [[_p(DOCUMENT_LABELS.get(d.document_type, d.document_type), s["b"]), _p(d.original_filename, s["b"]),
                  _p(d.file_hash_sha256[:24] + "…", s["m"]), _p(d.ocr_status.replace("_", " "), s["b"])] for d in docs]
        out.append(_table(rows, [W * .22, W * .3, W * .32, W * .16]))
    else:
        out.append(_p("No documents uploaded.", s["b"]))

    out.append(Paragraph("7. Reviewer decisions", s["h"]))
    if claim.reviewer_actions:
        rows = [[_p(h, s["bb"]) for h in ("When", "Reviewer", "AI recommendation", "Decision", "Comments / override reason")]]
        rows += [[_p(f"{a.timestamp:%d %b %Y %H:%M}", s["b"]), _p(a.reviewer.full_name, s["b"]),
                  _p(a.previous_recommendation or "—", s["b"]),
                  _p(a.reviewer_decision + (" (override)" if a.is_override else ""), s["bb"] if a.is_override else s["b"]),
                  _p(a.comments + (f" — Override reason: {a.override_reason}" if a.override_reason else ""), s["m"])]
                 for a in claim.reviewer_actions]
        out.append(_table(rows, [W * .15, W * .17, W * .18, W * .16, W * .34]))
    else:
        out.append(_p("No reviewer decision yet.", s["b"]))

    out.append(Spacer(1, 8))
    out.append(_p("Decision produced by the team's Python model, Google Teachable Machine model, warranty rule engine "
                  "and decision table. No external generative-AI service was used to decide this claim.", s["m"]))
    doc.build(out)
    return buf.getvalue()
