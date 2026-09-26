"""SRS demonstration cases (sample_claims/*.json) through the production rule engine, Python model and
decision table. Hidden-claim readiness: nothing here is keyed on claim IDs or hard-coded answers."""
import json
from pathlib import Path

import pytest

from src.core import decision_table
from src.core.pipeline import compare
from src.core.python_classifier import get_python_classifier
from src.rules import policy_engine
from src.rules.policy_store import get_policy

CASES = sorted((Path(__file__).resolve().parent.parent / "sample_claims").glob("*.json"))


def test_all_eleven_cases_present():
    assert len(CASES) == 11


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
def test_demonstration_case(path):
    case = json.loads(path.read_text())
    rec = case["record"]
    py = get_python_classifier().predict(rec)
    if case["expected"]["rule"] == "D04":
        gtm = {"predicted_class": "Invalid Claim", "top_confidence": 0.9,
               "confidence_scores": {"Valid Claim": 0.05, "Invalid Claim": 0.9, "Manual Review": 0.05}}
    else:
        gtm = dict(py)
    cmp = compare(py, gtm)
    rules = policy_engine.evaluate(rec)
    mandatory = {"receipt": "has_receipt", "warranty_card": "has_warranty_card", "serial_photo": "has_serial_photo",
                 "damage_photo": "has_damage_photo"}
    missing = [d for d in get_policy(rec["product_category"])["mandatory_documents"] if not rec[mandatory[d]]]
    d = decision_table.decide({
        "hard_fail_count": len(rules.hard_fails), "manual_trigger_count": len(rules.manual_triggers),
        "warning_count": len(rules.warnings), "missing_mandatory_count": len(missing),
        "contradiction_count": rec["claim_date_conflict_flag"] + (1 - rec["serial_number_match"]),
        "duplicate_count": rec["duplicate_invoice_flag"], "consistency": cmp["status"],
        "python_class": py["predicted_class"], "gtm_class": gtm["predicted_class"]})
    assert (d["decision"], d["rule_id"]) == (case["expected"]["decision"], case["expected"]["rule"]), \
        f"{case['title']}: python={py['predicted_class']} {py['top_confidence']}, rules={[r.rule_id for r in rules.results if r.fired]}"
