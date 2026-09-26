"""Pure policy tests: every role x permission x scope x constraint. No Flask needed."""
from types import SimpleNamespace as NS

import pytest

from src.security import rbac


def user(uid, role, active=True, sc=None):
    return NS(id=uid, role=role, is_active=active, service_center_id=sc)


CUST, OTHER = user(1, "customer"), user(2, "customer")
STAFF_A, STAFF_B = user(10, "service_center_staff", sc=100), user(11, "service_center_staff", sc=200)
REV, REV2 = user(20, "claim_reviewer"), user(21, "claim_reviewer")
ADMIN, ADMIN2 = user(30, "administrator"), user(31, "administrator")


def claim(owner=1, status="Manual Review", reviewer=None, sc=100, created_by=None):
    return NS(claim_id="CLM-1", user_id=owner, status=status, assigned_reviewer_id=reviewer,
              service_center_id=sc, created_by_id=created_by)


def doc(c):
    return NS(document_id="DOC-1", claim=c, product=None, user_id=None)


# ---------- layer 1: permission (deny by default) ----------
@pytest.mark.parametrize("u,perm,ok", [
    (CUST, "claim.create", True), (CUST, "admin.dashboard", False), (CUST, "review.decide", False),
    (CUST, "user.manage", False), (STAFF_A, "repair.record", True), (STAFF_A, "review.decide", False),
    (STAFF_A, "policy.manage", False), (REV, "review.queue", True), (REV, "claim.create", False),
    (REV, "export.data", False), (ADMIN, "policy.manage", True),
    (ADMIN, "review.decide", False),              # separation: config owners don't decide claims
    (user(9, "superuser"), "claim.read", False),  # unknown role
    (user(9, "customer", active=False), "claim.read", False),
])
def test_permission_matrix(u, perm, ok):
    assert rbac.has_permission(u, perm) is ok


def test_unauthenticated_denied():
    assert rbac.authorize(None, "claim.read").code == "NOT_AUTHENTICATED"


# ---------- layer 2: scope ----------
def test_customer_sees_only_own_claim_and_gets_404_semantics():
    assert rbac.authorize(CUST, "claim.read", claim(owner=1))
    d = rbac.authorize(OTHER, "claim.read", claim(owner=1))
    assert not d and d.code == "OUT_OF_SCOPE" and d.hide


def test_customer_document_idor_blocked():
    assert not rbac.authorize(OTHER, "document.correct_ocr", doc(claim(owner=1, status="Draft")))


def test_staff_limited_to_own_service_center():
    assert rbac.authorize(STAFF_A, "claim.read", claim(sc=100))
    assert not rbac.authorize(STAFF_B, "claim.read", claim(sc=100))
    assert not rbac.authorize(user(12, "service_center_staff", sc=None), "claim.read", claim(sc=None))


def test_reviewer_scope_assigned_or_unassigned_queue():
    assert rbac.authorize(REV, "claim.read", claim(reviewer=None, status="Manual Review"))
    assert rbac.authorize(REV, "claim.read", claim(reviewer=20, status="Approved"))
    assert not rbac.authorize(REV, "claim.read", claim(reviewer=21))           # someone else's
    assert not rbac.authorize(REV, "claim.read", claim(reviewer=None, status="Draft"))


# ---------- layer 3: constraints ----------
def test_reviewer_cannot_decide_own_claim():
    c = claim(owner=20, reviewer=20)
    assert rbac.authorize(REV, "review.decide", c).code == "SOD_OWN_CLAIM"
    assert rbac.authorize(REV, "review.decide", claim(owner=1, created_by=20, reviewer=20)).code == "SOD_OWN_CLAIM"


@pytest.mark.parametrize("status,target,ok", [
    ("Manual Review", "Approved", True), ("Manual Review", "Closed", False),
    ("Approved", "Rejected", False), ("Approved", "Closed", True), ("Closed", "Approved", False),
    ("Draft", "Approved", False),
])
def test_review_state_machine(status, target, ok):
    c = claim(status=status, reviewer=20)
    assert bool(rbac.authorize(REV, "review.decide", c, target_status=target)) is ok


def test_override_requires_reason():
    c = claim(reviewer=20)
    assert rbac.authorize(REV, "review.override", c, reason="no").code == "OVERRIDE_REASON_REQUIRED"
    assert rbac.authorize(REV, "review.override", c, reason="Receipt verified by phone with retailer.")


def test_submitted_claim_locked_for_customer_edits():
    assert rbac.authorize(CUST, "claim.update_draft", claim(status="Draft"))
    assert rbac.authorize(CUST, "claim.update_draft", claim(status="Manual Review")).code == "CLAIM_LOCKED"
    assert rbac.authorize(CUST, "document.replace", doc(claim(status="Approved"))).code == "CLAIM_LOCKED"


def test_admin_self_protection_and_last_admin():
    assert rbac.authorize(ADMIN, "user.manage", target_user=ADMIN, new_role="customer").code == "SOD_SELF_CHANGE"
    assert rbac.authorize(ADMIN, "user.manage", target_user=ADMIN2, deactivate=True,
                          active_admin_count=1).code == "LAST_ADMIN"
    assert rbac.authorize(ADMIN, "user.manage", target_user=ADMIN2, deactivate=True, active_admin_count=2)
    assert rbac.authorize(ADMIN, "user.manage", target_user=CUST, new_role="root").code == "UNKNOWN_ROLE"


def test_only_customer_can_self_register():
    assert rbac.self_registrable_roles() == {"customer"}


def test_list_filter_matches_object_scope():
    assert rbac.visible_claims_filter(CUST) == {"any": [{"user_id": 1}]}
    assert rbac.visible_claims_filter(ADMIN) == {"all_rows": True}
    assert rbac.visible_claims_filter(user(12, "service_center_staff")) == {"any": []}
    assert rbac.visible_claims_filter(NS(id=5, role="ghost", is_active=True)) == {"any": []}


def test_every_message_code_has_text():
    for code in ["NOT_AUTHENTICATED", "ACCOUNT_DISABLED", "NO_PERMISSION", "OUT_OF_SCOPE", "SOD_OWN_CLAIM",
                 "INVALID_TRANSITION", "OVERRIDE_REASON_REQUIRED", "CLAIM_LOCKED", "SOD_SELF_CHANGE", "LAST_ADMIN"]:
        assert rbac.MESSAGES[code]
