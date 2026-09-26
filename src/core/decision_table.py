"""Config-driven final decision (SRS xxxiv). First matching row wins.

Surprise modification ("change the decision logic", "change a threshold") =
edit config/decision_policy.json; no code change, fully unit-tested.
"""
from __future__ import annotations

import json
import operator
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "decision_policy.json"
DECISIONS = {"Likely Valid", "Likely Invalid", "Manual Review Required"}
ROUTABLE_STATUSES = {"Approved", "Rejected", "Manual Review"}
OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le,
       "==": operator.eq, "!=": operator.ne, "in": lambda a, b: a in b}


def load_policy(path: Path = POLICY_PATH) -> dict:
    policy = json.loads(path.read_text())
    for row in policy["decision_table"] + [policy["default"]]:           # fail fast on typos
        if row["decision"] not in DECISIONS:
            raise ValueError(f"{row['id']}: invalid decision {row['decision']!r}")
        for cond in row.get("when", {}).get("all", []) + row.get("when", {}).get("any", []):
            if cond[1] not in OPS:
                raise ValueError(f"{row['id']}: unknown operator {cond[1]!r}")
    routing = policy.get("routing", {})
    if set(routing) != DECISIONS or not set(routing.values()) <= ROUTABLE_STATUSES:
        raise ValueError("routing must map every decision to Approved, Rejected or Manual Review")
    c = policy["consistency"]
    if not (0 <= c["strong_max_diff"] <= c["acceptable_max_diff"] <= 1 and 0 <= c["min_confidence"] <= 1):
        raise ValueError("consistency thresholds must satisfy 0 <= strong <= acceptable <= 1")
    return policy


def save_policy(policy: dict, path: Path = POLICY_PATH) -> None:
    """Validate then atomically replace the policy file (used by Admin > Decision policy)."""
    import os
    import tempfile
    tmp_fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(policy, indent=2) + "\n")
    try:
        load_policy(Path(tmp))
    except Exception:
        os.unlink(tmp)
        raise
    os.replace(tmp, path)


def _holds(cond: list, facts: dict) -> bool:
    field, op, value = cond
    if field not in facts:
        raise KeyError(f"decision table references unknown fact {field!r}")
    return OPS[op](facts[field], value)


def decide(facts: dict, policy: dict | None = None) -> dict:
    """facts: flat dict built by the pipeline (counts, classes, consistency).
    Returns decision + the row that fired + every row evaluated (for the audit trail)."""
    policy = policy or load_policy()
    trace = []
    for row in policy["decision_table"]:
        w = row["when"]
        hit = all(_holds(c, facts) for c in w.get("all", [])) and \
            (not w.get("any") or any(_holds(c, facts) for c in w["any"]))
        trace.append({"id": row["id"], "matched": hit})
        if hit:
            return {"decision": row["decision"], "rule_id": row["id"], "reason": row["reason"],
                    "policy_version": policy["version"], "trace": trace}
    d = policy["default"]
    return {"decision": d["decision"], "rule_id": d["id"], "reason": d["reason"],
            "policy_version": policy["version"], "trace": trace}
