"""Frontend contracts: verdict payload, JSON envelope, scope on the evaluation API, template hygiene."""
from __future__ import annotations

import json
from datetime import date, timedelta
import re
from pathlib import Path

from src.core.consistency import consistency_status
from src.core.decision_table import decide, load_policy
from src.models.entities import Claim
from tests.conftest import login, make_product, make_user
from tests.test_workflow import wizard_post

ROOT = Path(__file__).resolve().parent.parent
# Pages still on the pre-rebuild markup; the list shrinks with each frontend phase and ends empty.
NOT_YET_REBUILT: set[str] = set()   # every page is on the Inspection Bench components
CLASSES = ["Valid Claim", "Invalid Claim", "Manual Review"]


def _submitted_claim(client, gtm, email="c@x.io"):
    gtm.mirror_python()
    u = make_user(email)
    p = make_product(u)
    login(client, email)
    assert wizard_post(client, p).status_code == 302
    return u, Claim.query.one()


def test_verdict_payload_is_stored_complete_and_consistent(app, client, gtm):
    _, c = _submitted_claim(client, gtm)
    ev = c.model_evaluation
    p = json.loads(ev.payload_json)
    assert p["state"] == "decided" and p["claim_id"] == c.claim_id
    assert [s["name"] for s in p["stages"]] == ["preprocess", "python", "card", "gtm", "rules"]
    assert all(isinstance(s["ms"], int) and s["ms"] >= 0 for s in p["stages"]) and p["total_ms"] == ev.latency_ms
    for model in ("python", "gtm"):
        scores = p[model]["scores"]
        assert list(scores) == CLASSES                                   # fixed order, never sorted by value
        assert abs(sum(scores.values()) - 1) <= 0.001
        assert p[model]["top"] == max(scores.values())
    py, gt = p["python"], p["gtm"]
    assert p["consistency"]["difference"] == round(abs(py["top"] - gt["top"]), 4)
    status, _ = consistency_status(py["predicted"], py["top"], gt["predicted"], gt["top"], p["consistency"]["thresholds"])
    assert p["consistency"]["status"] == status
    assert decide(p["decision"]["facts"], load_policy())["decision"] == p["decision"]["value"] == c.final_decision
    assert len(p["gtm"]["occlusion"]) == 9 and p["gtm"]["card_url"].startswith(f"/claims/{c.claim_id}/card.png")


def test_evaluation_api_returns_the_stored_payload_in_the_envelope(app, client, gtm):
    _, c = _submitted_claim(client, gtm)
    r = client.get(f"/api/claims/{c.claim_id}/evaluation")
    body = r.get_json()
    assert r.status_code == 200 and body["success"] is True and body["error"] is None
    stored = json.loads(c.model_evaluation.payload_json)
    assert body["data"]["decision"] == stored["decision"] and list(body["data"]["python"]["scores"].items()) == list(stored["python"]["scores"].items())


def test_evaluation_api_errors_use_the_envelope(app, client, gtm):
    r = client.get("/api/claims/CLM-NOPE/evaluation")
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "NOT_AUTHENTICATED"
    make_user("x@x.io")
    login(client, "x@x.io")
    r = client.get("/api/claims/CLM-NOPE/evaluation")
    body = r.get_json()
    assert r.status_code == 404 and body["success"] is False and body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND" and body["error"]["reference"].startswith("ERR-")


def test_customer_b_gets_404_on_everything_of_customer_a(app, client, gtm):
    _, c = _submitted_claim(client, gtm)
    doc = c.documents[0]
    client.post("/logout")
    make_user("b@x.io")
    login(client, "b@x.io")
    for url in (f"/claims/{c.claim_id}", f"/api/claims/{c.claim_id}/evaluation", f"/claims/{c.claim_id}/card.png",
                f"/claims/documents/{doc.document_id}", f"/claims/{c.claim_id}/report.pdf"):
        assert client.get(url).status_code == 404, url


def test_fresh_verdict_animates_once_and_reload_is_static(app, client, gtm):
    _, c = _submitted_claim(client, gtm)
    fresh = client.get(f"/claims/{c.claim_id}?fresh=1").get_data(as_text=True)
    again = client.get(f"/claims/{c.claim_id}").get_data(as_text=True)
    assert 'class="panel verdict animate"' in fresh and "verdict animate" not in again
    assert 'role="img" aria-label="Python model:' in again                # meter has a text equivalent


def test_templates_have_no_unsafe_patterns():
    """No |safe on data, no inline style except CSS custom properties, no inline scripts except the nonce'd preloader."""
    allowed_safe = {"public/blog.html"}                                  # rendered Markdown of our own blog file
    for path in (ROOT / "templates").rglob("*.html"):
        rel = path.relative_to(ROOT / "templates").as_posix()
        if rel in NOT_YET_REBUILT:
            continue
        text = path.read_text(encoding="utf-8")
        if rel not in allowed_safe:
            assert "|safe" not in text, rel
        for style in re.findall(r'style="([^"]*)"', text):
            assert all(part.strip().startswith("--") for part in style.split(";") if part.strip()), (rel, style)
        for tag in re.findall(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>", text):
            assert "nonce=" in tag, (rel, tag)


def _row_counts():
    from database.db import db
    return {t.name: db.session.query(t).count()
            for t in db.metadata.sorted_tables}


def test_demo_evaluate_runs_the_real_pipeline_and_writes_nothing(app, client, gtm):
    gtm.mirror_python()
    before = _row_counts()
    for case, sample in (("valid", "01_valid_claim"), ("invalid", "02_invalid_claim"), ("boundary", "10_boundary_date_claim")):
        r = client.post("/api/demo/evaluate", json={"case": case})
        body = r.get_json()
        assert r.status_code == 200 and body["success"] is True, case
        p = body["data"]["payload"]
        assert decide(p["decision"]["facts"], load_policy())["decision"] == p["decision"]["value"]   # same table as a real claim
        assert list(p["python"]["scores"]) == CLASSES and p["gtm"]["card_url"].startswith("data:image/png;base64,")
        expected = json.loads((ROOT / "sample_claims" / f"{sample}.json").read_text())["expected"]
        if case != "boundary":                                            # boundary's expected D04 needs the real image model
            assert (p["decision"]["value"], p["decision"]["rule_id"]) == (expected["decision"], expected["rule"]), case
        assert body["data"]["meter"]["label"].startswith("Python model:")
    assert _row_counts() == before


def test_demo_evaluate_rejects_unknown_cases_with_field_errors(app, client):
    r = client.post("/api/demo/evaluate", json={"case": "../../etc/passwd"})
    body = r.get_json()
    assert r.status_code == 400 and body["error"]["code"] == "VALIDATION_FAILED" and "case" in body["error"]["fields"]


def test_demo_evaluate_is_rate_limited(tmp_path, monkeypatch):
    from config.config import TestConfig
    from database.db import db
    from src.app import create_app

    class Limited(TestConfig):
        RATELIMIT_ENABLED = True
    monkeypatch.setattr(Limited, "UPLOAD_DIR", tmp_path / "uploads")
    app = create_app(Limited)
    with app.app_context():
        db.create_all()
        c = app.test_client()
        codes = [c.post("/api/demo/evaluate", json={"case": "nope"}).status_code for _ in range(11)]
        assert codes[:10] == [400] * 10 and codes[10] == 429
        assert c.post("/api/demo/evaluate", json={"case": "nope"}).get_json()["error"]["code"] == "RATE_LIMITED"
        db.session.remove()
        db.drop_all()


def test_macro_attributes_render_as_attributes_not_escaped_text(app, client):
    html = client.get("/register").get_data(as_text=True)
    assert 'placeholder="+92 300 1234567"' in html and 'autocomplete="email"' in html
    assert not re.search(r"<(input|button|select|textarea)\b[^>]*&#34;", html)       # no escaped quotes inside a tag


def _step2(product, **over):
    data = {"product_id": product.product_id, "fault_category": "Motherboard failure", "damage_type": "Manufacturing Defect",
            "fault_occurrence_date": (date.today() - timedelta(days=3)).isoformat(),
            "fault_description": "Laptop shuts down within minutes of starting."}
    data.update(over)
    return data


def test_wizard_autosave_creates_one_draft_and_submit_reuses_it(app, client, gtm):
    gtm.mirror_python()
    u = make_user("c@x.io")
    p = make_product(u)
    login(client, "c@x.io")
    r = client.post("/api/claims/draft", data=_step2(p))
    body = r.get_json()
    assert r.status_code == 200 and body["success"] and body["data"]["claim_id"].startswith("CLM-")
    draft_id = body["data"]["claim_id"]
    again = client.post("/api/claims/draft", data=_step2(p, draft_id=draft_id, fault_description="Shuts down after five minutes, every time."))
    assert again.get_json()["data"]["claim_id"] == draft_id and Claim.query.count() == 1
    assert Claim.query.one().fault_description.startswith("Shuts down") and Claim.query.one().status == "Draft"
    assert wizard_post(client, p, draft_id=draft_id).status_code == 302
    c = Claim.query.one()                                                 # the draft became the submitted claim
    assert c.claim_id == draft_id and c.status != "Draft" and c.model_evaluation is not None


def test_wizard_autosave_validates_and_never_touches_someone_elses_draft(app, client):
    a = make_user("a@x.io")
    pa = make_product(a)
    login(client, "a@x.io")
    short = client.post("/api/claims/draft", data=_step2(pa, fault_description="Too short"))
    assert short.status_code == 400 and short.get_json()["error"]["code"] == "VALIDATION_FAILED" and Claim.query.count() == 0
    theirs = client.post("/api/claims/draft", data=_step2(pa)).get_json()["data"]["claim_id"]
    client.post("/logout")
    b = make_user("b@x.io")
    pb = make_product(b, serial="SN-TST-2000002", invoice="INV-2025-22222")
    login(client, "b@x.io")
    mine = client.post("/api/claims/draft", data=_step2(pb, draft_id=theirs)).get_json()["data"]["claim_id"]
    assert mine != theirs and Claim.query.filter_by(claim_id=theirs).one().user_id == a.id


def test_readiness_check_uses_the_envelope(app, client):
    u = make_user("c@x.io")
    p = make_product(u)
    login(client, "c@x.io")
    body = client.post("/claims/preparation-check", data={"product_id": p.product_id}).get_json()
    assert body["success"] and {"items", "score", "ready"} <= set(body["data"])


def test_workbench_opens_for_reviewers_only_and_decisions_return_to_it(app, client):
    from tests.conftest import make_claim
    cust = make_user("c@x.io")
    rv = make_user("rv@x.io", "claim_reviewer")
    high = make_claim(make_product(cust), status="Manual Review", risk_level="High", claim_submission_date=date.today(),
                      final_decision="Manual Review Required")
    low = make_claim(make_product(cust, serial="SN-TST-3000003", invoice="INV-2025-33333"), status="Manual Review",
                     risk_level="Low", claim_submission_date=date.today() - timedelta(days=5), final_decision="Manual Review Required")
    login(client, "c@x.io")
    assert client.get(f"/reviewer/claim/{high.claim_id}").status_code == 403
    client.post("/logout")
    login(client, "rv@x.io")
    html = client.get(f"/reviewer/claim/{low.claim_id}").get_data(as_text=True)
    assert "data-decision-bar" in html and "Keyboard shortcuts" in html
    assert f'/reviewer/claim/{high.claim_id}' in html                     # next claim: the other open one
    assert client.get("/reviewer/next").headers["Location"].endswith(f"/reviewer/claim/{high.claim_id}")   # high risk first
    wb = f"/reviewer/claim/{high.claim_id}"
    r = client.post(f"/reviewer/claims/{high.claim_id}/take", data={"next": wb})
    assert r.headers["Location"].endswith(wb) and high.assigned_reviewer_id == rv.id
    r = client.post(f"/reviewer/claims/{high.claim_id}/decide", data={"action": "approve", "comments": "Receipt and photos checked.", "next": wb})
    assert r.headers["Location"].endswith(wb) and high.status == "Approved"
    r = client.post(f"/reviewer/claims/{low.claim_id}/decide", data={"action": "approve", "comments": "Checked.", "next": "https://evil.example"})
    assert "evil" not in r.headers["Location"]                            # open-redirect guard


def test_what_if_simulation_is_read_only_and_reproduces_current_decisions(app, client):
    from src.core import decision_table
    from src.services import whatif
    assert whatif.reproduces_stored() == 1.0                              # replay == stored decisions at current thresholds
    make_user("ad@x.io", "administrator")
    make_user("c@x.io")
    before = decision_table.POLICY_PATH.read_text()
    login(client, "c@x.io")
    assert client.post("/api/admin/what-if", json={}).status_code == 403
    client.post("/logout")
    login(client, "ad@x.io")
    cur = decision_table.load_policy()["consistency"]
    same = client.post("/api/admin/what-if", json=cur).get_json()["data"]
    assert same["test"]["changed"] == 0 and same["test"]["current"] == same["test"]["proposed"]
    strict = client.post("/api/admin/what-if", json={**cur, "min_confidence": 0.95}).get_json()["data"]
    assert strict["test"]["proposed"]["automation_rate"] <= strict["test"]["current"]["automation_rate"]
    bad = client.post("/api/admin/what-if", json={**cur, "strong_max_diff": 0.5, "acceptable_max_diff": 0.2})
    assert bad.status_code == 400 and bad.get_json()["error"]["code"] == "VALIDATION_FAILED"
    assert decision_table.POLICY_PATH.read_text() == before              # simulation never saves
    assert client.get("/admin/what-if").status_code == 200


def test_what_if_apply_saves_a_new_version_and_audits(app, client):
    from src.core import decision_table
    from src.models.entities import AuditLog
    make_user("ad@x.io", "administrator")
    login(client, "ad@x.io")
    before = decision_table.POLICY_PATH.read_text()
    try:
        old = decision_table.load_policy()
        r = client.post("/admin/what-if/apply", data={**old["consistency"], "min_confidence": 0.65})
        new = decision_table.load_policy()
        assert r.status_code == 302 and new["consistency"]["min_confidence"] == 0.65 and new["version"] != old["version"]
        log = AuditLog.query.filter_by(action="DECISION_POLICY_UPDATED").one()
        assert "what-if" in log.details_json and "auto_accuracy" in log.details_json
    finally:
        decision_table.POLICY_PATH.write_text(before)


def _csv_upload(rows: int = 3, mutate=None):
    import io
    lines = (ROOT / "data" / "splits" / "test.csv").read_text(encoding="utf-8").splitlines()
    body = [lines[0]] + lines[1:1 + rows]
    if mutate:
        body = mutate(body)
    return {"file": (io.BytesIO("\n".join(body).encode()), "batch.csv")}


def test_batch_runs_in_chunks_writes_no_claims_and_exports(app, client):
    from src.services import batch as batch_service
    make_user("ad@x.io", "administrator")
    login(client, "ad@x.io")
    r = client.post("/api/admin/batch", data=_csv_upload(25), content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 201 and body["data"]["status"] == "queued" and body["data"]["total"] == 25
    steps, data = 0, body["data"]
    while data["status"] in ("queued", "running"):
        data = client.post(data["step_url"], json={}).get_json()["data"]
        steps += 1
    assert data["status"] == "done" and steps == -(-25 // batch_service.CHUNK)      # one chunk per call
    assert data["labelled"] == 25 and 0 <= data["python_accuracy"] <= 1 and sum(data["decisions"].values()) == 25
    assert Claim.query.count() == 0
    csv_text = client.get(data["csv_url"]).get_data(as_text=True)
    assert csv_text.splitlines()[0].startswith("claim_id,actual_class") and len(csv_text.splitlines()) == 26


def test_batch_rejects_bad_files_with_row_errors(app, client):
    make_user("ad@x.io", "administrator")
    make_user("rv@x.io", "claim_reviewer")
    login(client, "rv@x.io")
    assert client.post("/api/admin/batch", data=_csv_upload(), content_type="multipart/form-data").status_code == 403
    client.post("/logout")
    login(client, "ad@x.io")
    drop = lambda b: [",".join(line.split(",")[1:]) for line in b]                          # noqa: E731  first column gone
    r = client.post("/api/admin/batch", data=_csv_upload(mutate=drop), content_type="multipart/form-data")
    assert r.status_code == 400 and "Missing columns" in r.get_json()["error"]["message"]
    bad_cat = lambda b: [b[0]] + [line.replace("Consumer Electronics", "Toys").replace("Home Appliances", "Toys").replace("Industrial Tools", "Toys") for line in b[1:]]  # noqa: E731
    r = client.post("/api/admin/batch", data=_csv_upload(mutate=bad_cat), content_type="multipart/form-data")
    err = r.get_json()["error"]
    assert r.status_code == 400 and len(err["fields"]["rows"]) == 3 and err["fields"]["rows"][0].startswith("Row 2")


def test_batch_upload_is_rate_limited(tmp_path, monkeypatch):
    from config.config import TestConfig
    from database.db import db
    from src.app import create_app

    class Limited(TestConfig):
        RATELIMIT_ENABLED = True
    monkeypatch.setattr(Limited, "UPLOAD_DIR", tmp_path / "uploads")
    app = create_app(Limited)
    with app.app_context():
        db.create_all()
        make_user("ad@x.io", "administrator")
        c = app.test_client()
        login(c, "ad@x.io")
        codes = [c.post("/api/admin/batch", data={}, content_type="multipart/form-data").status_code for _ in range(4)]
        assert codes == [400, 400, 400, 429]
        db.session.remove()
        db.drop_all()


def test_policy_save_shows_up_in_version_history(app, client, tmp_path, monkeypatch):
    import shutil
    from src.rules import policy_store
    shutil.copytree(policy_store.POLICY_DIR, tmp_path / "policies")
    monkeypatch.setattr(policy_store, "POLICY_DIR", tmp_path / "policies")
    policy_store.reload()
    try:
        make_user("ad@x.io", "administrator")
        login(client, "ad@x.io")
        p = policy_store.get_policy("Home Appliances")
        form = {"category": "Home Appliances", **{k: p[k] for k in policy_store.EDITABLE}, "grace_period_days": p["grace_period_days"] + 1,
                "excluded_damage_types": p["excluded_damage_types"]}
        form.update({f"rule_{rid}": ("hard_fail" if rid in p["hard_fail_rules"] else "manual_review" if rid in p["manual_review_rules"]
                                     else "warning" if rid in p["warning_rules"] else "off") for rid in policy_store.RULE_CATALOG})
        client.post("/admin/policies", data=form)
        html = client.get("/admin/policies?category=Home+Appliances").get_data(as_text=True)
        assert f"<del>{p['grace_period_days']}</del> → <ins>{p['grace_period_days'] + 1}</ins>" in html
    finally:
        policy_store.reload()


def test_customer_view_setting_hides_model_details_from_customers_only(app, client, gtm):
    _, c = _submitted_claim(client, gtm)
    client.post("/logout")
    make_user("ad@x.io", "administrator")
    login(client, "ad@x.io")
    client.post("/admin/settings/customer-view", data={})                 # unchecked box: off
    client.post("/logout")
    login(client, "c@x.io")
    customer_html = client.get(f"/claims/{c.claim_id}").get_data(as_text=True)
    assert 'aria-label="Python model:' not in customer_html                # no gauge for the customer
    client.post("/logout")
    login(client, "ad@x.io")
    assert 'aria-label="Python model:' in client.get(f"/claims/{c.claim_id}").get_data(as_text=True)


def test_overrides_export_lists_reviewer_decisions_next_to_the_models(app, client):
    from tests.conftest import make_claim
    cust = make_user("c@x.io")
    make_user("rv@x.io", "claim_reviewer")
    make_user("ad@x.io", "administrator")
    c = make_claim(make_product(cust), status="Manual Review", final_decision="Likely Invalid", claim_submission_date=date.today())
    login(client, "rv@x.io")
    client.post(f"/reviewer/claims/{c.claim_id}/decide", data={"action": "approve", "comments": "Receipt checked.",
                "override_reason": "Retailer confirmed the purchase by phone."})
    client.post("/logout")
    login(client, "ad@x.io")
    text = client.get("/admin/export/overrides").get_data(as_text=True)
    lines = text.lstrip("﻿").splitlines()
    assert lines[0].startswith("Claim ID,Category") and len(lines) == 2
    assert c.claim_id in lines[1] and ",Likely Invalid," in lines[1] and ",Approved,yes,Retailer confirmed" in lines[1]
