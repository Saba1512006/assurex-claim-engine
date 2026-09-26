"""Claim Summary Card v2 — square, image-model-friendly, deterministic.

Why v2:
  * v1 was 640x420 landscape; Teachable Machine centre-crops uploads to a
    square, silently cutting off both side columns. v2 is 600x600.
  * v1 used Windows-only fonts and fell back to PIL's bitmap font on Linux, so
    cards rendered on the server differed from the training cards (skew).
    v2 ships its fonts in static/fonts and fails loudly if they are missing.
  * A CNN cannot read 12px text. v2 encodes every feature as a fixed-position
    visual (bars, filled/hollow tiles, pips) and keeps the text for humans.
  * Contains claim facts only: no prediction, confidence or decision (SRS xx).
"""
from __future__ import annotations

import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.core.vocab import CATEGORIES, DAMAGE_TYPES

ROOT = Path(__file__).resolve().parent.parent.parent
FONT_DIR = ROOT / "static" / "fonts"
SIZE = 600
THEMES = {
    "light": {"bg": (244, 246, 248), "ink": (21, 32, 43), "muted": (104, 116, 128), "line": (206, 212, 218),
              "fill": (21, 32, 43), "track": (226, 230, 234), "accent": (14, 124, 123)},
    "dark": {"bg": (24, 30, 38), "ink": (236, 240, 244), "muted": (150, 160, 170), "line": (60, 70, 82),
             "fill": (236, 240, 244), "track": (48, 57, 68), "accent": (80, 196, 190)},
}
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


def render_card(r: dict, variation: int = 0) -> Image.Image:
    """variation 0 = canonical (used for val/test/live); >0 = training augmentation."""
    rnd = random.Random(f"{r.get('claim_id', '')}-{variation}")
    # Same polarity for every card: inverting colours (v1 dark/light) destroys what an
    # image model learns. Variations change tint, date format, rotation, blur, JPEG.
    theme = dict(THEMES["light"])
    if variation > 0:
        t = rnd.randint(-8, 8)
        theme["bg"] = tuple(max(0, min(255, c + t)) for c in theme["bg"])
    date_style = DATE_STYLES[variation % len(DATE_STYLES)]
    img = Image.new("RGB", (SIZE, SIZE), theme["bg"])
    g = ImageDraw.Draw(img)
    f_h, f_s, f_b, f_t = _font(22, True), _font(13), _font(14, True), _font(11)
    ink, muted, line, track, fill = theme["ink"], theme["muted"], theme["line"], theme["track"], theme["fill"]

    g.text((28, 24), "Claim summary", font=f_h, fill=ink)
    # category as a fixed-position pip strip (exclusions differ per category)
    cat = r.get("product_category", "")
    for i, name in enumerate(CATEGORIES):
        box = [500 + i * 26, 30, 518 + i * 26, 48]
        g.rectangle(box, fill=fill) if name == cat else g.rectangle(box, outline=line, width=2)
    g.text((28, 54), f"{r.get('claim_id', '')}  ·  {r.get('product_category', '')}", font=f_s, fill=muted)
    g.line([(28, 80), (572, 80)], fill=line, width=1)

    def bar(y: int, label: str, value: float, marker: float | None = None, caption: str = "") -> None:
        g.text((28, y), label, font=f_b, fill=ink)
        g.text((572 - g.textlength(caption, font=f_s), y + 1), caption, font=f_s, fill=muted)
        g.rounded_rectangle([28, y + 24, 572, y + 44], radius=4, fill=track)
        w = int(544 * max(0.0, min(1.0, value)))
        if w:
            g.rounded_rectangle([28, y + 24, 28 + w, y + 44], radius=4, fill=fill)
        if marker is not None:
            x = 28 + int(544 * marker)
            g.line([(x, y + 18), (x, y + 50)], fill=theme["accent"], width=3)

    cover = max(1, int(round(r.get("warranty_duration_months", 12) * 30.44)))
    age = int(r.get("product_age_days", 0))
    horizon = cover * 1.5                              # bar spans 150% of coverage; marker = expiry
    bar(96, "Warranty life used", age / horizon, cover / horizon,
        f"{age} d of {cover} d · expires {_fmt(r.get('warranty_expiry_date', ''), date_style)}")
    delay = int(r.get("reporting_delay_days", 0))
    bar(160, "Reporting delay", delay / 90, 30 / 90, f"{delay} days after fault")
    diag = float(r.get("diagnostic_confidence", 0))
    bar(224, "Diagnostic confidence", diag, None, f"{diag:.2f}")

    g.text((28, 288), "Evidence", font=f_b, fill=ink)
    docs = [("Receipt", "has_receipt"), ("Warranty card", "has_warranty_card"),
            ("Damage photo", "has_damage_photo"), ("Serial photo", "has_serial_photo"),
            ("Repair report", "has_repair_report")]
    for i, (name, key) in enumerate(docs):
        x = 28 + i * 110
        box = [x, 312, x + 100, 356]
        if int(r.get(key, 0)):
            g.rounded_rectangle(box, radius=6, fill=fill)
            g.text((x + 50 - g.textlength(name, font=f_t) / 2, 327), name, font=f_t, fill=theme["bg"])
        else:                                             # hollow + hatch = missing
            g.rounded_rectangle(box, radius=6, outline=ink, width=2)
            for k in range(0, 100, 10):
                g.line([(x + k, 356), (x + k + 12, 312)], fill=line, width=1)
            g.text((x + 50 - g.textlength(name, font=f_t) / 2, 327), name, font=f_t, fill=ink)

    g.text((28, 376), "Integrity signals", font=f_b, fill=ink)
    flags = [("Serial matches", int(r.get("serial_number_match", 1)) == 1),
             ("Dates consistent", int(r.get("claim_date_conflict_flag", 0)) == 0),
             ("Authorised repairs", int(r.get("unauthorized_repair_flag", 0)) == 0),
             ("Invoice unique", int(r.get("duplicate_invoice_flag", 0)) == 0)]
    for i, (name, ok) in enumerate(flags):
        x = 28 + (i % 2) * 272
        y = 402 + (i // 2) * 38
        if ok:
            g.ellipse([x, y, x + 22, y + 22], fill=fill)
        else:
            g.ellipse([x, y, x + 22, y + 22], outline=ink, width=3)
            g.line([(x + 4, y + 4), (x + 18, y + 18)], fill=ink, width=3)
        g.text((x + 32, y + 3), name if ok else name.replace("matches", "differs").replace("consistent", "conflict")
               .replace("Authorised", "Unauthorised").replace("unique", "reused"), font=f_s, fill=ink)

    reps = int(r.get("previous_repairs_count", 0))
    g.text((28, 488), "Previous repairs", font=f_b, fill=ink)
    for i in range(4):
        box = [180 + i * 30, 488, 200 + i * 30, 508]
        g.rectangle(box, fill=fill) if i < reps else g.rectangle(box, outline=line, width=2)
    damage = r.get("damage_type", "")
    g.text((28, 518), "Damage cause", font=f_b, fill=ink)
    for i, name in enumerate(DAMAGE_TYPES):                # one fixed slot per cause
        box = [180 + i * 30, 518, 200 + i * 30, 538]
        g.rectangle(box, fill=fill) if name == damage else g.rectangle(box, outline=line, width=2)
    g.text((396, 520), damage, font=f_s, fill=ink)
    g.text((28, 548), f"Fault: {r.get('fault_category', '')}  ·  purchased "
                      f"{_fmt(r.get('purchase_date', ''), date_style)}", font=f_s, fill=muted)
    g.text((28, 576), "Claim facts only. Contains no model output or decision.", font=_font(11), fill=muted)

    if variation > 0:                                   # label-preserving augmentation
        img = img.rotate(rnd.uniform(-1.5, 1.5), resample=Image.BICUBIC, fillcolor=theme["bg"])
        if rnd.random() < 0.5:
            img = img.filter(ImageFilter.GaussianBlur(rnd.uniform(0.2, 0.8)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=rnd.randint(55, 90))
        img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    return img
