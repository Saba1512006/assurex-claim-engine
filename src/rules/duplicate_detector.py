"""Duplicate claim and duplicate document detection (SRS xxx, xxxi).

Indicators compare the claim with every other record: SHA-256 hashes of the
uploaded files, invoice numbers, product serial numbers, fault descriptions,
the claimant and previous claims. Claim IDs are generated server-side and
unique by constraint, so an ID collision cannot occur.
"""
from __future__ import annotations

import difflib
import re
from datetime import timedelta

from src.models.entities import Claim, ClaimDocument, Product

CLOSED = {"Closed", "Rejected"}
SIMILARITY = 0.9


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _norm_id(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def document_reuse(file_hash: str, *, exclude_claim_id: int | None = None,
                   exclude_product_id: int | None = None) -> list:
    """Other claims/products that already hold a file with this exact SHA-256."""
    q = ClaimDocument.query.filter(ClaimDocument.file_hash_sha256 == file_hash)
    hits = []
    for d in q.all():
        if exclude_claim_id and d.claim_id == exclude_claim_id:
            continue
        if d.claim_id is None and exclude_product_id and d.product_id == exclude_product_id:
            continue
        ref = d.claim.claim_id if d.claim else (d.product.product_id if d.product else d.document_id)
        hits.append({"document_id": d.document_id, "document_type": d.document_type, "reference": ref})
    return hits


def check(claim: Claim) -> dict:
    """Return {"indicators": [{code, message, related}], "duplicate_invoice": bool, "previous_claims": [ids]}."""
    product = claim.product
    indicators = []
    duplicate_invoice = False

    # 1. identical files already used elsewhere (receipt reused for another product/claim)
    for doc in claim.documents + [d for d in product.documents if d.claim_id is None]:
        hits = document_reuse(doc.file_hash_sha256, exclude_claim_id=claim.id, exclude_product_id=product.id)
        if hits:
            refs = sorted({h["reference"] for h in hits})
            indicators.append({"code": "DOCUMENT_REUSED", "related": refs,
                               "message": f"The same {doc.document_type.replace('_', ' ')} file was already used in {', '.join(refs)}."})
            if doc.document_type == "receipt":
                duplicate_invoice = True

    # 2. invoice number reused on a different product (registered or read from the receipt)
    invoices = {_norm_id(product.invoice_number)} if product.invoice_number else set()
    for doc in claim.documents + product.documents:
        if doc.document_type == "receipt":
            inv = (doc.get_ocr_payload() or {}).get("invoice_number")
            if inv:
                invoices.add(_norm_id(inv))
    invoices.discard("")
    if invoices:
        others = [p for p in Product.query.filter(Product.id != product.id, Product.invoice_number.isnot(None)).all()
                  if _norm_id(p.invoice_number) in invoices]
        if others:
            duplicate_invoice = True
            refs = sorted(p.product_id for p in others)
            indicators.append({"code": "INVOICE_REUSED", "related": refs,
                               "message": f"Invoice number is already registered to another product ({', '.join(refs)})."})

    # 3-5. other claims on the same physical unit (same serial, any owner)
    same_serial = Product.query.filter(Product.serial_number == product.serial_number).all()
    previous = [c for p in same_serial for c in p.claims if c.id != claim.id and c.status != "Draft"]
    for other in previous:
        if other.status not in CLOSED:
            indicators.append({"code": "OPEN_CLAIM_SAME_SERIAL", "related": [other.claim_id],
                               "message": f"Claim {other.claim_id} for serial {product.serial_number} is still open ({other.status})."})
        ratio = difflib.SequenceMatcher(None, _norm_text(other.fault_description),
                                        _norm_text(claim.fault_description)).ratio()
        if ratio >= SIMILARITY:
            indicators.append({"code": "SIMILAR_DESCRIPTION", "related": [other.claim_id],
                               "message": f"Fault description is {ratio:.0%} identical to claim {other.claim_id} on the same unit."})
        if other.user_id == claim.user_id and other.fault_category == claim.fault_category and \
                other.claim_submission_date and claim.claim_submission_date and \
                abs(claim.claim_submission_date - other.claim_submission_date) <= timedelta(days=30):
            indicators.append({"code": "REPEAT_BY_CLAIMANT", "related": [other.claim_id],
                               "message": f"Same claimant filed {other.claim_id} for the same fault within 30 days."})
    return {"indicators": indicators, "duplicate_invoice": duplicate_invoice,
            "previous_claims": sorted(c.claim_id for c in previous)}
