"""Input validation (SRS xv) and claim-preparation assistance (SRS xxxiii).

Validators return (clean_values, errors, warnings). Errors block the action;
warnings are shown but do not block. Messages are written for the user.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.vocab import (CATEGORIES, DAMAGE_TYPES, DEFAULT_DIAGNOSTIC_CONFIDENCE, DOCUMENT_LABELS, FAULTS,
                            try_parse_date)
from src.rules.policy_store import get_policy

MAX_TEXT = {"product_name": 120, "brand": 60, "model_number": 60, "serial_number": 80, "retailer": 100,
            "invoice_number": 80, "warranty_provider": 100, "fault_description": 2000,
            "previous_replacement_details": 255}


def _text(form, key, label, errors, required=True, min_len=1):
    value = (form.get(key) or "").strip()
    if required and len(value) < min_len:
        errors.append(f"{label} is required." if min_len == 1 else f"{label} needs at least {min_len} characters.")
    if len(value) > MAX_TEXT.get(key, 255):
        errors.append(f"{label} can be at most {MAX_TEXT.get(key, 255)} characters.")
    return value


def product_form(form, today: date | None = None) -> tuple[dict, list, list]:
    today = today or date.today()
    e, w, v = [], [], {}
    v["product_name"] = _text(form, "product_name", "Product name", e)
    v["brand"] = _text(form, "brand", "Brand", e)
    v["model_number"] = _text(form, "model_number", "Model number", e)
    v["serial_number"] = _text(form, "serial_number", "Serial number", e, min_len=4).upper()
    v["retailer"] = _text(form, "retailer", "Retailer", e)
    v["invoice_number"] = _text(form, "invoice_number", "Invoice number", e, required=False) or None
    v["warranty_provider"] = _text(form, "warranty_provider", "Warranty provider", e, required=False)
    v["category"] = form.get("category", "")
    if v["category"] not in CATEGORIES:
        e.append("Choose a product category.")
    raw_date = form.get("purchase_date", "")
    v["purchase_date"] = try_parse_date(raw_date)
    if v["purchase_date"] is None:
        e.append("Enter the purchase date (for example 2025-03-15 or 15/03/2025).")
    elif v["purchase_date"] > today:
        e.append("The purchase date can't be in the future.")
    elif v["purchase_date"] < today - timedelta(days=365 * 15):
        e.append("The purchase date is more than 15 years ago; check the year.")
    try:
        v["purchase_price"] = round(float(str(form.get("purchase_price", "")).replace(",", "")), 2)
        if not 0 < v["purchase_price"] <= 1_000_000:
            e.append("Enter a purchase price between 0 and 1,000,000.")
    except ValueError:
        v["purchase_price"] = None
        e.append("Enter the purchase price as a number.")
    v["is_extended"] = form.get("warranty_type") == "extended"
    policy = get_policy(v["category"]) if v["category"] in CATEGORIES else None
    try:
        months = int(form.get("warranty_months") or (policy["coverage_duration_months"] if policy else 12))
        if not 1 <= months <= 120:
            raise ValueError
        v["warranty_months"] = months
    except ValueError:
        v["warranty_months"] = None
        e.append("Warranty length must be a whole number of months between 1 and 120.")
    if policy and v.get("warranty_months") and v["is_extended"] and v["warranty_months"] <= min(policy["standard_terms_months"]):
        w.append("An extended warranty is usually longer than the standard term; check the months.")
    return v, e, w


def claim_form(form, product, *, is_staff: bool, today: date | None = None) -> tuple[dict, list, list]:
    today = today or date.today()
    e, w, v = [], [], {}
    category = product.category if product else None
    v["fault_category"] = form.get("fault_category", "")
    if category and v["fault_category"] not in FAULTS.get(category, ()):
        e.append("Choose the fault from the list for this product category.")
    v["damage_type"] = form.get("damage_type", "")
    if v["damage_type"] not in DAMAGE_TYPES:
        e.append("Choose what caused the damage (pick 'Unknown / Not Sure' if you don't know).")
    v["fault_description"] = _text(form, "fault_description", "Fault description", e, min_len=15)
    v["previous_replacement_details"] = _text(form, "previous_replacement_details", "Previous replacement", e,
                                              required=False) or None
    v["fault_occurrence_date"] = try_parse_date(form.get("fault_occurrence_date", ""))
    if v["fault_occurrence_date"] is None:
        e.append("Enter the date the fault started.")
    elif v["fault_occurrence_date"] > today:
        e.append("The fault date can't be in the future.")
    elif product and v["fault_occurrence_date"] < product.purchase_date:
        w.append("The fault date is before the purchase date. The claim will be checked for contradictions.")
    raw_conf = (form.get("diagnostic_confidence") or "").strip()
    if raw_conf:
        try:
            conf = float(raw_conf)
            conf = conf / 100 if conf > 1 else conf
            if not 0 <= conf <= 1:
                raise ValueError
            v["diagnostic_confidence"], v["diagnosis_source"] = round(conf, 3), \
                "Service-center technician" if is_staff else "Diagnostic report (customer entered)"
        except ValueError:
            e.append("Diagnostic confidence must be a number between 0 and 1 (or 0-100%).")
    else:
        v["diagnostic_confidence"], v["diagnosis_source"] = DEFAULT_DIAGNOSTIC_CONFIDENCE, "Not assessed"
    return v, e, w


def readiness(product, form, present_docs: set, today: date | None = None) -> dict:
    """Pre-submission guidance: missing fields/documents, deadlines, contradictions, next actions."""
    today = today or date.today()
    items = []

    def add(level, title, detail):
        items.append({"level": level, "title": title, "detail": detail})

    if product is None:
        add("error", "Choose a product", "Pick the registered product this claim is about.")
        return {"items": items, "ready": False, "score": 0}
    policy = get_policy(product.category)
    values, errors, warnings = claim_form(form, product, is_staff=False, today=today)
    for msg in errors:
        add("error", "Missing or invalid information", msg)
    for msg in warnings:
        add("warning", "Check this", msg)
    for doc in policy["mandatory_documents"]:
        if doc not in present_docs:
            add("error", f"{DOCUMENT_LABELS[doc]} required",
                "Without it the claim cannot be decided automatically and goes to manual review.")
    gaps = [d for d in policy["supporting_documents"] if d not in present_docs]
    for doc in gaps:
        add("warning" if len(gaps) >= 2 else "info", f"{DOCUMENT_LABELS[doc]} recommended",
            "Two or more missing supporting documents send the claim to manual review.")
    w = product.warranty
    if w is None:
        add("error", "No warranty on file", "Add the warranty to this product before filing a claim.")
    else:
        left = (w.expiry_date - today).days
        if left < -policy["grace_period_days"]:
            add("error", "Warranty has ended",
                f"It ended on {w.expiry_date:%d %b %Y}, beyond the {policy['grace_period_days']}-day grace period. "
                "The claim is likely to be rejected.")
        elif left < 0:
            add("warning", "Inside the grace period",
                f"The warranty ended {-left} days ago; a reviewer will decide.")
        elif left <= 30:
            add("info", "Warranty ends soon", f"{left} days left — submit before {w.expiry_date:%d %b %Y}.")
    fault = values.get("fault_occurrence_date")
    if fault:
        limit = policy["claim_reporting_period_days"]
        waited = (today - fault).days
        if waited > limit:
            add("error", "Reporting deadline passed",
                f"Faults must be reported within {limit} days; this one is {waited} days old.")
        elif waited > limit - 7:
            add("warning", "Reporting deadline close", f"Only {limit - waited} day(s) left to report this fault.")
    if values.get("damage_type") in set(policy["excluded_damage_types"]):
        add("warning", "Excluded cause", f"'{values['damage_type']}' is excluded for {product.category}. "
            "If a technician found a different cause, attach the diagnostic report.")
    if any(not r.is_authorized_center for r in product.repair_records):
        add("warning", "Unauthorised repair on record", "Earlier work by an unauthorised center usually voids cover.")
    blocking = sum(1 for i in items if i["level"] == "error")
    score = max(0, 100 - 30 * blocking - 10 * sum(1 for i in items if i["level"] == "warning"))
    return {"items": items, "ready": blocking == 0, "score": score}
