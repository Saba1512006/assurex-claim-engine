"""Pure RBAC + ABAC policy engine (no Flask import -> unit-testable in isolation).

Three layers, all must pass:
  1. Permission  : does the role hold the permission at all?        (deny by default)
  2. Scope       : is THIS record inside the role's scope?          (own / service_center / assigned_or_queue / all)
  3. Constraints : separation of duties, claim state, editability.  (business rules)

Every decision returns a Decision with a machine reason code -> audited, testable,
and shown to users as a human message (never a stack trace).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

POLICY_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "rbac.json"
SCOPES = {"own", "service_center", "assigned_or_queue", "all"}
QUEUE_STATUSES = {"Manual Review", "Under Evaluation", "Additional Information Required"}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str                 # e.g. OK, NO_PERMISSION, OUT_OF_SCOPE, SOD_OWN_CLAIM ...
    hide: bool = False        # True -> respond 404 (do not reveal the record exists)

    def __bool__(self) -> bool:
        return self.allowed


@lru_cache(maxsize=1)
def policy() -> dict:
    p = json.loads(POLICY_PATH.read_text())
    for role, spec in p["roles"].items():                       # fail fast on typos
        bad = {s for s in spec["permissions"].values() if s not in SCOPES}
        if bad:
            raise ValueError(f"rbac.json: role {role} uses unknown scope(s) {bad}")
    return p


def reload_policy() -> None:
    policy.cache_clear()


def roles() -> list[str]:
    return list(policy()["roles"])


def self_registrable_roles() -> set[str]:
    return {r for r, s in policy()["roles"].items() if s.get("self_registration")}


def scope_of(role: str, permission: str) -> str | None:
    return policy()["roles"].get(role, {}).get("permissions", {}).get(permission)


def has_permission(user: Any, permission: str) -> bool:
    return bool(user and getattr(user, "is_active", False) and scope_of(user.role, permission))


# ---------------------------------------------------------------- scope
def _owner_id(obj: Any):
    """Resolve the customer who owns a claim / product / document."""
    if not hasattr(obj, "document_id") and getattr(obj, "user_id", None) is not None:
        return obj.user_id                      # Claim / Product
    parent = getattr(obj, "claim", None) or getattr(obj, "product", None)
    return getattr(parent, "user_id", None) if parent is not None else None


def _service_center(obj: Any):
    for o in (obj, getattr(obj, "claim", None), getattr(obj, "product", None)):
        if o is not None and getattr(o, "service_center_id", None) is not None:
            return o.service_center_id
    return None


def _claim_of(obj: Any):
    return obj if hasattr(obj, "assigned_reviewer_id") else getattr(obj, "claim", None)


def _in_review_scope(user: Any, claim: Any) -> bool:
    if claim.assigned_reviewer_id == user.id:
        return True
    return claim.assigned_reviewer_id is None and claim.status in QUEUE_STATUSES


def in_scope(user: Any, scope: str, obj: Any) -> bool:
    if scope == "all":
        return True
    if scope == "own":
        return obj is not None and _owner_id(obj) == user.id
    if scope == "service_center":
        sc = getattr(user, "service_center_id", None)
        return sc is not None and _service_center(obj) == sc
    if scope == "assigned_or_queue":
        claim = _claim_of(obj)
        if claim is not None:
            return _in_review_scope(user, claim)
        # a product (or product-level document) is reachable through any claim in the reviewer's scope
        product = obj if hasattr(obj, "serial_number") else getattr(obj, "product", None)
        return product is not None and any(_in_review_scope(user, c) for c in getattr(product, "claims", []))
    return False


# ---------------------------------------------------------------- main entry
def authorize(user: Any, permission: str, obj: Any = None, **ctx) -> Decision:
    if user is None:
        return Decision(False, "NOT_AUTHENTICATED")
    if not getattr(user, "is_active", False):
        return Decision(False, "ACCOUNT_DISABLED")
    scope = scope_of(user.role, permission)
    if scope is None:
        return Decision(False, "NO_PERMISSION")
    if obj is not None and not in_scope(user, scope, obj):
        # the user may not even know this record exists -> 404, not 403
        return Decision(False, "OUT_OF_SCOPE", hide=True)
    return _constraints(user, permission, obj, ctx)


def _constraints(user: Any, permission: str, obj: Any, ctx: dict) -> Decision:
    sod = policy()["separation_of_duties"]
    claim = _claim_of(obj) if obj is not None else None

    if permission in {"review.decide", "review.override"}:
        if claim is None:
            return Decision(False, "CLAIM_REQUIRED")
        if sod["reviewer_cannot_decide_own_claim"] and user.id in {claim.user_id, getattr(claim, "created_by_id", None)}:
            return Decision(False, "SOD_OWN_CLAIM")
        target = ctx.get("target_status")
        allowed_next = policy()["review_transitions"].get(claim.status, [])
        if target is not None and target not in allowed_next:
            return Decision(False, "INVALID_TRANSITION")
        if permission == "review.override" and len((ctx.get("reason") or "").strip()) < sod["override_reason_min_chars"]:
            return Decision(False, "OVERRIDE_REASON_REQUIRED")

    if permission in {"claim.update_draft", "document.replace", "document.delete", "document.correct_ocr"}:
        if claim is not None and claim.status not in policy()["editable_claim_statuses"]:
            return Decision(False, "CLAIM_LOCKED")

    if permission == "user.manage" and ctx.get("target_user") is not None:
        target = ctx["target_user"]
        new_role = ctx.get("new_role")
        if new_role is not None and new_role not in policy()["roles"]:
            return Decision(False, "UNKNOWN_ROLE")
        if sod["cannot_change_own_role"] and target.id == user.id and (new_role or ctx.get("deactivate")):
            return Decision(False, "SOD_SELF_CHANGE")
        if sod["keep_at_least_one_admin"] and target.role == "administrator" and \
                (ctx.get("deactivate") or (new_role and new_role != "administrator")) and ctx.get("active_admin_count", 0) <= 1:
            return Decision(False, "LAST_ADMIN")
    return Decision(True, "OK")


def visible_claims_filter(user: Any) -> dict:
    """Row-level filter spec for list/search/export queries (mirrors in_scope exactly).
    Shape: {"any": [ {field: value | [values]} , ... ]}  ->  OR of ANDed equality/IN terms.
    Empty "any" list = no rows. {"all_rows": True} = no restriction."""
    scope = scope_of(user.role, "claim.read") if user else None
    if scope == "all":
        return {"all_rows": True}
    if scope == "own":
        return {"any": [{"user_id": user.id}]}
    if scope == "service_center":
        sc = getattr(user, "service_center_id", None)
        return {"any": [{"service_center_id": sc}]} if sc is not None else {"any": []}
    if scope == "assigned_or_queue":
        return {"any": [{"assigned_reviewer_id": user.id},
                        {"assigned_reviewer_id": None, "status": sorted(QUEUE_STATUSES)}]}
    return {"any": []}


MESSAGES = {
    "NOT_AUTHENTICATED": "Sign in to continue.",
    "ACCOUNT_DISABLED": "This account is disabled. Contact your administrator.",
    "NO_PERMISSION": "Your role doesn't include this action.",
    "OUT_OF_SCOPE": "We couldn't find that record.",
    "SOD_OWN_CLAIM": "You can't review a claim you submitted. It has been left for another reviewer.",
    "INVALID_TRANSITION": "This claim can't move to that status from its current stage.",
    "OVERRIDE_REASON_REQUIRED": "Add a reason of at least 20 characters to override the automated recommendation.",
    "CLAIM_LOCKED": "This claim is locked for editing at its current stage.",
    "SOD_SELF_CHANGE": "You can't change your own role or disable your own account.",
    "LAST_ADMIN": "At least one active administrator must remain.",
    "UNKNOWN_ROLE": "That role doesn't exist.",
    "CLAIM_REQUIRED": "Select a claim first.",
    "PASSWORD_CHANGE_REQUIRED": "Set a new password to finish activating your account.",
}
