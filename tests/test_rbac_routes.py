"""Route-level RBAC tests against the real app.
Every endpoint must be public-by-allowlist or guarded; escalation and IDOR paths are pinned."""
import pytest

from database.db import db
from src.models.entities import ClaimDocument, User
from src.security.guards import PUBLIC_ENDPOINTS, invalidate_sessions
from tests.conftest import login, make_center, make_claim, make_product, make_user


def test_no_unguarded_endpoints(app):
    unguarded = [ep for ep, view in app.view_functions.items()
                 if ep not in PUBLIC_ENDPOINTS and not getattr(view, "_rbac_guarded", False)]
    assert unguarded == [], f"add @require(...) to: {unguarded}"


def test_public_registration_cannot_create_admin(client):
    client.post("/register", data={"email": "evil@x.io", "full_name": "Evil", "password": "Passw0rd!xyz",
                                   "confirm_password": "Passw0rd!xyz", "role": "administrator"})
    assert User.query.filter_by(email="evil@x.io").one().role == "customer"


def test_login_does_not_reveal_which_emails_exist(app, client):
    make_user("a@x.io")
    r1 = client.post("/login", data={"email": "a@x.io", "password": "wrong"}, follow_redirects=True)
    r2 = client.post("/login", data={"email": "nobody@x.io", "password": "wrong"}, follow_redirects=True)
    assert b"Email or password is incorrect" in r1.data and b"Email or password is incorrect" in r2.data
    assert r1.status_code == r2.status_code


def test_lockout_after_five_failures(app, client):
    u = make_user("l@x.io")
    for _ in range(5):
        client.post("/login", data={"email": "l@x.io", "password": "wrong"})
    r = login(client, "l@x.io")                    # right password, but locked
    assert r.status_code == 401 and b"Too many attempts" in r.data
    assert db.session.get(User, u.id).is_locked


def test_role_change_kills_existing_session(app, client):
    u = make_user("r@x.io", "claim_reviewer")
    login(client, "r@x.io")
    assert client.get("/reviewer/queue").status_code == 200
    u.role = "customer"
    invalidate_sessions(u)
    db.session.commit()
    assert client.get("/reviewer/queue").status_code in (302, 403)


def test_disabled_user_is_signed_out(app, client):
    u = make_user("d@x.io")
    login(client, "d@x.io")
    u.is_active = False
    db.session.commit()
    assert client.get("/claims/").status_code == 302


@pytest.mark.parametrize("role,path,expected", [
    ("customer", "/admin/dashboard", 403), ("customer", "/reviewer/queue", 403),
    ("service_center_staff", "/admin/policies", 403), ("claim_reviewer", "/admin/export/claims", 403),
    ("claim_reviewer", "/claims/new", 403), ("administrator", "/claims/new", 403),
    ("administrator", "/admin/dashboard", 200), ("claim_reviewer", "/reviewer/queue", 200),
    ("customer", "/claims/new", 200), ("service_center_staff", "/claims/", 200),
])
def test_role_endpoint_matrix(app, client, role, path, expected):
    center = make_center()
    make_user(f"{role}@x.io", role, center=center if role == "service_center_staff" else None)
    login(client, f"{role}@x.io")
    assert client.get(path).status_code == expected


def test_idor_on_other_customers_records_returns_404(app, client):
    owner, _ = make_user("o@x.io"), make_user("i@x.io")
    product = make_product(owner)
    claim = make_claim(product)
    doc = ClaimDocument(document_id="DOC-T1", claim=claim, product=product, document_type="receipt",
                        original_filename="r.pdf", file_path="docs/x.pdf", file_hash_sha256="0" * 64)
    db.session.add(doc)
    db.session.commit()
    login(client, "i@x.io")
    assert client.post("/claims/documents/DOC-T1/correct-data", data={"serial_number": "HACK"}).status_code == 404
    assert client.get(f"/claims/{claim.claim_id}").status_code == 404
    assert client.get(f"/products/{product.product_id}").status_code == 404
    assert client.get("/claims/documents/DOC-T1").status_code == 404
    assert "HACK" not in (db.session.get(ClaimDocument, doc.id).ocr_data_json or "")


def test_staff_only_see_their_service_center(app, client):
    a, b = make_center("A Center"), make_center("B Center", "Karachi")
    make_user("sa@x.io", "service_center_staff", center=a)
    cust = make_user("c@x.io")
    mine = make_claim(make_product(cust, center=a, serial="SN-A-1"))
    theirs = make_claim(make_product(cust, center=b, serial="SN-B-1", invoice="INV-B"))
    login(client, "sa@x.io")
    assert client.get(f"/claims/{mine.claim_id}").status_code == 200
    assert client.get(f"/claims/{theirs.claim_id}").status_code == 404
    listing = client.get("/claims/search").get_data(as_text=True)
    assert mine.claim_id in listing and theirs.claim_id not in listing


def test_reviewer_cannot_decide_claim_they_filed(app, client):
    rev = make_user("rv@x.io", "claim_reviewer")
    claim = make_claim(make_product(make_user("c2@x.io")), actor=rev, status="Manual Review")
    login(client, "rv@x.io")
    r = client.post(f"/reviewer/claims/{claim.claim_id}/decide",
                    data={"action": "approve", "comments": "Looks fine to me."})
    assert r.status_code == 403
    assert claim.status == "Manual Review"


def test_denied_access_is_audited(app, client):
    from src.models.entities import AuditLog
    make_user("x@x.io")
    login(client, "x@x.io")
    client.get("/admin/dashboard")
    assert AuditLog.query.filter_by(action="ACCESS_DENIED").count() == 1


def test_admin_cannot_demote_themselves_or_last_admin(app, client):
    admin = make_user("ad@x.io", "administrator")
    login(client, "ad@x.io")
    client.post(f"/admin/access/{admin.user_id}/role", data={"role": "customer"})
    client.post(f"/admin/access/{admin.user_id}/status")
    assert admin.role == "administrator" and admin.is_active
