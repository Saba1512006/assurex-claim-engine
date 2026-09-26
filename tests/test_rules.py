"""Rule engine, policy files and the SRS 'surprise modification' scenarios (boundary + negative cases)."""
import json
import shutil

import pytest

from src.core import decision_table
from src.core.vocab import DATE_FORMATS, parse_date
from src.rules import policy_engine, policy_store
from src.rules.policy_store import PolicyError


def facts(**kw):
    base = dict(product_category="Consumer Electronics", damage_type="Manufacturing Defect",
                fault_category="Motherboard failure", previous_replacement_details="", days_to_expiry=200,
                reporting_delay_days=3, diagnostic_confidence=0.8, previous_repairs_count=0,
                unauthorized_repair_flag=0, serial_number_match=1, has_receipt=1, has_warranty_card=1,
                has_damage_photo=1, has_serial_photo=1, claim_date_conflict_flag=0)
    base.update(kw)
    return base


def fired(report):
    return {r.rule_id: r.severity for r in report.results if r.fired}


def test_clean_claim_passes_every_rule():
    rep = policy_engine.evaluate(facts())
    assert fired(rep) == {} and rep.overall == "PASS"
    assert len(rep.results) == len(policy_store.RULE_CATALOG)


@pytest.mark.parametrize("days_to_expiry,expected", [
    (0, {"WARRANTY_ENDING_SOON": "warning"}),        # last day of cover
    (-1, {"GRACE_PERIOD": "manual_review"}),          # first day of grace
    (-7, {"GRACE_PERIOD": "manual_review"}),          # last day of 7-day grace (Consumer Electronics)
    (-8, {"WARRANTY_EXPIRED": "hard_fail"}),          # first day after grace
])
def test_warranty_boundaries(days_to_expiry, expected):
    assert fired(policy_engine.evaluate(facts(days_to_expiry=days_to_expiry))) == expected


@pytest.mark.parametrize("delay,expected", [
    (23, {}), (24, {"NEAR_REPORTING_DEADLINE": "warning"}), (30, {"NEAR_REPORTING_DEADLINE": "warning"}),
    (31, {"LATE_REPORTING": "hard_fail"}),
])
def test_reporting_window_boundaries(delay, expected):
    assert fired(policy_engine.evaluate(facts(reporting_delay_days=delay))) == expected


def test_late_reporting_not_judged_when_dates_conflict():
    rep = policy_engine.evaluate(facts(reporting_delay_days=200, claim_date_conflict_flag=1))
    assert "LATE_REPORTING" not in fired(rep)


@pytest.mark.parametrize("conf,rule", [(0.55, "EXCLUDED_DAMAGE"), (0.54, "EXCLUDED_DAMAGE_UNCONFIRMED")])
def test_exclusion_needs_diagnosis_to_hard_fail(conf, rule):
    assert rule in fired(policy_engine.evaluate(facts(damage_type="Water Ingress", diagnostic_confidence=conf)))


def test_exclusions_are_per_category():
    """Electrical surge is excluded for electronics but covered for home appliances."""
    assert "EXCLUDED_DAMAGE" in fired(policy_engine.evaluate(facts(damage_type="Electrical Surge")))
    ha = facts(product_category="Home Appliances", fault_category="Motor burnout", damage_type="Electrical Surge")
    assert fired(policy_engine.evaluate(ha)) == {}


@pytest.mark.parametrize("receipt,photo,rule", [(1, 1, "SERIAL_MISMATCH"), (1, 0, "SERIAL_UNVERIFIED"),
                                                (0, 1, "SERIAL_UNVERIFIED")])
def test_serial_mismatch_severity_depends_on_evidence(receipt, photo, rule):
    rep = policy_engine.evaluate(facts(serial_number_match=0, has_receipt=receipt, has_serial_photo=photo))
    assert rule in fired(rep)


def test_evidence_rules():
    assert fired(policy_engine.evaluate(facts(has_warranty_card=0))) == {"SUPPORTING_DOCUMENT_MISSING": "warning"}
    assert "INCOMPLETE_EVIDENCE" in fired(policy_engine.evaluate(facts(has_warranty_card=0, has_serial_photo=0)))


def test_other_manual_review_rules():
    assert "UNAUTHORIZED_REPAIR" in fired(policy_engine.evaluate(facts(unauthorized_repair_flag=1)))
    assert "REPEAT_REPAIRS" in fired(policy_engine.evaluate(facts(previous_repairs_count=2)))
    assert "UNKNOWN_CAUSE" in fired(policy_engine.evaluate(facts(damage_type="Unknown / Not Sure", diagnostic_confidence=0.4)))
    assert "PRIOR_REPLACEMENT" in fired(policy_engine.evaluate(facts(previous_replacement_details="Replaced in May")))
    assert "UNCOVERED_FAULT" in fired(policy_engine.evaluate(facts(fault_category="Screen cracked")))


def test_all_three_policies_are_valid_and_complete():
    pols = policy_store.all_policies()
    assert len(pols) == 3
    for p in pols.values():
        for key in ("category", "coverage_duration_months", "start_conditions", "covered_faults", "exclusions",
                    "claim_reporting_period_days", "repair_conditions", "authorized_service_center_required",
                    "replacement_conditions", "grace_period_days", "mandatory_documents", "hard_fail_rules",
                    "warning_rules", "manual_review_rules"):
            assert p[key] not in (None, "", []), f"{p['category']} is missing {key} (SRS deliverable 7)"


def test_policy_validation_rejects_bad_files():
    p = policy_store.get_policy("Home Appliances")
    with pytest.raises(PolicyError):
        policy_store.validate({**p, "excluded_damage_types": ["Alien Attack"]})
    with pytest.raises(PolicyError):
        policy_store.validate({**p, "grace_period_days": -1})
    with pytest.raises(PolicyError):
        policy_store.validate({**p, "warning_rules": ["WARRANTY_EXPIRED"]})     # in two severity lists


@pytest.fixture()
def policy_sandbox(tmp_path, monkeypatch):
    """Point the policy store at a copy of policies/ so surprise modifications don't touch the repo."""
    shutil.copytree(policy_store.POLICY_DIR, tmp_path / "policies")
    monkeypatch.setattr(policy_store, "POLICY_DIR", tmp_path / "policies")
    policy_store.reload()
    yield tmp_path / "policies"
    policy_store.reload()


def test_surprise_add_warranty_exclusion(policy_sandbox):
    before = fired(policy_engine.evaluate(facts(product_category="Home Appliances", fault_category="Motor burnout",
                                                damage_type="Mechanical Stress")))
    assert before == {}
    p = policy_store.get_policy("Home Appliances")
    policy_store.save_policy("Home Appliances", {"excluded_damage_types": p["excluded_damage_types"] + ["Mechanical Stress"]})
    after = fired(policy_engine.evaluate(facts(product_category="Home Appliances", fault_category="Motor burnout",
                                               damage_type="Mechanical Stress")))
    assert after == {"EXCLUDED_DAMAGE": "hard_fail"}
    assert "Mechanical Stress" in json.loads((policy_sandbox / "home_appliances.json").read_text())["excluded_damage_types"]


def test_surprise_change_rule_severity(policy_sandbox):
    sev = {rid: "off" for rid in policy_store.RULE_CATALOG}
    sev.update({"UNAUTHORIZED_REPAIR": "manual_review", "WARRANTY_EXPIRED": "hard_fail"})
    policy_store.save_policy("Consumer Electronics", {"rule_severity": sev})
    assert fired(policy_engine.evaluate(facts(unauthorized_repair_flag=1))) == {"UNAUTHORIZED_REPAIR": "manual_review"}


def test_surprise_change_confidence_threshold(tmp_path, monkeypatch):
    from src.core import consistency
    path = tmp_path / "decision_policy.json"
    shutil.copy(decision_table.POLICY_PATH, path)
    monkeypatch.setattr(consistency, "CONFIG", path)
    policy = decision_table.load_policy(path)
    assert consistency.consistency_status("Valid Claim", 0.62, "Valid Claim", 0.62)[0] == "Strong Match"
    policy["consistency"]["min_confidence"] = 0.7
    decision_table.save_policy(policy, path)
    assert consistency.consistency_status("Valid Claim", 0.62, "Valid Claim", 0.62)[0] == "Uncertain Result"


def test_decision_policy_save_rejects_invalid(tmp_path):
    path = tmp_path / "decision_policy.json"
    shutil.copy(decision_table.POLICY_PATH, path)
    policy = decision_table.load_policy(path)
    policy["consistency"]["strong_max_diff"] = 0.5       # bigger than acceptable -> invalid
    with pytest.raises(ValueError):
        decision_table.save_policy(policy, path)
    assert decision_table.load_policy(path)["consistency"]["strong_max_diff"] == 0.10   # file untouched


def test_surprise_modify_decision_logic():
    policy = decision_table.load_policy()
    policy["routing"]["Likely Invalid"] = "Manual Review"          # e.g. "a human confirms every rejection"
    facts_ = dict(hard_fail_count=1, contradiction_count=0, duplicate_count=0, missing_mandatory_count=0,
                  manual_trigger_count=0, warning_count=0, consistency="Strong Match",
                  python_class="Invalid Claim", gtm_class="Invalid Claim")
    d = decision_table.decide(facts_, policy)
    assert d["decision"] == "Likely Invalid" and policy["routing"][d["decision"]] == "Manual Review"


def test_surprise_support_another_date_format(monkeypatch):
    import src.core.vocab as vocab
    with pytest.raises(ValueError):
        parse_date("2026.09.26")
    monkeypatch.setattr(vocab, "DATE_FORMATS", DATE_FORMATS + ("%Y.%m.%d",))
    assert str(vocab.parse_date("2026.09.26")) == "2026-09-26"


def test_unknown_fact_in_decision_table_fails_loudly():
    policy = decision_table.load_policy()
    policy["decision_table"][0]["when"] = {"any": [["no_such_fact", ">", 0]]}
    with pytest.raises(KeyError):
        decision_table.decide({"hard_fail_count": 0}, policy)
