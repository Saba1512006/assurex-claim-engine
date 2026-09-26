"""Manual-review workflow (SRS xxxvi, xxxvii): queue, take, decide/override, assign, re-evaluate."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from config.config import Config
from database.db import db
from src.core.features import FeatureError
from src.core.vocab import CATEGORIES, CONSISTENCY_STATUSES
from src.models.entities import Claim, Product, ReviewerAction, User
from src.security import rbac
from src.security.guards import authorize_object, check, require, scoped_claims
from src.services import claim_service

reviewer_bp = Blueprint("reviewer", __name__, url_prefix="/reviewer")
RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2, None: 3}
TABS = ("queue", "mine", "waiting", "decided")


def _claim(claim_id: str, permission: str, **ctx) -> Claim:
    return authorize_object(permission, Claim.query.filter_by(claim_id=claim_id).first_or_404(), **ctx)


@reviewer_bp.get("/queue")
@require("review.queue")
def queue():
    tab = request.args.get("tab") if request.args.get("tab") in TABS else "queue"
    base = scoped_claims(Claim)
    uid = g.user.id
    if tab == "queue":
        q = base.filter(Claim.status.in_([Config.STATUS_MANUAL_REVIEW, Config.STATUS_UNDER_EVALUATION]),
                        Claim.assigned_reviewer_id.is_(None))
    elif tab == "mine":
        q = base.filter(Claim.assigned_reviewer_id == uid,
                        Claim.status.in_([Config.STATUS_MANUAL_REVIEW, Config.STATUS_UNDER_EVALUATION]))
        if g.user.role == Config.ROLE_ADMIN:           # admins see every assigned open claim
            q = base.filter(Claim.assigned_reviewer_id.isnot(None),
                            Claim.status.in_([Config.STATUS_MANUAL_REVIEW, Config.STATUS_UNDER_EVALUATION]))
    elif tab == "waiting":
        q = base.filter(Claim.status == Config.STATUS_ADDITIONAL_INFO)
    else:
        decided_ids = db.session.query(ReviewerAction.claim_id)
        if g.user.role != Config.ROLE_ADMIN:
            decided_ids = decided_ids.filter(ReviewerAction.reviewer_id == uid)
        q = base.filter(Claim.id.in_(decided_ids))
    if request.args.get("category") in CATEGORIES:
        q = q.join(Product, Claim.product_id == Product.id).filter(Product.category == request.args["category"])
    if request.args.get("risk") in ("Low", "Medium", "High"):
        q = q.filter(Claim.risk_level == request.args["risk"])
    claims = q.all()
    if request.args.get("consistency") in CONSISTENCY_STATUSES:
        claims = [c for c in claims if c.model_evaluation and
                  c.model_evaluation.model_consistency_status == request.args["consistency"]]
    claims.sort(key=lambda c: (RISK_ORDER.get(c.risk_level, 3), c.claim_submission_date or date.today()))
    counts = {
        "queue": base.filter(Claim.status.in_([Config.STATUS_MANUAL_REVIEW, Config.STATUS_UNDER_EVALUATION]),
                             Claim.assigned_reviewer_id.is_(None)).count(),
        "mine": base.filter(Claim.assigned_reviewer_id == uid,
                            Claim.status.in_([Config.STATUS_MANUAL_REVIEW, Config.STATUS_UNDER_EVALUATION])).count(),
        "waiting": base.filter(Claim.status == Config.STATUS_ADDITIONAL_INFO).count(),
    }
    reviewers = User.query.filter_by(role=Config.ROLE_REVIEWER, is_active=True).order_by(User.full_name).all()
    return render_template("reviewer/queue.html", claims=claims, tab=tab, counts=counts, categories=CATEGORIES,
                           consistency_statuses=CONSISTENCY_STATUSES, reviewers=reviewers, today=date.today())


@reviewer_bp.post("/claims/<string:claim_id>/take")
@require("review.decide")
def take(claim_id):
    claim = _claim(claim_id, "review.decide")
    if claim.assigned_reviewer_id not in (None, g.user.id):
        flash("Another reviewer already has this claim.", "warning")
    else:
        claim_service.assign(claim, g.user, g.user)
        db.session.commit()
        flash(f"{claim.claim_id} is assigned to you.", "success")
    return redirect(url_for("claims.view_claim", claim_id=claim_id, _anchor="decision"))


@reviewer_bp.post("/claims/<string:claim_id>/decide")
@require("review.decide")
def decide(claim_id):
    action = request.form.get("action", "")
    comments = request.form.get("comments", "").strip()
    reason = request.form.get("override_reason", "").strip() or None
    back = redirect(url_for("claims.view_claim", claim_id=claim_id, _anchor="decision"))
    if action not in claim_service.REVIEW_ACTIONS:
        flash("Choose a decision.", "warning")
        return back
    claim = _claim(claim_id, "review.decide")          # scope + SoD (404 / 403)
    target = claim_service.REVIEW_ACTIONS[action]
    permission = "review.override" if claim_service.is_override(claim, target) else "review.decide"
    decision = check(permission, claim, target_status=target, reason=reason)
    if not decision:
        flash(rbac.MESSAGES.get(decision.code, "This decision isn't allowed."), "danger")
        return back
    if len(comments) < 5:
        flash("Add a comment for the customer and the audit trail (at least 5 characters).", "warning")
        return back
    claim_service.decide(claim, g.user, action, comments, reason)
    db.session.commit()
    flash(f"{claim.claim_id} is now {claim.status}.", "success")
    return back


@reviewer_bp.post("/claims/<string:claim_id>/assign")
@require("review.assign")
def assign(claim_id):
    claim = _claim(claim_id, "claim.read")
    code = request.form.get("reviewer", "")
    reviewer = User.query.filter_by(user_id=code, role=Config.ROLE_REVIEWER, is_active=True).first() if code else None
    if code and reviewer is None:
        flash("Choose an active claim reviewer.", "warning")
    elif reviewer and reviewer.id in {claim.user_id, claim.created_by_id}:
        flash(rbac.MESSAGES["SOD_OWN_CLAIM"], "warning")
    else:
        claim_service.assign(claim, reviewer, g.user)
        db.session.commit()
        flash(f"{claim.claim_id} assigned to {reviewer.full_name}." if reviewer else "Assignment cleared.", "success")
    return redirect(request.referrer or url_for("claims.view_claim", claim_id=claim_id))


@reviewer_bp.post("/claims/<string:claim_id>/reevaluate")
@require("review.decide")
def reevaluate(claim_id):
    """Re-run both models and all rules (e.g. after new evidence). Earlier evaluations are kept."""
    claim = _claim(claim_id, "review.decide")
    try:
        outcome = claim_service.reevaluate(claim, g.user)
    except FeatureError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    else:
        db.session.commit()
        flash(f"Re-evaluated: {outcome.decision['decision']} (rule {outcome.decision['rule_id']}). "
              "The status is unchanged until you decide.", "info")
    return redirect(url_for("claims.view_claim", claim_id=claim_id, _anchor="models"))
