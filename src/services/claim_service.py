"""Claim lifecycle (SRS x, xxxvi-xxxix): submit -> evaluate -> route -> review -> close.

Routes call these functions; they own the status transitions, notifications
and audit rows so every entry point behaves the same way.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from flask import current_app

from config.config import Config
from src.core.features import missing_mandatory, missing_supporting
from src.core.pipeline import Outcome, evaluate_claim
from src.core.vocab import DOCUMENT_LABELS
from src.models.entities import ReviewerAction
from src.services.audit import audit
from src.services.notifications import notify

REVIEW_ACTIONS = {"approve": Config.STATUS_APPROVED, "reject": Config.STATUS_REJECTED,
                  "request_info": Config.STATUS_ADDITIONAL_INFO, "close": Config.STATUS_CLOSED,
                  "reopen_review": Config.STATUS_MANUAL_REVIEW}
# Reviewer outcomes that contradict the automated recommendation need an override reason.
OVERRIDES = {("Likely Valid", Config.STATUS_REJECTED), ("Likely Invalid", Config.STATUS_APPROVED)}


def _upload_dir() -> Path:
    return Path(current_app.config["UPLOAD_DIR"])


def submit(claim, actor) -> Outcome:
    """Draft / Additional-Information-Required -> Submitted -> Under Evaluation -> routed status."""
    first = claim.claim_submission_date is None
    claim.claim_submission_date = claim.claim_submission_date or date.today()
    claim.transition_status(Config.STATUS_SUBMITTED, actor.id,
                            "Claim submitted" if first else "Claim resubmitted with additional information")
    claim.transition_status(Config.STATUS_UNDER_EVALUATION, None, "Automated evaluation started")
    outcome = evaluate_claim(claim, upload_dir=_upload_dir(), actor=actor)
    d = outcome.decision
    claim.transition_status(outcome.next_status, None,
                            f"Automated recommendation {d['decision']} (rule {d['rule_id']}: {d['reason']})")
    audit("CLAIM_SUBMITTED", "Claim", claim.claim_id, user=actor, first_submission=first)

    owner = claim.user_id
    notify(owner, "claim_submission", f"Claim {claim.claim_id} received",
           f"Your claim for {claim.product.product_name} was submitted and evaluated.", claim=claim)
    notify(owner, "status_change", f"Claim {claim.claim_id}: {claim.status}",
           f"Recommendation: {d['decision']}. {d['reason']}.", claim=claim)
    required, recommended = missing_mandatory(claim), missing_supporting(claim)
    if required or recommended:
        text = []
        if required:
            text.append("Required: " + ", ".join(DOCUMENT_LABELS[m] for m in required) + ".")
        if recommended:
            text.append("Recommended: " + ", ".join(DOCUMENT_LABELS[m] for m in recommended) + ".")
        notify(owner, "missing_documents", f"Documents needed for {claim.claim_id}", " ".join(text), claim=claim)
    _outcome_notice(claim, owner, automated=True)
    return outcome


def reevaluate(claim, actor) -> Outcome:
    """Re-run the pipeline without changing status (e.g. after a model update, for comparison)."""
    outcome = evaluate_claim(claim, upload_dir=_upload_dir(), actor=actor)
    audit("CLAIM_REEVALUATED", "Claim", claim.claim_id, user=actor, decision=outcome.decision["decision"])
    return outcome


def _outcome_notice(claim, owner: int, automated: bool) -> None:
    who = "Automated evaluation" if automated else "The reviewer"
    if claim.status == Config.STATUS_APPROVED:
        notify(owner, "claim_approval", f"Claim {claim.claim_id} approved",
               f"{who} approved your claim for {claim.product.product_name}.", claim=claim)
        notify(owner, "review_complete", f"Review complete: {claim.claim_id}", "Outcome: Approved.", claim=claim)
    elif claim.status == Config.STATUS_REJECTED:
        notify(owner, "claim_rejection", f"Claim {claim.claim_id} rejected",
               f"{who} rejected your claim. Reason: {claim.decision_reason if automated else claim.reviewer_notes}",
               claim=claim)
        notify(owner, "review_complete", f"Review complete: {claim.claim_id}", "Outcome: Rejected.", claim=claim)


def is_override(claim, target_status: str) -> bool:
    return (claim.final_decision, target_status) in OVERRIDES


def decide(claim, reviewer, action: str, comments: str, override_reason: str | None) -> ReviewerAction:
    """Record a reviewer decision. Permission/SoD/transition checks happen in the route (authorize_object)."""
    from database.db import db
    target = REVIEW_ACTIONS[action]
    override = is_override(claim, target)
    previous = claim.status
    if claim.assigned_reviewer_id is None:
        claim.assigned_reviewer_id = reviewer.id
    row = ReviewerAction(claim=claim, reviewer_id=reviewer.id, previous_status=previous,
                         previous_recommendation=claim.final_decision, reviewer_decision=target,
                         is_override=override, override_reason=override_reason if override else None,
                         comments=comments)
    db.session.add(row)
    claim.reviewer_notes = comments
    claim.transition_status(target, reviewer.id, f"Reviewer: {comments}")
    audit("REVIEWER_DECISION", "Claim", claim.claim_id, user=reviewer, from_status=previous, to_status=target,
          ai_recommendation=claim.final_decision, override=override, override_reason=override_reason)
    owner = claim.user_id
    if target == Config.STATUS_ADDITIONAL_INFO:
        notify(owner, "additional_info_required", f"More information needed for {claim.claim_id}",
               f"Reviewer request: {comments}", claim=claim)
    else:
        notify(owner, "status_change", f"Claim {claim.claim_id}: {target}", f"Reviewer note: {comments}", claim=claim)
    _outcome_notice(claim, owner, automated=False)
    return row


def assign(claim, reviewer, actor) -> None:
    previous = claim.assigned_reviewer
    claim.assigned_reviewer_id = reviewer.id if reviewer else None
    audit("REVIEWER_ASSIGNED", "Claim", claim.claim_id, user=actor,
          reviewer=getattr(reviewer, "user_id", None), previous=getattr(previous, "user_id", None))
