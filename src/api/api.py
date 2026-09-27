"""JSON endpoints for live UI parts. Every response uses the envelope in src/api/errors.py."""
from __future__ import annotations

import base64
import json
import time
from datetime import date, timedelta
from pathlib import Path

from flask import Blueprint, request

from src.api.errors import ErrorCode, fail, ok
from src.app_security import limiter
from src.core import features as feature_builder
from src.core.pipeline import run as run_pipeline
from src.models.entities import Claim
from src.security.guards import authorize_object, require
from src.services import verdict

SAMPLES = Path(__file__).resolve().parent.parent.parent / "sample_claims"
# The landing page's live bench may run exactly these sample records (valid, invalid, boundary).
DEMO_CASES = {"valid": "01_valid_claim.json", "invalid": "02_invalid_claim.json", "boundary": "10_boundary_date_claim.json"}

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/claims/<string:claim_id>/evaluation")
@require("claim.read")
def claim_evaluation(claim_id):
    """Stored verdict payload (never re-runs a model), or the pending stages while evaluation runs."""
    claim = authorize_object("claim.read", Claim.query.filter_by(claim_id=claim_id).first_or_404())
    return ok(verdict.api_payload(claim))


def demo_facts(case: str) -> tuple[dict, dict]:
    """Feature record of an allow-listed sample claim, with the dates the card prints filled in."""
    sample = json.loads((SAMPLES / DEMO_CASES[case]).read_text())
    facts = dict(sample["record"])
    purchased = date.fromisoformat(facts["purchase_date"])
    facts["claim_submission_date"] = (purchased + timedelta(days=int(facts["product_age_days"]))).isoformat()
    facts["fault_occurrence_date"] = (date.fromisoformat(facts["claim_submission_date"])
                                      - timedelta(days=int(facts["reporting_delay_days"]))).isoformat()
    feature_builder.validate(facts)
    return facts, sample


@api_bp.post("/demo/evaluate")
@limiter.limit("10/minute")
def demo_evaluate():
    """Public: run the real pipeline on one allow-listed sample claim. Writes nothing to the database."""
    case = (request.get_json(silent=True) or {}).get("case")
    if case not in DEMO_CASES:
        return fail(ErrorCode.VALIDATION_FAILED, fields={"case": f"Choose one of: {', '.join(DEMO_CASES)}."})
    started = time.perf_counter()
    facts, sample = demo_facts(case)
    missing = [] if facts["has_receipt"] else ["receipt"]
    empty_findings = {"findings": [], "date_conflict": False, "serial_mismatch": False, "serials_seen": []}
    out = run_pipeline(facts, contradictions=empty_findings, duplicates={"indicators": []}, missing=missing,
                       preprocess_ms=round((time.perf_counter() - started) * 1000), claim_id=facts["claim_id"])
    payload = out["payload"]
    payload["total_ms"] = round((time.perf_counter() - started) * 1000)
    payload["gtm"]["card_url"] = "data:image/png;base64," + base64.b64encode(out["card_bytes"]).decode()
    return ok({"case": case, "title": sample["title"], "payload": payload, "meter": verdict.meter(payload)})
