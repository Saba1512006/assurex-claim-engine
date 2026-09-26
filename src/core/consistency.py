"""Model consistency status (SRS xxiv). Thresholds come from config, never literals."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "decision_policy.json"


def thresholds() -> dict:
    return json.loads(CONFIG.read_text())["consistency"]


def consistency_status(py_cls: str, py_conf: float, gtm_cls: str, gtm_conf: float, t: dict | None = None):
    """Return (status, |py_top - gtm_top|). Order matters and is documented:
    low confidence first (an unsure agreement is not a match), then class conflict,
    then the size of the confidence gap."""
    t = t or thresholds()
    diff = round(abs(py_conf - gtm_conf), 4)
    if min(py_conf, gtm_conf) < t["min_confidence"]:
        return "Uncertain Result", diff
    if py_cls != gtm_cls:
        return "Model Disagreement", diff
    if diff <= t["strong_max_diff"]:
        return "Strong Match", diff
    if diff <= t["acceptable_max_diff"]:
        return "Acceptable Match", diff
    return "Weak Match", diff
