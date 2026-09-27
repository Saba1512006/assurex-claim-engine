"""Claim Summary Card v3 — square, image-model-friendly, deterministic.

History:
  * v1 was 640x420 landscape (Teachable Machine centre-crops to a square) and
    used platform fonts. v2 fixed both (600x600, bundled fonts).
  * v2 drew every fact as small grey bars and tiles. Measured with a replica of
    Teachable Machine's trainer (frozen MobileNetV2-0.35 + dense head) and with
    the real Teachable Machine export, it reached only 54-62% test accuracy:
    ImageNet features barely separate thin grey shapes at 224x224.
  * v3 shows each claim fact against its warranty-policy limit as a large,
    colour-coded tile in a fixed 3x3 grid (coverage, reporting time, damage
    cause, receipt, supporting evidence, serial, dates, invoice, repairs).
    Colour and position carry the information; text is kept for people.
  * The card still contains claim facts only: no class, decision, rule outcome
    or model confidence (SRS xx). Limits come from policies/*.json, the same
    source the rule engine uses.
"""
from __future__ import annotations

import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.core.vocab import CATEGORIES

ROOT = Path(__file__).resolve().parent.parent.parent
FONT_DIR = ROOT / "static" / "fonts"
SIZE = 600
CARD_VERSION = "v3"
# Policy limits drawn on the card. Changing one changes the Teachable Machine input: retrain after changing it.
CARD_POLICY_FIELDS = ("grace_period_days", "claim_reporting_period_days", "excluded_damage_types",
                      "exclusion_min_diagnostic_confidence", "repeat_repair_review_threshold")
BG, INK, MUTED, WHITE = (246, 247, 249), (21, 32, 43), (96, 108, 120), (255, 255, 255)
# Tile states. Each state has its own colour AND its own glyph, so colour is never the only cue.
STATE = {"ok": (34, 139, 84), "caution": (222, 146, 18), "fail": (196, 48, 48), "conflict": (112, 72, 190)}
CATEGORY_COLOUR = dict(zip(CATEGORIES, ((37, 99, 235), (13, 148, 136), (120, 113, 108))))
DATE_STYLES = ("%Y-%m-%d", "%d/%m/%Y", "%d %b %Y")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    if not path.exists():
        raise FileNotFoundError(f"Card font missing: {path}. Cards must render identically everywhere.")
    return ImageFont.truetype(str(path), size)


def _fmt(d: str, style: str) -> str:
    from datetime import datetime
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").strftime(style)
    except ValueError:
        return "n/a"


def _policy(category: str) -> dict:
    from src.rules.policy_store import get_policy
    return get_policy(category)


def tiles(r: dict) -> list[tuple[str, str, str]]:
    """(title, detail, state) for the nine fixed tiles, in grid order. Facts vs policy limits only."""
    pol = _policy(r.get("product_category", CATEGORIES[0]))
    grace, period = int(pol["grace_period_days"]), int(pol["claim_reporting_period_days"])
    excluded = set(pol["excluded_damage_types"])
    min_diag, repeat = float(pol["exclusion_min_diagnostic_confidence"]), int(pol["repeat_repair_review_threshold"])

    overdue = -int(r.get("days_to_expiry", 0))
    if overdue <= 0:
        cover = ("Within coverage", f"{-overdue} days left", "ok")
    elif overdue <= grace:
        cover = ("Grace period", f"{overdue} of {grace} grace days", "caution")
    else:
        cover = ("Coverage ended", f"{overdue} days ago (grace {grace})", "fail")
    delay = int(r.get("reporting_delay_days", 0))
    report = ("Reported in time" if delay <= period else "Reported late",
              f"{delay} days · limit {period}", "ok" if delay <= period else "fail")
    damage, diag = r.get("damage_type", ""), float(r.get("diagnostic_confidence", 0.5))
    if damage in excluded:
        cause_state = "fail" if diag >= min_diag else "caution"
    elif damage == "Unknown / Not Sure" and diag < 0.5:
        cause_state = "caution"
    else:
        cause_state = "ok"
    cause = (damage.replace(" / Not Sure", ""), f"{'excluded' if damage in excluded else 'covered'} cause · diag {diag:.2f}",
             cause_state)
    receipt = ("Receipt", "on file" if int(r.get("has_receipt", 0)) else "missing",
               "ok" if int(r.get("has_receipt", 0)) else "fail")
    support_keys = ("has_warranty_card", "has_damage_photo", "has_serial_photo")
    gaps = sum(1 - int(r.get(k, 0)) for k in support_keys)
    support = ("Evidence", f"{3 - gaps} of 3 supporting", ("ok", "caution", "fail", "fail")[gaps])
    if int(r.get("serial_number_match", 1)):
        serial = ("Serial matches", "registered = evidence", "ok")
    elif int(r.get("has_receipt", 0)) and int(r.get("has_serial_photo", 0)):
        serial = ("Serial differs", "receipt + photo disagree", "fail")
    else:
        serial = ("Serial unverified", "evidence incomplete", "caution")
    dates = (("Dates conflict", "fault before purchase", "conflict") if int(r.get("claim_date_conflict_flag", 0))
             else ("Dates consistent", "purchase < fault < claim", "ok"))
    invoice = (("Invoice reused", "seen on another claim", "caution") if int(r.get("duplicate_invoice_flag", 0))
               else ("Invoice unique", "not seen before", "ok"))
    reps = int(r.get("previous_repairs_count", 0))
    if int(r.get("unauthorized_repair_flag", 0)):
        repairs = ("Unauthorised repair", f"{reps} previous repair(s)", "fail")
    elif reps >= repeat:
        repairs = ("Repeat repairs", f"{reps} previous · review at {repeat}", "caution")
    else:
        repairs = ("Repairs", f"{reps} previous", "ok")
    return [cover, report, cause, receipt, support, serial, dates, invoice, repairs]


GRID_X, GRID_Y, TILE_W, TILE_H, GAP = 16, 80, 184, 150, 8


def tile_boxes() -> list[tuple[int, int, int, int]]:
    """(x0, y0, x1, y1) of the nine tiles in grid order; shared by the renderer and the occlusion map."""
    return [(GRID_X + (i % 3) * (TILE_W + GAP), GRID_Y + (i // 3) * (TILE_H + GAP),
             GRID_X + (i % 3) * (TILE_W + GAP) + TILE_W, GRID_Y + (i // 3) * (TILE_H + GAP) + TILE_H) for i in range(9)]


def _glyph(g: ImageDraw.ImageDraw, cx: int, cy: int, state: str) -> None:
    """White glyph per state: check / exclamation / cross / double-headed arrow."""
    w = 7
    if state == "ok":
        g.line([(cx - 16, cy), (cx - 5, cy + 12), (cx + 17, cy - 13)], fill=WHITE, width=w, joint="curve")
    elif state == "caution":
        g.line([(cx, cy - 16), (cx, cy + 5)], fill=WHITE, width=w)
        g.ellipse([cx - 4, cy + 11, cx + 4, cy + 19], fill=WHITE)
    elif state == "fail":
        g.line([(cx - 13, cy - 13), (cx + 13, cy + 13)], fill=WHITE, width=w)
        g.line([(cx - 13, cy + 13), (cx + 13, cy - 13)], fill=WHITE, width=w)
    else:
        g.line([(cx - 16, cy), (cx + 16, cy)], fill=WHITE, width=w)
        g.polygon([(cx - 20, cy), (cx - 9, cy - 10), (cx - 9, cy + 10)], fill=WHITE)
        g.polygon([(cx + 20, cy), (cx + 9, cy - 10), (cx + 9, cy + 10)], fill=WHITE)


def render_card(r: dict, variation: int = 0) -> Image.Image:
    """variation 0 = canonical (used for val/test/live); >0 = training augmentation."""
    rnd = random.Random(f"{r.get('claim_id', '')}-{variation}")
    jitter = (lambda c: tuple(max(0, min(255, v + rnd.randint(-10, 10))) for v in c)) if variation else (lambda c: c)
    date_style = DATE_STYLES[variation % len(DATE_STYLES)]
    img = Image.new("RGB", (SIZE, SIZE), jitter(BG))
    g = ImageDraw.Draw(img)
    f_h, f_s, f_d = _font(22, True), _font(13), _font(11)

    cat = r.get("product_category", "")
    g.rectangle([0, 0, SIZE, 10], fill=jitter(CATEGORY_COLOUR.get(cat, MUTED)))     # category band
    g.text((20, 22), "Claim summary", font=f_h, fill=INK)
    g.text((20, 52), f"{r.get('claim_id', '')}  ·  {cat}  ·  {r.get('fault_category', '')}", font=f_s, fill=MUTED)

    for (title, detail, state), (x, y, _, _) in zip(tiles(r), tile_boxes()):
        tw, th = TILE_W, TILE_H
        colour = jitter(STATE[state])
        g.rounded_rectangle([x, y, x + tw, y + th], radius=14, fill=colour)
        _glyph(g, x + tw // 2, y + 50, state)
        for text, size, bold, ty in ((title, 15, True, y + 92), (detail, 11, False, y + 118)):
            font = _font(size, bold)
            while g.textlength(text, font=font) > tw - 14 and size > 9:     # shrink to fit, never truncate
                size -= 1
                font = _font(size, bold)
            g.text((x + tw / 2 - g.textlength(text, font=font) / 2, ty), text, font=font, fill=WHITE)

    g.text((20, 556), f"Purchased {_fmt(r.get('purchase_date', ''), date_style)}  ·  claim "
                      f"{_fmt(r.get('claim_submission_date', ''), date_style)}", font=f_s, fill=MUTED)
    g.text((20, 578), "Claim facts vs policy limits. Contains no model output or decision.", font=f_d, fill=MUTED)

    if variation > 0:                                   # label-preserving augmentation
        img = img.rotate(rnd.uniform(-1.5, 1.5), resample=Image.BICUBIC, fillcolor=jitter(BG))
        if rnd.random() < 0.5:
            img = img.filter(ImageFilter.GaussianBlur(rnd.uniform(0.2, 0.8)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=rnd.randint(55, 90))
        img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    return img
