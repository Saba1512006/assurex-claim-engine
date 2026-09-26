"""Contradiction detection (SRS xxvii, xxviii).

Compares what the claimant entered with what the evidence says: dates against
each other, and the registered serial number / model / purchase details
against values extracted from the receipt, warranty card, serial photo,
diagnostic report and repair records.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from src.core.vocab import try_parse_date

SERIAL_SOURCES = {"receipt": "receipt", "warranty_card": "warranty card", "serial_photo": "serial photo",
                  "diagnostic_report": "diagnostic report", "product_photo": "product photo"}
PLACEHOLDERS = {"", "N/A", "NA", "NONE", "UNKNOWN", "SN-UNKNOWN", "NULL"}


@dataclass
class Finding:
    code: str       # DATE_* | SERIAL_MISMATCH | MODEL_MISMATCH | PURCHASE_MISMATCH | INVOICE_MISMATCH
    message: str

    def to_dict(self):
        return {"code": self.code, "message": self.message}


def _norm(value) -> str:
    """Compare identifiers ignoring case, spaces and punctuation (OCR noise)."""
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _clean(value):
    v = str(value or "").strip()
    return None if v.upper() in PLACEHOLDERS else v


def detect(*, purchase_date: date | None, fault_date: date | None, submission_date: date | None,
           registered_serial: str | None, registered_model: str | None, registered_invoice: str | None,
           documents: list, repairs: list) -> dict:
    """documents: objects with document_type + get_ocr_payload(); repairs: objects with repair_date,
    serial_number_seen. Returns {"findings": [...], "date_conflict": bool, "serial_mismatch": bool,
    "serials_seen": {source: serial}}."""
    findings: list[Finding] = []
    submission_date = submission_date or date.today()

    # ---- chronology
    if purchase_date and submission_date < purchase_date:
        findings.append(Finding("DATE_CLAIM_BEFORE_PURCHASE",
                                f"Claim date {submission_date} is before the purchase date {purchase_date}."))
    if purchase_date and fault_date and fault_date < purchase_date:
        findings.append(Finding("DATE_FAULT_BEFORE_PURCHASE",
                                f"Fault date {fault_date} is before the purchase date {purchase_date}."))
    if fault_date and fault_date > submission_date:
        findings.append(Finding("DATE_FAULT_AFTER_CLAIM",
                                f"Fault date {fault_date} is after the claim date {submission_date}."))
    for rep in repairs:
        if purchase_date and rep.repair_date and rep.repair_date < purchase_date:
            findings.append(Finding("DATE_REPAIR_BEFORE_PURCHASE",
                                    f"Repair on {rep.repair_date} is dated before the purchase date {purchase_date}."))
    date_conflict = bool(findings)

    # ---- identifiers extracted from evidence
    serials_seen = {}
    reg_serial = _norm(registered_serial)
    for doc in documents:
        payload = doc.get_ocr_payload() or {}
        source = SERIAL_SOURCES.get(doc.document_type)
        sn = _clean(payload.get("serial_number"))
        if source and sn:
            serials_seen.setdefault(source, sn)
        if doc.document_type == "receipt":
            model = _clean(payload.get("model_number"))
            if model and registered_model and _norm(model) not in _norm(registered_model) \
                    and _norm(registered_model) not in _norm(model):
                findings.append(Finding("MODEL_MISMATCH",
                                        f"Receipt shows model '{model}' but the product is registered as '{registered_model}'."))
            inv = _clean(payload.get("invoice_number"))
            if inv and registered_invoice and _norm(inv) != _norm(registered_invoice):
                findings.append(Finding("INVOICE_MISMATCH",
                                        f"Receipt invoice number '{inv}' differs from the registered '{registered_invoice}'."))
            ocr_date = try_parse_date(payload.get("purchase_date"))
            if ocr_date and purchase_date and abs((ocr_date - purchase_date).days) > 3:
                findings.append(Finding("PURCHASE_MISMATCH",
                                        f"Receipt date {ocr_date} differs from the registered purchase date {purchase_date}."))
    for rep in repairs:
        sn = _clean(getattr(rep, "serial_number_seen", None))
        if sn:
            serials_seen.setdefault("repair record", sn)

    serial_mismatch = False
    for source, sn in serials_seen.items():
        if reg_serial and _norm(sn) != reg_serial:
            serial_mismatch = True
            findings.append(Finding("SERIAL_MISMATCH",
                                    f"Serial '{sn}' on the {source} does not match the registered serial '{registered_serial}'."))

    return {"findings": [f.to_dict() for f in findings], "date_conflict": date_conflict,
            "serial_mismatch": serial_mismatch, "serials_seen": serials_seen}
