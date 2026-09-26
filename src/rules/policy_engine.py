"""Warranty rule validation (SRS xxv). Deterministic, config-driven, explainable.

Each check in CHECKS returns (fired, message). Whether a fired rule is a hard
fail, a manual-review trigger or a warning is decided by the category policy
file (policies/*.json), never here. Rules that pass are reported too, so the
decision explanation can list "rules passed" as the SRS requires.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.rules.policy_store import RULE_CATALOG, RULE_NAMES, get_policy

SEVERITY_OF_LIST = {"hard_fail_rules": "hard_fail", "manual_review_rules": "manual_review",
                    "warning_rules": "warning"}


@dataclass
class RuleResult:
    rule_id: str
    title: str
    severity: str          # hard_fail | manual_review | warning
    fired: bool
    message: str


@dataclass
class RuleReport:
    policy_name: str
    category: str
    results: list = field(default_factory=list)

    def _fired(self, severity: str) -> list:
        return [r for r in self.results if r.fired and r.severity == severity]

    @property
    def hard_fails(self):
        return self._fired("hard_fail")

    @property
    def manual_triggers(self):
        return self._fired("manual_review")

    @property
    def warnings(self):
        return self._fired("warning")

    @property
    def passed(self):
        return [r for r in self.results if not r.fired]

    @property
    def overall(self) -> str:
        if self.hard_fails:
            return "FAIL"
        if self.manual_triggers or self.warnings:
            return "REVIEW"
        return "PASS"

    def to_dict(self) -> dict:
        return {"policy_name": self.policy_name, "category": self.category, "overall": self.overall,
                "results": [asdict(r) for r in self.results]}


# ------------------------------------------------------------------ checks
# f = claim facts (see src/core/features.py), p = category policy
def _overdue(f):
    return -int(f["days_to_expiry"])


def _warranty_expired(f, p):
    over = _overdue(f)
    if over > p["grace_period_days"]:
        return True, f"Warranty ended {over} days before the claim; grace period is {p['grace_period_days']} days."
    return False, "Claim is inside the warranty period or its grace period."


def _grace_period(f, p):
    over = _overdue(f)
    if 0 < over <= p["grace_period_days"]:
        return True, f"Claim filed {over} days after expiry, inside the {p['grace_period_days']}-day grace period."
    return False, "Claim is not in the grace-period window."


def _ending_soon(f, p):
    days = int(f["days_to_expiry"])
    if 0 <= days <= 14:
        return True, f"Warranty ends {days} days after the claim date."
    return False, "Warranty is not about to end."


def _unauthorized_repair(f, p):
    if int(f["unauthorized_repair_flag"]):
        return True, "Repair history includes work by an unauthorised service center."
    return False, "All previous repairs were done by authorised centers."


def _excluded(f, p):
    return f["damage_type"] in set(p.get("excluded_damage_types", []))


def _excluded_damage(f, p):
    thr = p["exclusion_min_diagnostic_confidence"]
    if _excluded(f, p) and float(f["diagnostic_confidence"]) >= thr:
        return True, (f"'{f['damage_type']}' is excluded for {p['category']} and the diagnosis confirms it "
                      f"({float(f['diagnostic_confidence']):.2f} ≥ {thr:.2f}).")
    return False, f"Damage cause '{f['damage_type']}' is not a confirmed exclusion."


def _excluded_unconfirmed(f, p):
    thr = p["exclusion_min_diagnostic_confidence"]
    if _excluded(f, p) and float(f["diagnostic_confidence"]) < thr:
        return True, (f"'{f['damage_type']}' is excluded for {p['category']}, but diagnostic confidence "
                      f"{float(f['diagnostic_confidence']):.2f} is below {thr:.2f}. A reviewer must confirm the cause.")
    return False, "No unconfirmed exclusion."


def _serial_mismatch(f, p):
    if not int(f["serial_number_match"]) and int(f["has_receipt"]) and int(f["has_serial_photo"]):
        return True, "Registered serial number differs from the one on the receipt and serial photo."
    return False, "Serial number is consistent with the evidence."


def _serial_unverified(f, p):
    if not int(f["serial_number_match"]) and not (int(f["has_receipt"]) and int(f["has_serial_photo"])):
        return True, "Serial number mismatch reported, but receipt or serial photo is missing to confirm it."
    return False, "No unverifiable serial mismatch."


def _late_reporting(f, p):
    if int(f["claim_date_conflict_flag"]):
        return False, "Reporting window not assessed: claim dates conflict (see contradictions)."
    delay, limit = int(f["reporting_delay_days"]), p["claim_reporting_period_days"]
    if delay > limit:
        return True, f"Fault reported {delay} days after it occurred; the policy allows {limit} days."
    return False, f"Fault reported {delay} days after it occurred (limit {limit})."


def _near_deadline(f, p):
    delay, limit = int(f["reporting_delay_days"]), p["claim_reporting_period_days"]
    if limit - 7 < delay <= limit and not int(f["claim_date_conflict_flag"]):
        return True, f"Reported on day {delay} of a {limit}-day reporting window."
    return False, "Reported well inside the reporting window."


def _uncovered_fault(f, p):
    covered = p.get("covered_faults", [])
    if covered and f.get("fault_category") not in covered:
        return True, f"'{f.get('fault_category')}' is not on the covered-fault list for {p['category']}."
    return False, f"'{f.get('fault_category')}' is a covered fault."


def _unknown_cause(f, p):
    if f["damage_type"] == "Unknown / Not Sure" and float(f["diagnostic_confidence"]) < 0.5:
        return True, "Cause is unknown and the diagnosis is inconclusive."
    return False, "Cause of damage is identified."


def _repeat_repairs(f, p):
    n, thr = int(f["previous_repairs_count"]), p["repeat_repair_review_threshold"]
    if n >= thr:
        return True, f"{n} previous repairs on record (review threshold {thr})."
    return False, f"{n} previous repair(s), below the review threshold of {thr}."


def _prior_replacement(f, p):
    detail = (f.get("previous_replacement_details") or "").strip()
    if detail and detail.lower() not in {"none", "no", "n/a", "-"}:
        return True, f"Product was previously replaced: {detail}"
    return False, "No earlier replacement of this unit."


def _supporting_missing(f, p):
    flag = {"warranty_card": "has_warranty_card", "serial_photo": "has_serial_photo",
            "damage_photo": "has_damage_photo", "receipt": "has_receipt"}
    return [d for d in p.get("supporting_documents", []) if d in flag and not int(f[flag[d]])]


def _incomplete_evidence(f, p):
    gone = _supporting_missing(f, p)
    if len(gone) >= 2:
        return True, f"{len(gone)} supporting documents are missing ({', '.join(d.replace('_', ' ') for d in gone)})."
    return False, "Supporting evidence is sufficient."


def _supporting_document_missing(f, p):
    gone = _supporting_missing(f, p)
    if len(gone) == 1:
        return True, f"The {gone[0].replace('_', ' ')} is missing; uploading it speeds up the claim."
    return False, "No single supporting document is missing." if not gone else "See incomplete-evidence rule."


CHECKS = {
    "WARRANTY_EXPIRED": _warranty_expired,
    "GRACE_PERIOD": _grace_period,
    "WARRANTY_ENDING_SOON": _ending_soon,
    "UNAUTHORIZED_REPAIR": _unauthorized_repair,
    "EXCLUDED_DAMAGE": _excluded_damage,
    "EXCLUDED_DAMAGE_UNCONFIRMED": _excluded_unconfirmed,
    "SERIAL_MISMATCH": _serial_mismatch,
    "SERIAL_UNVERIFIED": _serial_unverified,
    "LATE_REPORTING": _late_reporting,
    "NEAR_REPORTING_DEADLINE": _near_deadline,
    "UNCOVERED_FAULT": _uncovered_fault,
    "UNKNOWN_CAUSE": _unknown_cause,
    "REPEAT_REPAIRS": _repeat_repairs,
    "PRIOR_REPLACEMENT": _prior_replacement,
    "INCOMPLETE_EVIDENCE": _incomplete_evidence,
    "SUPPORTING_DOCUMENT_MISSING": _supporting_document_missing,
}
assert set(CHECKS) == set(RULE_CATALOG) == set(RULE_NAMES), "every catalogued rule needs a check and a name"


def evaluate(facts: dict) -> RuleReport:
    """Run every enabled rule of the claim's category policy against the facts."""
    policy = get_policy(facts["product_category"])
    report = RuleReport(policy_name=policy["policy_name"], category=policy["category"])
    for list_name, severity in SEVERITY_OF_LIST.items():
        for rule_id in policy.get(list_name, []):
            fired, message = CHECKS[rule_id](facts, policy)
            report.results.append(RuleResult(rule_id, RULE_NAMES[rule_id], severity, bool(fired), message))
    return report
