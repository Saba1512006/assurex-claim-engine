"""Frontend contracts: verdict payload, JSON envelope, scope on the evaluation API, template hygiene."""
from __future__ import annotations

import json
import re
from pathlib import Path

from src.core.consistency import consistency_status
from src.core.decision_table import decide, load_policy
from src.models.entities import Claim
from tests.conftest import login, make_product, make_user
from tests.test_workflow import wizard_post

ROOT = Path(__file__).resolve().parent.parent
# Pages still on the pre-rebuild markup; the list shrinks with each frontend phase and ends empty.
NOT_YET_REBUILT = {'public/blog.html', 'components/macros.html', 'claims/wizard.html', 'admin/policies.html', 'admin/analytics.html', 'admin/audit.html', 'admin/dashboard.html', 'admin/models.html', 'claims/track.html', 'claims/search.html', 'reviewer/queue.html', 'admin/access_control.html', 'components/nav.html'}
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
