"""Claim summary (SRS xxxii) and decision explanation (SRS xxxv).

Both are generated from the stored evaluation, rule log and claim records with
plain templates: deterministic, reproducible and free of any external
generative-AI service (SRS 1.10.15 forbids an external API deciding claims).
"""
from __future__ import annotations

from datetime import date

from src.core.features import missing_mandatory, missing_supporting, present_document_types
from src.core.vocab import DOCUMENT_LABELS

REQUEST = {
    "receipt": "Upload the purchase receipt or tax invoice showing date, retailer and amount.",
    "warranty_card": "Upload the warranty card or certificate.",
    "serial_photo": "Upload a clear photo of the serial-number label.",
    "damage_photo": "Upload a photo (or video) that shows the fault or damage.",
}


def _fmt(d):
    return d.strftime("%d %b %Y") if d else "—"


def summarise(claim) -> dict:
    """Short, human-readable brief of the whole claim."""
    p, w = claim.product, claim.warranty or claim.product.warranty
    ev, log = claim.model_evaluation, claim.rule_validation
    on = claim.claim_submission_date or date.today()
    docs = present_document_types(claim)
    repairs = [r for r in p.repair_records if r.claim_id != claim.id]
    unauthorised = sum(1 for r in repairs if not r.is_authorized_center)

    if w is None:
        cover = "has no warranty on file"
    else:
        left = (w.expiry_date - on).days
        cover = (f"was {left} days from the end of its {w.duration_months}-month{' extended' if w.is_extended else ''} "
                 f"warranty ({_fmt(w.expiry_date)})" if left >= 0 else
                 f"was {-left} days past the end of its warranty ({_fmt(w.expiry_date)})")
    age = (on - p.purchase_date).days
    parts = [
        f"{claim.claimant.full_name} reports “{claim.fault_category}” on a {p.brand} {p.product_name} "
        f"(serial {p.serial_number}), bought {_fmt(p.purchase_date)} — {age} days before the claim. "
        f"The product {cover}.",
        f"Cause given: {claim.damage_type.lower()}; the fault started {_fmt(claim.fault_occurrence_date)}"
        + (f", {max(0, (on - claim.fault_occurrence_date).days)} days before it was reported." if claim.claim_submission_date else "."),
        (f"{len(repairs)} earlier repair{'s' if len(repairs) != 1 else ''} on record"
         + (f", {unauthorised} by an unauthorised center." if unauthorised else ", all by authorised centers.")) if repairs
        else "No earlier repairs on record.",
        f"Evidence: {len(docs)} document type{'s' if len(docs) != 1 else ''} provided"
        + (f"; missing {', '.join(DOCUMENT_LABELS[m].lower() for m in gaps)}." if (gaps := missing_mandatory(claim)
           + missing_supporting(claim)) else "; every required and recommended document is present."),
    ]
    issues = []
    if log:
        issues += [r.get("description") or r["title"] for r in log.of("hard_fail") + log.of("manual_review")]
        issues += [c["message"] for c in log.contradictions][:2]
        issues += [d["message"] for d in log.duplicate_flags][:2]
    if ev:
        py = f"{ev.python_predicted_class} ({ev.python_top:.0%})" if ev.python_available else "unavailable"
        gt = f"{ev.gtm_predicted_class} ({ev.gtm_top:.0%})" if ev.gtm_available else "unavailable"
        parts.append(f"Python model: {py}; Teachable Machine: {gt}; consistency: {ev.model_consistency_status}.")
    if issues:
        parts.append("Issues found: " + "; ".join(issues) + ".")
    parts.append(f"Current status: {claim.status}" + (f", recommendation {claim.final_decision}." if claim.final_decision else "."))
    return {"text": " ".join(parts), "issues": issues, "documents": sorted(docs)}


def explain(claim) -> dict:
    """Factors for and against the recommendation, rules passed/failed, contradictions, evidence still needed."""
    ev, log = claim.model_evaluation, claim.rule_validation
    support, oppose = [], []
    if ev:
        if ev.python_available:
            (support if ev.python_predicted_class == "Valid Claim" else oppose).append(
                f"Python model predicts {ev.python_predicted_class} with {ev.python_top:.0%} confidence.")
        else:
            oppose.append("Python model was unavailable for this evaluation.")
        if ev.gtm_available:
            (support if ev.gtm_predicted_class == "Valid Claim" else oppose).append(
                f"Teachable Machine predicts {ev.gtm_predicted_class} with {ev.gtm_top:.0%} confidence.")
        else:
            oppose.append("Teachable Machine model was unavailable, so the two models could not be compared.")
        if ev.model_consistency_status in ("Strong Match", "Acceptable Match"):
            support.append(f"The models agree ({ev.model_consistency_status}, difference "
                           f"{ev.top_confidence_difference:.2f}).")
        else:
            oppose.append(f"Model consistency: {ev.model_consistency_status}. {ev.thresholds.get('explanation', '')}")
    passed, failed = [], []
    if log:
        for r in log.rules:
            (failed if r["fired"] else passed).append(r)
        for r in failed:
            oppose.append(r["message"])
        if not failed:
            support.append("Every enabled warranty rule passed.")
        if not log.contradictions:
            support.append("Dates and identifiers are consistent across the evidence.")
        if not log.duplicate_flags:
            support.append("No duplicate claim or reused document was found.")
    needed = [REQUEST.get(m, f"Upload the {DOCUMENT_LABELS[m].lower()}.")
              for m in missing_mandatory(claim) + missing_supporting(claim)]
    if log and any(r["rule_id"] in ("EXCLUDED_DAMAGE_UNCONFIRMED", "UNKNOWN_CAUSE") for r in failed):
        needed.append("A technician's diagnostic report confirming the cause of the fault.")
    if log and any(r["rule_id"] == "SERIAL_UNVERIFIED" for r in failed):
        needed.append("A receipt and serial photo that show the same serial number.")
    return {"decision": claim.final_decision, "rule_id": claim.decision_rule_id, "reason": claim.decision_reason,
            "supporting": support, "opposing": oppose, "passed": passed, "failed": failed,
            "contradictions": log.contradictions if log else [], "duplicates": log.duplicate_flags if log else [],
            "evidence_needed": needed, "trace": ev.decision_trace if ev else []}
