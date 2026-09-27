"""What-if simulator (Admin): replay decisions under proposed consistency thresholds without changing anything.

Two populations:
  * the 225 labelled test claims (reports/model_comparison_test.csv): automation rate and the accuracy of
    automated decisions against the true labels, current versus proposed;
  * the live claims' stored evaluations: which recommendations would change.
Rule outcomes are replayed exactly as stored; only the consistency status and therefore the decision can move.
"""
from __future__ import annotations

import copy
import csv
import json
from collections import Counter
from pathlib import Path

from src.core.consistency import consistency_status
from src.core.decision_table import decide, load_policy

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_CSV = ROOT / "reports" / "model_comparison_test.csv"
DECISIONS = ["Likely Valid", "Likely Invalid", "Manual Review Required"]
LABEL_FOR = {"Likely Valid": "Valid Claim", "Likely Invalid": "Invalid Claim"}
KEYS = ("min_confidence", "strong_max_diff", "acceptable_max_diff")


class WhatIfError(ValueError):
    pass


def validate(t: dict) -> dict:
    try:
        out = {k: round(float(t[k]), 3) for k in KEYS}
    except (KeyError, TypeError, ValueError):
        raise WhatIfError("Give min_confidence, strong_max_diff and acceptable_max_diff as numbers between 0 and 1.")
    if not (0 <= out["min_confidence"] <= 1 and 0 <= out["strong_max_diff"] <= out["acceptable_max_diff"] <= 1):
        raise WhatIfError("Thresholds must satisfy 0 ≤ strong ≤ acceptable ≤ 1 and 0 ≤ minimum confidence ≤ 1.")
    return out


def _policy_with(t: dict) -> dict:
    p = copy.deepcopy(load_policy())
    p["consistency"].update(t)
    return p


def _decide(facts: dict, py: tuple, gtm: tuple, policy: dict) -> str:
    f = dict(facts)
    if py[0] and gtm[0]:
        f["consistency"], _ = consistency_status(py[0], py[1], gtm[0], gtm[1], policy["consistency"])
    return decide(f, policy)["decision"]


def _test_rows() -> list[dict]:
    rows = []
    with TEST_CSV.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            fired = r["rules_fired"] or ""
            facts = {"hard_fail_count": fired.count("(hard_fail)"), "manual_trigger_count": fired.count("(manual_review)"),
                     "contradiction_count": int(bool(r["contradictions"])), "duplicate_count": int(bool(r["duplicate_indicators"])),
                     "missing_mandatory_count": int("receipt" in (r["missing_documents"] or "").lower()),
                     "python_class": r["python_predicted"], "gtm_class": r["gtm_predicted"], "consistency": r["consistency_status"]}
            py_top = max(float(r[k]) for k in ("python_valid", "python_invalid", "python_manual"))
            gtm_top = max(float(r[k]) for k in ("gtm_valid", "gtm_invalid", "gtm_manual"))
            rows.append({"facts": facts, "py": (r["python_predicted"], py_top), "gtm": (r["gtm_predicted"], gtm_top),
                         "actual": r["actual_class"], "stored": r["final_decision"], "id": r["claim_id"]})
    return rows


def _summary(decisions: list[str], actual: list[str]) -> dict:
    n = len(decisions)
    auto = [(d, a) for d, a in zip(decisions, actual) if d in LABEL_FOR]
    correct = sum(LABEL_FOR[d] == a for d, a in auto)
    review_ok = sum(1 for d, a in zip(decisions, actual) if d == "Manual Review Required" and a == "Manual Review")
    counts = Counter(decisions)
    return {"n": n, "counts": {d: counts.get(d, 0) for d in DECISIONS},
            "automation_rate": round(len(auto) / n, 4) if n else 0.0,
            "auto_accuracy": round(correct / len(auto), 4) if auto else None,
            "auto_errors": len(auto) - correct, "review_share": round(counts.get("Manual Review Required", 0) / n, 4) if n else 0.0,
            "review_needed_caught": review_ok}


def _live_rows() -> list[dict]:
    from src.models.entities import Claim
    rows = []
    for c in Claim.query.filter(Claim.final_decision.isnot(None)).all():
        ev = c.model_evaluation
        if ev is None or not ev.payload_json:
            continue
        p = json.loads(ev.payload_json)
        rows.append({"facts": p["decision"]["facts"], "id": c.claim_id, "stored": p["decision"]["value"],
                     "py": (p["python"].get("predicted"), p["python"].get("top") or 0.0),
                     "gtm": (p["gtm"].get("predicted"), p["gtm"].get("top") or 0.0), "product": c.product.product_name})
    return rows


def simulate(proposed: dict, include_live: bool = True) -> dict:
    proposed = validate(proposed)
    current_policy, proposed_policy = load_policy(), _policy_with(proposed)
    test = _test_rows()
    cur = [_decide(r["facts"], r["py"], r["gtm"], current_policy) for r in test]
    new = [_decide(r["facts"], r["py"], r["gtm"], proposed_policy) for r in test]
    actual = [r["actual"] for r in test]
    out = {"current": {k: current_policy["consistency"][k] for k in KEYS}, "proposed": proposed,
           "test": {"current": _summary(cur, actual), "proposed": _summary(new, actual),
                    "changed": sum(a != b for a, b in zip(cur, new)),
                    "transitions": _transitions(cur, new)}}
    if include_live:
        live = _live_rows()
        lc = [_decide(r["facts"], r["py"], r["gtm"], current_policy) for r in live]
        ln = [_decide(r["facts"], r["py"], r["gtm"], proposed_policy) for r in live]
        out["live"] = {"n": len(live), "changed": [{"claim_id": r["id"], "product": r["product"], "from": a, "to": b}
                                                   for r, a, b in zip(live, lc, ln) if a != b][:50],
                       "changed_count": sum(a != b for a, b in zip(lc, ln)), "transitions": _transitions(lc, ln)}
    return out


def _transitions(before: list[str], after: list[str]) -> list[list[int]]:
    idx = {d: i for i, d in enumerate(DECISIONS)}
    m = [[0] * 3 for _ in DECISIONS]
    for a, b in zip(before, after):
        m[idx[a]][idx[b]] += 1
    return m


def reproduces_stored() -> float:
    """Share of test rows whose replay under the current thresholds equals the stored decision (a self-check)."""
    policy = load_policy()
    rows = _test_rows()
    return sum(_decide(r["facts"], r["py"], r["gtm"], policy) == r["stored"] for r in rows) / len(rows)
