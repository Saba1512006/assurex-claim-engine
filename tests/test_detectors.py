"""Contradiction, serial-number, duplicate and missing-document detection."""
import json
from datetime import date, timedelta
from types import SimpleNamespace as NS

from database.db import db
from src.core.features import missing_mandatory, missing_supporting
from src.rules import contradiction_detector, duplicate_detector
from src.services import documents
from tests.conftest import (add_repair, attach_docs, make_claim, make_product, make_user, png_bytes,
                            standard_receipt, upload)

TODAY = date.today()


def doc(kind, **ocr):
    return NS(document_type=kind, get_ocr_payload=lambda: ocr)


def detect(**kw):
    base = dict(purchase_date=TODAY - timedelta(days=100), fault_date=TODAY - timedelta(days=3), submission_date=TODAY,
                registered_serial="SN-ABC-123", registered_model="ABP-16", registered_invoice="INV-1", documents=[],
                repairs=[])
    base.update(kw)
    return contradiction_detector.detect(**base)


def codes(r):
    return [f["code"] for f in r["findings"]]


def test_consistent_claim_has_no_contradictions():
    r = detect(documents=[doc("receipt", serial_number="sn abc 123", model_number="ABP-16", invoice_number="INV-1")])
    assert r["findings"] == [] and not r["serial_mismatch"] and not r["date_conflict"]


def test_date_contradictions():
    assert codes(detect(fault_date=TODAY - timedelta(days=200))) == ["DATE_FAULT_BEFORE_PURCHASE"]
    assert codes(detect(fault_date=TODAY + timedelta(days=2))) == ["DATE_FAULT_AFTER_CLAIM"]
    assert "DATE_CLAIM_BEFORE_PURCHASE" in codes(detect(submission_date=TODAY - timedelta(days=150),
                                                         fault_date=TODAY - timedelta(days=160)))
    rep = NS(repair_date=TODAY - timedelta(days=300), serial_number_seen=None)
    assert codes(detect(repairs=[rep])) == ["DATE_REPAIR_BEFORE_PURCHASE"]


def test_serial_checked_against_every_source():
    for kind in ("receipt", "warranty_card", "serial_photo", "diagnostic_report"):
        r = detect(documents=[doc(kind, serial_number="SN-XYZ-999")])
        assert r["serial_mismatch"] and "SERIAL_MISMATCH" in codes(r), kind
    r = detect(repairs=[NS(repair_date=TODAY, serial_number_seen="SN-OTHER-1")])
    assert r["serial_mismatch"]


def test_model_invoice_and_purchase_date_mismatch():
    r = detect(documents=[doc("receipt", model_number="ZZ-99", invoice_number="INV-2",
                              purchase_date=(TODAY - timedelta(days=30)).isoformat())])
    assert {"MODEL_MISMATCH", "INVOICE_MISMATCH", "PURCHASE_MISMATCH"} <= set(codes(r))


def test_placeholder_serials_are_ignored():
    assert detect(documents=[doc("receipt", serial_number="N/A")])["findings"] == []


def test_duplicate_document_hash_across_products(app):
    a, b = make_user("a@x.io"), make_user("b@x.io")
    p1 = make_product(a, serial="SN-1", invoice="INV-A")
    p2 = make_product(b, serial="SN-2", invoice="INV-B")
    same = png_bytes((1, 2, 3))
    c1, c2 = make_claim(p1), make_claim(p2)
    documents.store(upload(same, "p.png"), "damage_photo", claim=c1, uploader=a)
    _, info = documents.store(upload(same, "p.png"), "damage_photo", claim=c2, uploader=b)
    db.session.commit()
    assert info["reused_in"] and info["reused_in"][0]["reference"] == c1.claim_id
    assert "DOCUMENT_REUSED" in [i["code"] for i in duplicate_detector.check(c2)["indicators"]]


def test_invoice_reuse_and_open_claim_on_same_serial(app):
    a, b = make_user("a@x.io"), make_user("b@x.io")
    p1 = make_product(a, serial="SN-SAME", invoice="INV-777")
    p2 = make_product(b, serial="SN-SAME", invoice="inv 777")
    make_claim(p1, status="Manual Review", claim_submission_date=TODAY)
    c2 = make_claim(p2)
    r = duplicate_detector.check(c2)
    found = {i["code"] for i in r["indicators"]}
    assert {"INVOICE_REUSED", "OPEN_CLAIM_SAME_SERIAL", "SIMILAR_DESCRIPTION"} <= found
    assert r["duplicate_invoice"]


def test_closed_claim_on_same_unit_is_history_not_duplicate(app):
    a = make_user("a@x.io")
    p = make_product(a)
    old = make_claim(p, status="Closed", description="Screen stopped showing anything after an update.",
                     claim_submission_date=TODAY - timedelta(days=90))
    new = make_claim(p, description="Battery drains within an hour even when idle.")
    r = duplicate_detector.check(new)
    assert r["indicators"] == [] and r["previous_claims"] == [old.claim_id]


def test_missing_documents_follow_policy(app):
    u = make_user("m@x.io")
    c = make_claim(make_product(u))
    assert missing_mandatory(c) == ["receipt"]
    assert set(missing_supporting(c)) == {"warranty_card", "serial_photo", "damage_photo"}
    attach_docs(c, ("receipt", "damage_photo"))
    assert missing_mandatory(c) == [] and set(missing_supporting(c)) == {"warranty_card", "serial_photo"}


def test_product_level_receipt_counts_for_claims(app):
    u = make_user("r@x.io")
    p = make_product(u)
    documents.store(upload(standard_receipt(p), "r.pdf"), "receipt", product=p, uploader=u)
    db.session.commit()
    assert missing_mandatory(make_claim(p)) == []


def test_repair_serial_feeds_contradictions(app):
    u = make_user("s@x.io")
    p = make_product(u)
    add_repair(p, serial="SN-DIFFERENT-9")
    from src.core.pipeline import evaluate_claim
    c = make_claim(p, claim_submission_date=TODAY)
    evaluate_claim(c, upload_dir=app.config["UPLOAD_DIR"])
    assert any(f["code"] == "SERIAL_MISMATCH" for f in json.loads(c.rule_validation.contradictions_json))
