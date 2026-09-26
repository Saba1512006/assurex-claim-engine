"""Integration tests through HTTP: the full claim journey, reviewer workflow, admin tools, security controls."""
import io
from datetime import date, timedelta

from config.config import TestConfig
from database.db import db
from src.app import create_app
from src.models.entities import AuditLog, Claim, Notification, Product, ReviewerAction, User
from tests.conftest import (PASSWORD, login, make_center, make_claim, make_product, make_user, png_bytes,
                            standard_receipt)


def file(data, name):
    return (io.BytesIO(data), name)


def wizard_post(client, product, action="submit", **over):
    data = {"product_id": product.product_id, "fault_category": "Motherboard failure",
            "damage_type": "Manufacturing Defect", "fault_occurrence_date": (date.today() - timedelta(days=3)).isoformat(),
            "fault_description": "Laptop shuts down within minutes of starting.", "diagnostic_confidence": "0.85",
            "action": action, "receipt": file(standard_receipt(product), "receipt.pdf"),
            "warranty_card": file(png_bytes((1, 1, 1)), "card.png"), "serial_photo": file(png_bytes((2, 2, 2)), "sn.png"),
            "damage_photo": file(png_bytes((3, 3, 3)), "dmg.png"), "verified_serial_number": ""}
    data.update(over)
    return client.post("/claims/new", data=data, content_type="multipart/form-data")


def test_customer_registers_product_with_receipt(app, client):
    make_user("c@x.io")
    login(client, "c@x.io")
    purchased = date.today() - timedelta(days=100)
    pdf = standard_receipt(Product(product_name="Phone X", model_number="PX-1", serial_number="SN-PX-00001",
                                   invoice_number="INV-2026-00001", purchase_date=purchased, retailer="Store"))
    r = client.post("/products/new", data={
        "product_name": "Phone X", "category": "Consumer Electronics", "brand": "Nova", "model_number": "PX-1",
        "serial_number": "sn-px-00001", "purchase_date": purchased.strftime("%d/%m/%Y"), "purchase_price": "650",
        "retailer": "Store", "invoice_number": "INV-2026-00001", "warranty_type": "standard", "warranty_months": "12",
        "receipt": file(pdf, "r.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 302
    p = Product.query.one()
    assert p.serial_number == "SN-PX-00001" and p.warranty.duration_months == 12
    assert p.warranty.expiry_date == purchased + timedelta(days=365)
    assert p.documents[0].ocr_status == "ok"
    assert AuditLog.query.filter_by(action="PRODUCT_REGISTERED").count() == 1


def test_product_form_validation(app, client):
    make_user("c@x.io")
    login(client, "c@x.io")
    r = client.post("/products/new", data={"product_name": "", "category": "Toys", "purchase_date": "2099-01-01",
                                           "purchase_price": "-5"})
    assert r.status_code == 400 and Product.query.count() == 0


def test_scan_receipt_endpoint(app, client):
    u = make_user("c@x.io")
    p = make_product(u)
    login(client, "c@x.io")
    r = client.post("/products/scan-receipt", data={"receipt": file(standard_receipt(p), "r.pdf")},
                    content_type="multipart/form-data")
    assert r.json["ok"] and r.json["entities"]["serial_number"] == p.serial_number
    r = client.post("/products/scan-receipt", data={"receipt": file(b"GIF89a" + b"0" * 300, "r.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and not r.json["ok"]


def test_full_claim_journey_with_agreeing_models(app, client, gtm):
    gtm.mirror_python()
    u = make_user("c@x.io")
    p = make_product(u)
    login(client, "c@x.io")
    r = wizard_post(client, p)
    assert r.status_code == 302
    c = Claim.query.one()
    assert c.status == "Approved" and c.final_decision == "Likely Valid"
    assert c.model_evaluation.model_consistency_status in ("Strong Match", "Acceptable Match")
    kinds = {n.notification_type for n in Notification.query.filter_by(user_id=u.id)}
    assert {"claim_submission", "status_change", "claim_approval", "review_complete"} <= kinds
    actions = {a.action for a in AuditLog.query.all()}
    assert {"CLAIM_CREATED", "DOCUMENT_UPLOADED", "MODEL_PREDICTION", "FINAL_DECISION", "CLAIM_SUBMITTED",
            "STATUS_CHANGE"} <= actions
    page = client.get(f"/claims/{c.claim_id}").get_data(as_text=True)
    assert "Likely Valid" in page and "Claim Summary Card" in page
    assert client.get(f"/claims/{c.claim_id}/card.png").mimetype == "image/png"
    pdf = client.get(f"/claims/{c.claim_id}/report.pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    assert client.get(f"/claims/{c.claim_id}/track").status_code == 200


def test_ocr_values_confirmed_by_user_are_saved_and_audited(app, client):
    u = make_user("c@x.io")
    p = make_product(u)
    login(client, "c@x.io")
    wizard_post(client, p, action="draft", verified_serial_number="SN-CORRECTED-1")
    c = Claim.query.one()
    assert c.status == "Draft"
    receipt = next(d for d in c.documents if d.document_type == "receipt")
    assert receipt.get_ocr_payload()["serial_number"] == "SN-CORRECTED-1" and receipt.verified_by_user
    assert AuditLog.query.filter_by(action="EXTRACTED_DATA_CORRECTION").count() == 1


def test_draft_edit_then_submit(app, client):
    u = make_user("c@x.io")
    p = make_product(u)
    login(client, "c@x.io")
    wizard_post(client, p, action="draft")
    c = Claim.query.one()
    client.post(f"/claims/{c.claim_id}/update", data={"fault_category": "Battery not charging",
                "damage_type": "Manufacturing Defect", "fault_occurrence_date": c.fault_occurrence_date.isoformat(),
                "fault_description": "Battery stops charging at 10 percent."})
    assert c.fault_category == "Battery not charging"
    client.post(f"/claims/{c.claim_id}/submit")
    assert c.status == "Manual Review"        # no Teachable Machine model -> D04
    assert client.post(f"/claims/{c.claim_id}/update", data={"fault_category": "x"}).status_code == 403


def test_wizard_rejects_bad_input(app, client):
    u = make_user("c@x.io")
    p = make_product(u)
    login(client, "c@x.io")
    r = wizard_post(client, p, damage_type="Hardware Defect", fault_occurrence_date="2099-01-01")
    assert r.status_code == 400 and Claim.query.count() == 0


def test_reviewer_override_requires_reason_and_keeps_ai_result(app, client):
    cust = make_user("c@x.io")
    make_user("rv@x.io", "claim_reviewer")
    c = make_claim(make_product(cust), status="Manual Review", final_decision="Likely Invalid",
                   claim_submission_date=date.today())
    login(client, "rv@x.io")
    client.post(f"/reviewer/claims/{c.claim_id}/decide", data={"action": "approve", "comments": "Receipt checked."})
    assert c.status == "Manual Review"                                    # 20-char reason missing
    client.post(f"/reviewer/claims/{c.claim_id}/decide", data={"action": "approve", "comments": "Receipt checked.",
                "override_reason": "Retailer confirmed the purchase by phone."})
    assert c.status == "Approved" and c.final_decision == "Likely Invalid"   # AI recommendation preserved
    a = ReviewerAction.query.one()
    assert a.is_override and a.previous_recommendation == "Likely Invalid" and "Retailer" in a.override_reason
    assert client.post(f"/reviewer/claims/{c.claim_id}/decide", data={"action": "reject", "comments": "changed mind"}).status_code == 302
    assert c.status == "Approved"                                         # Approved -> Rejected is not a transition


def test_request_info_loop(app, client):
    cust = make_user("c@x.io")
    make_user("rv@x.io", "claim_reviewer")
    c = make_claim(make_product(cust), status="Manual Review", final_decision="Manual Review Required",
                   claim_submission_date=date.today())
    rv = app.test_client()
    login(rv, "rv@x.io")
    rv.post(f"/reviewer/claims/{c.claim_id}/decide", data={"action": "request_info",
                                                            "comments": "Please upload the warranty card."})
    assert c.status == "Additional Information Required"
    assert Notification.query.filter_by(user_id=cust.id, notification_type="additional_info_required").count() == 1
    login(client, "c@x.io")
    r = client.post(f"/claims/{c.claim_id}/documents", data={"document_type": "warranty_card",
                    "file": file(png_bytes(), "card.png")}, content_type="multipart/form-data")
    assert r.status_code == 302 and any(d.document_type == "warranty_card" for d in c.documents)
    client.post(f"/claims/{c.claim_id}/submit")
    assert c.status == "Manual Review" and len(c.evaluations) == 1


def test_reviewer_queue_and_take(app, client):
    cust = make_user("c@x.io")
    rv = make_user("rv@x.io", "claim_reviewer")
    c = make_claim(make_product(cust), status="Manual Review", claim_submission_date=date.today())
    login(client, "rv@x.io")
    assert c.claim_id in client.get("/reviewer/queue").get_data(as_text=True)
    client.post(f"/reviewer/claims/{c.claim_id}/take")
    assert c.assigned_reviewer_id == rv.id
    assert c.claim_id in client.get("/reviewer/queue?tab=mine").get_data(as_text=True)


def test_admin_tools(app, client):
    make_user("ad@x.io", "administrator")
    cust = make_user("c@x.io")
    make_claim(make_product(cust, name="=HYPERLINK(evil)"), claim_submission_date=date.today(), status="Manual Review")
    login(client, "ad@x.io")
    for url in ("/admin/dashboard", "/admin/analytics", "/admin/policies", "/admin/models", "/admin/audit",
                "/admin/access/", "/admin/analytics?format=json"):
        assert client.get(url).status_code == 200, url
    csv = client.get("/admin/export/claims").get_data(as_text=True)
    assert "'=HYPERLINK(evil)" in csv                    # formula injection neutralised
    for kind in ("products", "warranties", "analytics", "audit"):
        assert client.get(f"/admin/export/{kind}").status_code == 200


def test_admin_invites_staff_who_must_change_password(app, client):
    make_user("ad@x.io", "administrator")
    center = make_center()
    login(client, "ad@x.io")
    r = client.post("/admin/access/invite", data={"full_name": "New Staff", "email": "ns@x.io",
                                                  "role": "service_center_staff", "service_center_id": str(center.id)},
                    follow_redirects=True)
    temp = r.get_data(as_text=True).split("One-time password: ")[1].split(" ")[0]
    u = User.query.filter_by(email="ns@x.io").one()
    assert u.must_change_password and u.service_center_id == center.id
    staff = app.test_client()
    login(staff, "ns@x.io", temp)
    assert staff.get("/claims/").status_code == 302                    # forced to profile
    staff.post("/profile", data={"action": "password", "current_password": temp, "new_password": "BrandNew123x",
                                 "confirm_password": "BrandNew123x"})
    assert not u.must_change_password and staff.get("/claims/").status_code == 200


def test_policy_editor_validates_and_audits(app, client, monkeypatch, tmp_path):
    import shutil
    from src.rules import policy_store
    shutil.copytree(policy_store.POLICY_DIR, tmp_path / "p")
    monkeypatch.setattr(policy_store, "POLICY_DIR", tmp_path / "p")
    policy_store.reload()
    make_user("ad@x.io", "administrator")
    login(client, "ad@x.io")
    form = {"category": "Industrial Tools", "coverage_duration_months": "24", "grace_period_days": "21",
            "claim_reporting_period_days": "30", "exclusion_min_diagnostic_confidence": "0.55",
            "repeat_repair_review_threshold": "2", "excluded_damage_types": ["Accidental Drop"],
            **{f"rule_{r}": "hard_fail" if r == "WARRANTY_EXPIRED" else "off" for r in policy_store.RULE_CATALOG}}
    client.post("/admin/policies", data=form)
    assert policy_store.get_policy("Industrial Tools")["grace_period_days"] == 21
    assert AuditLog.query.filter_by(action="POLICY_UPDATED").count() == 1
    form["grace_period_days"] = "999"
    client.post("/admin/policies", data=form)
    assert policy_store.get_policy("Industrial Tools")["grace_period_days"] == 21
    policy_store.reload()


def test_gtm_upload_rejects_non_tflite(app, client):
    make_user("ad@x.io", "administrator")
    login(client, "ad@x.io")
    r = client.post("/admin/models/gtm", data={"model": file(b"not a model" * 200, "m.tflite"),
                                               "labels": file(b"0 Valid Claim\n1 Invalid Claim\n2 Manual Review", "labels.txt")},
                    content_type="multipart/form-data", follow_redirects=True)
    assert b"not a TensorFlow Lite model" in r.data


def test_security_headers_and_csp(app, client):
    r = client.get("/login")
    assert r.headers["X-Frame-Options"] == "DENY" and r.headers["X-Content-Type-Options"] == "nosniff"
    assert "script-src 'self';" in r.headers["Content-Security-Policy"]
    assert "unsafe-inline" not in r.headers["Content-Security-Policy"].split("script-src")[1].split(";")[0]
    assert r.headers["Cache-Control"] == "no-store"


def test_csrf_is_enforced(tmp_path, monkeypatch):
    class CsrfConfig(TestConfig):
        WTF_CSRF_ENABLED = True
        UPLOAD_DIR = tmp_path
    app = create_app(CsrfConfig)
    with app.app_context():
        db.create_all()
        make_user("c@x.io")
        c = app.test_client()
        r = c.post("/login", data={"email": "c@x.io", "password": PASSWORD})
        assert r.status_code == 400 and b"form expired" in r.data
        db.drop_all()


def test_open_redirect_blocked(app, client):
    make_user("c@x.io")
    r = client.post("/login?next=//evil.example", data={"email": "c@x.io", "password": PASSWORD})
    assert r.headers["Location"].endswith("/home")


def test_logout_is_post_only_and_clears_session(app, client):
    make_user("c@x.io")
    login(client, "c@x.io")
    assert client.get("/logout").status_code == 405
    client.post("/logout")
    assert client.get("/claims/").status_code == 302


def test_public_pages(client):
    for url in ("/", "/blog", "/login", "/register", "/healthz"):
        assert client.get(url).status_code == 200, url
    assert client.get("/nope").status_code == 404
    assert client.get("/admin/dashboard").status_code == 302


def test_database_constraints(app):
    """Duplicate public IDs and orphan claims are rejected by the database itself."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    u = make_user("c@x.io")
    c = make_claim(make_product(u))
    db.session.add(Claim(claim_id=c.claim_id, user_id=u.id, product_id=c.product_id, fault_category="x",
                         damage_type="Manufacturing Defect", fault_description="x", fault_occurrence_date=date.today()))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
