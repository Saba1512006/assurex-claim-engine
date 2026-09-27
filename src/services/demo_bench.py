"""The landing page's live bench: three allow-listed sample claims run through the real pipeline.

`evaluate(case)` runs the pipeline now (the "Run the checks again" button, /api/demo/evaluate).
`cached()` holds one result per sample, computed once per installed model version, so the page can show a
real decided claim on first paint without running the models on every page view. Nothing is written to the
database either way.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import date, timedelta
from pathlib import Path

from src.core import features as feature_builder
from src.core.pipeline import run as run_pipeline
from src.services import verdict

SAMPLES = Path(__file__).resolve().parent.parent.parent / "sample_claims"
# key: (sample file, short label for the segmented control, one-line description)
CASES = {
    "valid": ("01_valid_claim.json", "Clean fault", "Laptop motherboard failure, 7 months old, every document on file"),
    "invalid": ("02_invalid_claim.json", "Liquid damage", "Refrigerator control board, water ingress confirmed by a technician"),
    "boundary": ("10_boundary_date_claim.json", "Grace +4 d", "Warranty ended 4 days ago, inside the 7-day grace period"),
}
DECISION_TONE = {"Likely Valid": "valid", "Likely Invalid": "invalid", "Manual Review Required": "review"}
_cache: dict = {}
_lock = threading.Lock()


def facts_for(case: str) -> tuple[dict, dict]:
    """Feature record of a sample claim, with the dates the card prints filled in."""
    sample = json.loads((SAMPLES / CASES[case][0]).read_text())
    facts = dict(sample["record"])
    purchased = date.fromisoformat(facts["purchase_date"])
    facts["claim_submission_date"] = (purchased + timedelta(days=int(facts["product_age_days"]))).isoformat()
    facts["fault_occurrence_date"] = (date.fromisoformat(facts["claim_submission_date"])
                                      - timedelta(days=int(facts["reporting_delay_days"]))).isoformat()
    feature_builder.validate(facts)
    return facts, sample


def evaluate(case: str, explain: bool = True) -> dict:
    """Run the real pipeline on one sample. Returns the stored-verdict payload, the card PNG and the sample."""
    started = time.perf_counter()
    facts, sample = facts_for(case)
    missing = [] if facts["has_receipt"] else ["receipt"]
    empty = {"findings": [], "date_conflict": False, "serial_mismatch": False, "serials_seen": []}
    out = run_pipeline(facts, contradictions=empty, duplicates={"indicators": []}, missing=missing,
                       preprocess_ms=round((time.perf_counter() - started) * 1000), claim_id=facts["claim_id"], explain=explain)
    out["payload"]["total_ms"] = round((time.perf_counter() - started) * 1000)
    return {"payload": out["payload"], "card_bytes": out["card_bytes"], "sample": sample}


def view(case: str, payload: dict) -> dict:
    """What the instrument draws: the same shape for the cached first paint and for a live run."""
    m = verdict.meter(payload)
    cons = payload["consistency"]

    def model(x):
        return {"available": bool(x.get("available")), "predicted": x.get("predicted"), "top": x.get("top")}
    return {
        "case": case, "short": CASES[case][1], "desc": CASES[case][2],
        "decision": {k: payload["decision"].get(k) for k in ("value", "rule_id", "reason")},
        "tone": DECISION_TONE.get(payload["decision"]["value"], "none"),
        "python": model(payload["python"]), "gtm": model(payload["gtm"]),
        "consistency": {"status": cons["status"], "difference": cons.get("difference"), "tone": m["tone"]},
        "stages": [{"name": s["name"], "ms": s["ms"]} for s in payload.get("stages", [])],
        "total_ms": payload.get("total_ms"),
        "meter": {"arc": m["arc"], "tone_var": m["tone_var"], "label": m["label"],
                  "needles": [{k: n[k] for k in ("cls", "angle", "dashed", "value")} for n in m["needles"]]},
    }


def cached() -> dict:
    """{case: view} for all samples, computed once per installed model version (a new model resets it)."""
    from src.web import model_versions
    key = tuple(sorted(model_versions().items()))
    with _lock:
        if _cache.get("key") != key:
            payloads = {case: evaluate(case, explain=False)["payload"] for case in CASES}
            first = next(iter(payloads.values()))
            _cache.clear()
            _cache.update(key=key, views={c: view(c, p) for c, p in payloads.items()},
                          meter=verdict.meter_static(first["consistency"]["thresholds"].get("min_confidence") or 0.6))
        return {"views": _cache["views"], "meter": _cache["meter"]}
