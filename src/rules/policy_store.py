"""Warranty policies: one JSON file per product category (SRS xxvi).

The JSON files are the single source of truth for coverage, grace periods,
reporting deadlines, exclusions and mandatory documents. The rule engine, the
dataset generator and the admin policy editor all read them through this module,
so they can never disagree. Every load is validated against src/core/vocab.py.
"""
from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path

from src.core.vocab import CATEGORIES, DAMAGE_TYPES, DOCUMENT_LABELS, FAULTS

POLICY_DIR = Path(__file__).resolve().parent.parent.parent / "policies"
FILES = {
    "Consumer Electronics": "consumer_electronics.json",
    "Home Appliances": "home_appliances.json",
    "Industrial Tools": "industrial_tools.json",
}
# Fields an administrator may edit from the UI, with their type and allowed range.
EDITABLE = {
    "coverage_duration_months": (int, 1, 120),
    "grace_period_days": (int, 0, 90),
    "claim_reporting_period_days": (int, 1, 365),
    "exclusion_min_diagnostic_confidence": (float, 0.0, 1.0),
    "repeat_repair_review_threshold": (int, 1, 10),
}


# Every rule the engine knows. Its severity comes from the list a policy puts it in
# (hard_fail_rules / manual_review_rules / warning_rules); a rule in no list is off.
RULE_CATALOG = {
    "WARRANTY_EXPIRED": "Claim filed after the warranty and its grace period ended",
    "GRACE_PERIOD": "Claim filed inside the post-expiry grace period",
    "WARRANTY_ENDING_SOON": "Warranty ends within 14 days of the claim",
    "UNAUTHORIZED_REPAIR": "Product was repaired by an unauthorised service center",
    "EXCLUDED_DAMAGE": "Damage cause is excluded by the policy and confirmed by diagnosis",
    "EXCLUDED_DAMAGE_UNCONFIRMED": "Damage cause is excluded but the diagnosis is not conclusive",
    "SERIAL_MISMATCH": "Serial number differs from the receipt and serial photo",
    "SERIAL_UNVERIFIED": "Serial number mismatch that the evidence cannot confirm",
    "LATE_REPORTING": "Fault reported after the policy's reporting deadline",
    "NEAR_REPORTING_DEADLINE": "Fault reported in the last week before the deadline",
    "UNCOVERED_FAULT": "Fault is not in the policy's list of covered faults",
    "UNKNOWN_CAUSE": "Cause unknown and diagnostic confidence below 0.50",
    "REPEAT_REPAIRS": "Product has reached the repeat-repair review threshold",
    "PRIOR_REPLACEMENT": "Product was already replaced once under warranty",
    "INCOMPLETE_EVIDENCE": "Two or more supporting documents are missing",
    "SUPPORTING_DOCUMENT_MISSING": "One supporting document is missing",
}
# Neutral check names shown next to a pass/fail result (the catalog text describes the failure).
RULE_NAMES = {
    "WARRANTY_EXPIRED": "Warranty in force", "GRACE_PERIOD": "Grace-period claim",
    "WARRANTY_ENDING_SOON": "Warranty end date", "UNAUTHORIZED_REPAIR": "Authorised repairs only",
    "EXCLUDED_DAMAGE": "Damage cause covered", "EXCLUDED_DAMAGE_UNCONFIRMED": "Exclusion confirmed by diagnosis",
    "SERIAL_MISMATCH": "Serial number matches evidence", "SERIAL_UNVERIFIED": "Serial number verifiable",
    "LATE_REPORTING": "Reported within deadline", "NEAR_REPORTING_DEADLINE": "Reporting margin",
    "UNCOVERED_FAULT": "Fault on covered list", "UNKNOWN_CAUSE": "Cause identified",
    "REPEAT_REPAIRS": "Repair history", "PRIOR_REPLACEMENT": "No earlier replacement",
    "INCOMPLETE_EVIDENCE": "Supporting evidence", "SUPPORTING_DOCUMENT_MISSING": "Every supporting document",
}
SEVERITY_LISTS = ("hard_fail_rules", "manual_review_rules", "warning_rules")


class PolicyError(ValueError):
    """Raised when a policy file is missing or inconsistent with the vocabulary."""


def validate(policy: dict) -> dict:
    cat = policy.get("category")
    if cat not in CATEGORIES:
        raise PolicyError(f"Unknown category {cat!r}")
    for key, (typ, lo, hi) in EDITABLE.items():
        if key not in policy:
            raise PolicyError(f"{cat}: missing {key}")
        val = policy[key]
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not lo <= val <= hi:
            raise PolicyError(f"{cat}: {key} must be between {lo} and {hi}")
    bad = set(policy.get("excluded_damage_types", [])) - set(DAMAGE_TYPES)
    if bad:
        raise PolicyError(f"{cat}: excluded_damage_types not in vocabulary: {sorted(bad)}")
    bad = set(policy.get("covered_faults", [])) - set(FAULTS[cat])
    if bad:
        raise PolicyError(f"{cat}: covered_faults not in vocabulary: {sorted(bad)}")
    seen = []
    for lst in SEVERITY_LISTS:
        ids = policy.get(lst, [])
        unknown = set(ids) - set(RULE_CATALOG)
        if unknown:
            raise PolicyError(f"{cat}: {lst} has unknown rule ids {sorted(unknown)}")
        seen += ids
    if len(seen) != len(set(seen)):
        raise PolicyError(f"{cat}: a rule id appears in more than one severity list")
    for lst in ("mandatory_documents", "supporting_documents"):
        bad = set(policy.get(lst, [])) - set(DOCUMENT_LABELS)
        if bad:
            raise PolicyError(f"{cat}: unknown document types in {lst}: {sorted(bad)}")
    if set(policy.get("mandatory_documents", [])) & set(policy.get("supporting_documents", [])):
        raise PolicyError(f"{cat}: a document cannot be both mandatory and supporting")
    return policy


@lru_cache(maxsize=None)
def _load(category: str) -> dict:
    path = POLICY_DIR / FILES[category]
    if not path.exists():
        raise PolicyError(f"Policy file missing: {path.name}")
    return validate(json.loads(path.read_text(encoding="utf-8")))


def get_policy(category: str) -> dict:
    """Policy for a category (accepts legacy names such as 'Industrial & Automotive Tools')."""
    from src.core.vocab import normalise_category
    cat = category if category in CATEGORIES else normalise_category(category)
    return dict(_load(cat))


def all_policies() -> dict:
    return {c: get_policy(c) for c in CATEGORIES}


def excluded_damage(category: str) -> set:
    return set(get_policy(category).get("excluded_damage_types", []))


def mandatory_documents(category: str) -> tuple:
    return tuple(get_policy(category).get("mandatory_documents", ()))


def supporting_documents(category: str) -> tuple:
    return tuple(get_policy(category).get("supporting_documents", ()))


def reload() -> None:
    _load.cache_clear()


def save_policy(category: str, updates: dict) -> dict:
    """Validate and atomically write edited fields back to the category's JSON file."""
    policy = get_policy(category)
    for key, raw in updates.items():
        if key == "excluded_damage_types":
            policy[key] = [d for d in DAMAGE_TYPES if d in set(raw)]
            continue
        if key == "rule_severity":                      # {rule_id: hard_fail|manual_review|warning|off}
            for lst in SEVERITY_LISTS:
                policy[lst] = []
            for rid in RULE_CATALOG:
                sev = raw.get(rid, "off")
                if sev != "off":
                    if f"{sev}_rules" not in SEVERITY_LISTS:
                        raise PolicyError(f"Unknown severity {sev!r}")
                    policy[f"{sev}_rules"].append(rid)
            continue
        if key not in EDITABLE:
            raise PolicyError(f"{key} is not editable")
        typ = EDITABLE[key][0]
        try:
            policy[key] = typ(raw)
        except (TypeError, ValueError):
            raise PolicyError(f"{key} must be a number") from None
    validate(policy)
    path = POLICY_DIR / FILES[policy["category"]]
    fd, tmp = tempfile.mkstemp(dir=str(POLICY_DIR), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(policy, indent=2) + "\n")
    os.replace(tmp, path)
    reload()
    return policy
