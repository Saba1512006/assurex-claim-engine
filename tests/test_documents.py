"""Upload validation, storage, SHA-256 and OCR extraction (SRS v, vi, vii, xv, xxxi)."""
import hashlib

import pytest

from database.db import db
from src.ocr.document_processor import looks_like_receipt, parse_entities
from src.services import documents
from src.services.documents import UploadError
from tests.conftest import make_product, make_user, png_bytes, receipt_pdf, upload


@pytest.mark.parametrize("data,name,kind,message", [
    (b"\x89PNG\r\n\x1a\n" + b"0" * 10, "tiny.png", "damage_photo", "empty or damaged"),
    (b"GIF89a" + b"0" * 200, "photo.png", "damage_photo", "only PDF, JPG"),
    (b"%PDF-1.4" + b"0" * 200, "photo.png", "damage_photo", "does not match"),
    (b"MZ" + b"0" * 200, "virus.pdf", "receipt", "only PDF, JPG"),
])
def test_invalid_files_are_refused(app, data, name, kind, message):
    with pytest.raises(UploadError, match=message):
        documents.validate(upload(data, name), kind)


def test_oversized_file_is_refused(app):
    big = b"%PDF-1.4" + b"0" * (10 * 1024 * 1024 + 1)
    with pytest.raises(UploadError, match="at most 10 MB"):
        documents.validate(upload(big, "big.pdf"), "receipt")


def test_video_only_for_fault_video(app):
    mp4 = b"\x00\x00\x00\x18ftypmp42" + b"0" * 200
    documents.validate(upload(mp4, "v.mp4"), "fault_video")
    with pytest.raises(UploadError):
        documents.validate(upload(mp4, "v.mp4"), "damage_photo")


def test_stored_file_is_hashed_and_named_safely(app):
    u = make_user("u@x.io")
    p = make_product(u)
    data = png_bytes()
    doc, info = documents.store(upload(data, "../../etc/passwd.png"), "product_photo", product=p, uploader=u)
    db.session.commit()
    assert doc.file_hash_sha256 == hashlib.sha256(data).hexdigest()
    assert doc.file_path.startswith("docs/") and ".." not in doc.file_path
    assert doc.original_filename == "passwd.png"
    assert documents.absolute_path(doc).read_bytes() == data


def test_pdf_receipt_is_read_by_ocr(app):
    u = make_user("u@x.io")
    p = make_product(u)
    pdf = receipt_pdf(["CITY STORE", "Invoice No: INV-2025-555", "Date: 15/03/2025", "Model: ABP-16",
                       "Serial No: SN-APX-12345", "Grand Total: 1,899.00"])
    doc, info = documents.store(upload(pdf, "r.pdf"), "receipt", product=p, uploader=u)
    assert info["ocr_status"] == "ok"
    e = doc.get_ocr_payload()
    assert e["invoice_number"] == "INV-2025-555" and e["serial_number"] == "SN-APX-12345"
    assert e["purchase_date"] == "2025-03-15" and e["purchase_amount"] == 1899.0


def test_text_pdf_without_invoice_details_is_not_accepted_as_receipt(app):
    u = make_user("u@x.io")
    p = make_product(u)
    pdf = receipt_pdf(["Holiday photos from the beach", "Nothing to see here"])
    with pytest.raises(UploadError, match="no invoice details"):
        documents.store(upload(pdf, "r.pdf"), "receipt", product=p, uploader=u)


def test_image_receipt_accepted_when_ocr_engine_missing(app, monkeypatch):
    monkeypatch.setattr("src.ocr.document_processor.tesseract_available", lambda: False)
    u = make_user("u@x.io")
    doc, info = documents.store(upload(png_bytes(), "r.png"), "receipt", product=make_product(u), uploader=u)
    assert info["ocr_status"] == "unavailable" and doc.get_ocr_payload() == {}


@pytest.mark.parametrize("text,key,value", [
    ("Invoice # 88213", "invoice_number", "88213"),
    ("Tax Invoice No: INV-2026-00017", "invoice_number", "INV-2026-00017"),
    ("Date of purchase: 03 Apr 2026", "purchase_date", "2026-04-03"),
    ("Date: 2026-04-03", "purchase_date", "2026-04-03"),
    ("Serial number: X99-221", "serial_number", "X99-221"),
    ("Total Amount: Rs 12,500.50", "purchase_amount", 12500.5),
    ("Warranty: 2 years", "warranty_duration_months", 24),
    ("Retailer: Metro Hardware Centre", "retailer", "Metro Hardware Centre"),
])
def test_entity_patterns(text, key, value):
    assert parse_entities(text)[key] == value


def test_words_are_not_mistaken_for_identifiers():
    e = parse_entities("INVOICE\nSerial number: see label\nThank you")
    assert e["invoice_number"] is None and e["serial_number"] is None
    assert not looks_like_receipt(e)
