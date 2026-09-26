"""Claim pre-processing and feature engineering (SRS Step 3, xvi).

Turns a stored claim (product, warranty, documents, repairs, detector results)
into the exact feature record the Python model was trained on, plus the extra
fields the Claim Summary Card and the rule engine need. The same column names
and vocabularies are produced by dataset_generator/generator_v2.py, so there is
no train/serve skew (pinned by tests/test_ml_integrity.py).

Pre-processing steps, in order:
  1. date conversion      - every date parsed with vocab.parse_date (all configured formats)
  2. missing values       - absent documents -> 0, no repairs -> 0, no diagnosis -> neutral prior
  3. derived fields       - product age, days to expiry, remaining warranty, reporting delay,
                            missing-document count, repair count, conflict/mismatch/duplicate flags
  4. categorical checks   - category / damage type must be in the training vocabulary
  5. encoding + scaling   - done inside the saved sklearn Pipeline (OneHotEncoder with fixed
                            categories; StandardScaler for the linear candidate)
"""
from __future__ import annotations

from datetime import date

from src.core.vocab import (CATEGORIES, DAMAGE_TYPES, DEFAULT_DIAGNOSTIC_CONFIDENCE, MANDATORY_DOCUMENTS,
                            normalise_category)

NUMERIC = ["purchase_price", "warranty_duration_months", "product_age_days", "days_to_expiry",
           "reporting_delay_days", "diagnostic_confidence", "previous_repairs_count", "missing_document_count"]
BINARY = ["is_extended_warranty", "has_receipt", "has_warranty_card", "has_damage_photo", "has_serial_photo",
          "has_repair_report", "serial_number_match", "unauthorized_repair_flag", "duplicate_invoice_flag",
          "claim_date_conflict_flag"]
CATEGORICAL = ["product_category", "damage_type"]
MODEL_FEATURES = NUMERIC + BINARY + CATEGORICAL

DOC_FLAGS = {"has_receipt": "receipt", "has_warranty_card": "warranty_card",
             "has_damage_photo": "damage_photo", "has_serial_photo": "serial_photo"}


class FeatureError(ValueError):
    """Input cannot be turned into a valid model record (shown to the user, never a stack trace)."""


def present_document_types(claim) -> set:
    """Documents on the claim plus product-level documents (receipt/warranty card uploaded at registration)."""
    types = {d.document_type for d in claim.documents}
    types |= {d.document_type for d in claim.product.documents if d.claim_id is None}
    return types


def missing_mandatory(claim) -> list:
    """Documents the category policy makes mandatory (a gap routes the claim to manual review, rule D03)."""
    from src.rules.policy_store import mandatory_documents
    have = present_document_types(claim)
    return [d for d in mandatory_documents(claim.product.category) if d not in have]


def missing_supporting(claim) -> list:
    """Recommended documents that are absent (drive the evidence rules, never block on their own)."""
    from src.rules.policy_store import supporting_documents
    have = present_document_types(claim)
    return [d for d in supporting_documents(claim.product.category) if d not in have]


def build(claim, *, contradictions: dict, duplicates: dict, on_date: date | None = None) -> dict:
    """Feature record for one claim. `contradictions`/`duplicates` are detector outputs."""
    product, warranty = claim.product, claim.warranty or claim.product.warranty
    if warranty is None:
        raise FeatureError("This product has no warranty record. Add the warranty before submitting a claim.")
    try:
        category = normalise_category(product.category)
    except ValueError as exc:
        raise FeatureError(str(exc)) from None
    if claim.damage_type not in DAMAGE_TYPES:
        raise FeatureError(f"Unknown damage type '{claim.damage_type}'. Choose one of the listed causes.")

    submitted = claim.claim_submission_date or on_date or date.today()
    purchase = product.purchase_date
    fault = claim.fault_occurrence_date
    docs = present_document_types(claim)
    prior_repairs = [r for r in product.repair_records if r.claim_id != claim.id and r.repair_date <= submitted]

    flags = {k: int(v in docs) for k, v in DOC_FLAGS.items()}
    record = {
        "claim_id": claim.claim_id,
        "product_category": category,
        "damage_type": claim.damage_type,
        "fault_category": claim.fault_category,
        "fault_description": claim.fault_description,
        "previous_replacement_details": claim.previous_replacement_details or "",
        "purchase_date": purchase.isoformat(),
        "warranty_expiry_date": warranty.expiry_date.isoformat(),
        "fault_occurrence_date": fault.isoformat(),
        "claim_submission_date": submitted.isoformat(),
        # numeric
        "purchase_price": float(product.purchase_price or 0.0),
        "warranty_duration_months": int(warranty.duration_months),
        "product_age_days": max(0, (submitted - purchase).days),
        "days_to_expiry": (warranty.expiry_date - submitted).days,
        "reporting_delay_days": max(0, (submitted - fault).days),
        "diagnostic_confidence": float(claim.diagnostic_confidence
                                       if claim.diagnostic_confidence is not None else DEFAULT_DIAGNOSTIC_CONFIDENCE),
        "previous_repairs_count": len(prior_repairs),
        "missing_document_count": sum(1 - v for v in flags.values()),
        # binary
        "is_extended_warranty": int(bool(warranty.is_extended)),
        **flags,
        "has_repair_report": int("diagnostic_report" in docs),
        "serial_number_match": int(not contradictions.get("serial_mismatch")),
        "unauthorized_repair_flag": int(any(not r.is_authorized_center for r in prior_repairs)),
        "duplicate_invoice_flag": int(bool(duplicates.get("duplicate_invoice"))),
        "claim_date_conflict_flag": int(bool(contradictions.get("date_conflict"))),
    }
    record["remaining_warranty_days"] = max(0, record["days_to_expiry"])
    validate(record)
    return record


def validate(record: dict) -> None:
    """Fail loudly on anything the model has never seen (instead of silently mis-encoding it)."""
    missing = [f for f in MODEL_FEATURES if f not in record]
    if missing:
        raise FeatureError(f"Missing model inputs: {', '.join(missing)}")
    if record["product_category"] not in CATEGORIES:
        raise FeatureError(f"Unknown product category '{record['product_category']}'.")
    if not 0.0 <= record["diagnostic_confidence"] <= 1.0:
        raise FeatureError("Diagnostic confidence must be between 0 and 1.")
    for b in BINARY:
        if record[b] not in (0, 1):
            raise FeatureError(f"{b} must be 0 or 1.")
    assert set(DOC_FLAGS.values()) == set(MANDATORY_DOCUMENTS)
