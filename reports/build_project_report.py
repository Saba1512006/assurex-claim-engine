"""Build reports/AssureX_Project_Report.pdf from documentation/PROJECT_REPORT.md.

    python reports/build_project_report.py

The Markdown file is the single source; this renders headings, paragraphs, bullet lists, tables and the
diagram images (documentation/diagrams/*.png) with ReportLab and the bundled DejaVu fonts.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (Image, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

from src.services.report_generator import _fonts  # noqa: E402

SRC = ROOT / "documentation" / "PROJECT_REPORT.md"
OUT = ROOT / "reports" / "AssureX_Project_Report.pdf"
INK, MUTED, LINE, SOFT, BRAND = (colors.HexColor(c) for c in ("#0f172a", "#64748b", "#e2e8f0", "#f1f5f9", "#1d5bd8"))


def styles():
    return {
        "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=24, leading=30, textColor=INK, spaceAfter=6),
        "sub": ParagraphStyle("sub", fontName="DejaVu", fontSize=11, leading=15, textColor=MUTED),
        "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=13.5, leading=18, textColor=BRAND, spaceBefore=12, spaceAfter=6),
        "p": ParagraphStyle("p", fontName="DejaVu", fontSize=9.4, leading=13.6, textColor=INK, spaceAfter=5),
        "cell": ParagraphStyle("cell", fontName="DejaVu", fontSize=7.8, leading=10, textColor=INK),
        "head": ParagraphStyle("head", fontName="DejaVu-Bold", fontSize=7.8, leading=10, textColor=INK),
    }


def inline(text: str) -> str:
    """Markdown inline -> ReportLab mini-HTML (bold, italics, code, links)."""
    t = escape(text.replace("\\|", "|"))
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r'<font name="DejaVu" color="#1447b3">\1</font>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    return t


def table(lines, s, width):
    rows = [[c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))] for ln in lines]
    rows = [r for i, r in enumerate(rows) if i != 1]            # drop the |---| separator
    ncol = max(len(r) for r in rows)
    data = [[Paragraph(inline(c), s["head"] if i == 0 else s["cell"]) for c in r + [""] * (ncol - len(r))]
            for i, r in enumerate(rows)]
    # column widths proportional to content length (clamped), so "#" columns stay narrow
    # and never narrower than the longest single word, so IDs and numbers are not broken mid-token
    lens = [min(60, max(4, max(len(r[c]) if c < len(r) else 0 for r in rows))) for c in range(ncol)]
    words = [min(40, max((len(w) for r in rows if c < len(r) for w in r[c].split()), default=0) + 2) for c in range(ncol)]
    lens = [max(n, w) for n, w in zip(lens, words)]
    widths = [width * n / sum(lens) for n in lens]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def image(path: Path, width):
    from PIL import Image as PIL
    w, h = PIL.open(path).size
    scale = min(width / w, (230 * mm) / h)
    return Image(str(path), width=w * scale, height=h * scale)


def build() -> Path:
    _fonts()
    s = styles()
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title="AssureX Claim Engine — Project Report",
                            author="AssureX team")
    W = doc.width
    story, lines, i = [], SRC.read_text(encoding="utf-8").splitlines(), 0
    bullets = []

    def flush_bullets():
        if bullets:
            story.append(ListFlowable([ListItem(Paragraph(inline(b), s["p"]), leftIndent=10) for b in bullets],
                                      bulletType="bullet", start="•", leftIndent=12))
            bullets.clear()

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            flush_bullets()
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            story += [table(block, s, W), Spacer(1, 6)]
            continue
        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", ln.strip())
        if m:
            flush_bullets()
            story += [image((SRC.parent / m.group(1)).resolve(), W), Spacer(1, 6)]
        elif ln.startswith("# "):
            story += [Spacer(1, 60), Paragraph(inline(ln[2:]), s["title"])]
        elif ln.startswith("## "):
            flush_bullets()
            if story and ln.startswith("## 1. "):
                story.append(PageBreak())
            story.append(Paragraph(inline(ln[3:]), s["h2"]))
        elif re.match(r"^(\*|-|\d+\.) ", ln.strip()):
            item = re.sub(r"^(\*|-|\d+\.) ", "", ln.strip())
            while i + 1 < len(lines) and lines[i + 1].startswith("  ") and lines[i + 1].strip():
                i += 1                                   # wrapped continuation of the same bullet
                item += " " + lines[i].strip()
            bullets.append(item)
        elif ln.strip():
            flush_bullets()
            para = [ln.strip()]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||!\[|\* |- |\d+\. )", lines[i + 1].strip()):
                i += 1
                para.append(lines[i].strip())
            story.append(Paragraph(inline(" ".join(para)), s["sub"] if len(story) == 2 else s["p"]))
        else:
            flush_bullets()
        i += 1
    flush_bullets()

    def footer(canvas, d):
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 9 * mm, "AssureX Claim Engine — Project Report")
        canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Page {d.page}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUT


if __name__ == "__main__":
    print("written", build())
