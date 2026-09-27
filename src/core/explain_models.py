"""Per-claim explanations for both models, computed once at evaluation time and stored with the result.

Python model — feature occlusion: each input is replaced by its typical training value (median for numbers,
most common value for flags and categories) and the change in the predicted class's probability is measured.
A positive value means the claim's actual value pushed the model TOWARD its prediction.

Teachable Machine — tile occlusion: each of the nine tiles on the Claim Summary Card is painted over with the
card background and the image model is re-run. The drop in the predicted class's probability says how much
that tile drove the prediction. This shows what the image model actually looked at.

Both use only the saved models; nothing is retrained and no external service is called.
"""
from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd
from PIL import ImageDraw

from src.core.card_v2 import BG, tile_boxes, tiles
from src.core.features import BINARY, CATEGORICAL, MODEL_FEATURES, NUMERIC

ROOT = Path(__file__).resolve().parent.parent.parent
TRAIN = ROOT / "data" / "splits" / "train.csv"
LABELS = {
    "purchase_price": "Purchase price", "warranty_duration_months": "Warranty length (months)",
    "product_age_days": "Product age (days)", "days_to_expiry": "Days to warranty end",
    "reporting_delay_days": "Days from fault to claim", "diagnostic_confidence": "Diagnostic confidence",
    "previous_repairs_count": "Previous repairs", "missing_document_count": "Missing documents",
    "is_extended_warranty": "Extended warranty", "has_receipt": "Receipt on file", "has_warranty_card": "Warranty card on file",
    "has_damage_photo": "Damage photo on file", "has_serial_photo": "Serial photo on file",
    "has_repair_report": "Repair report on file", "serial_number_match": "Serial matches evidence",
    "unauthorized_repair_flag": "Unauthorised repair", "duplicate_invoice_flag": "Invoice used before",
    "claim_date_conflict_flag": "Dates conflict", "product_category": "Product category", "damage_type": "Damage cause",
}


@functools.lru_cache(maxsize=1)
def baseline() -> dict:
    """Typical training value per feature (train split only, so no test information leaks in)."""
    df = pd.read_csv(TRAIN)
    out = {f: float(df[f].median()) for f in NUMERIC}
    out.update({f: df[f].mode().iloc[0] for f in BINARY + CATEGORICAL})
    return out


def _show(feature: str, value) -> str:
    if feature in BINARY:
        return "yes" if int(value) else "no"
    if isinstance(value, float) and not float(value).is_integer():
        return f"{value:.2f}"
    return str(int(value)) if isinstance(value, float) else str(value)


def python_contributions(facts: dict, pipeline, classes: list, predicted: str, top_n: int = 3) -> list[dict]:
    base = baseline()
    rows = [{f: facts[f] for f in MODEL_FEATURES}]
    changed = []
    for f in MODEL_FEATURES:
        if facts[f] == base[f] or (f in NUMERIC and float(facts[f]) == float(base[f])):
            continue
        rows.append({**rows[0], f: base[f]})
        changed.append(f)
    if not changed:
        return []
    probs = pipeline.predict_proba(pd.DataFrame(rows))
    k = list(classes).index(predicted)
    p0 = float(probs[0][k])
    out = [{"feature": f, "label": LABELS[f], "value": _show(f, facts[f]), "typical": _show(f, base[f]),
            "effect": round(p0 - float(probs[i + 1][k]), 4)} for i, f in enumerate(changed)]
    out.sort(key=lambda x: -abs(x["effect"]))
    return [x for x in out[:top_n] if abs(x["effect"]) >= 0.005]


def gtm_occlusion(card, facts: dict, gtm, predicted: str) -> list[dict]:
    p0 = gtm.predict(card)["confidence_scores"][predicted]
    out = []
    for (title, detail, state), box in zip(tiles(facts), tile_boxes()):
        img = card.copy()
        ImageDraw.Draw(img).rectangle(box, fill=BG)
        drop = p0 - gtm.predict(img)["confidence_scores"][predicted]
        out.append({"tile": title, "detail": detail, "state": state, "effect": round(drop, 4)})
    peak = max((abs(t["effect"]) for t in out), default=0) or 1
    for t in out:
        t["weight"] = round(max(t["effect"], 0) / peak, 3)
    return out
