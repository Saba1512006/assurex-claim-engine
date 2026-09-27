"""JSON endpoints for live UI parts. Every response uses the envelope in src/api/errors.py."""
from __future__ import annotations

import base64

from flask import Blueprint, g, request, url_for

from config.config import Config
from database.db import db
from src.api.errors import ErrorCode, fail, ok
from src.app_security import limiter
from src.models.entities import Claim
from src.rules import validator
from src.security.guards import authorize_object, require
from src.services import demo_bench, verdict

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/claims/<string:claim_id>/evaluation")
@require("claim.read")
def claim_evaluation(claim_id):
    """Stored verdict payload (never re-runs a model), or the pending stages while evaluation runs."""
    claim = authorize_object("claim.read", Claim.query.filter_by(claim_id=claim_id).first_or_404())
    return ok(verdict.api_payload(claim))


@api_bp.post("/demo/evaluate")
@limiter.limit("10/minute")
def demo_evaluate():
    """Public: run the real pipeline on one allow-listed sample claim. Writes nothing to the database."""
    case = (request.get_json(silent=True) or {}).get("case")
    if case not in demo_bench.CASES:
        return fail(ErrorCode.VALIDATION_FAILED, fields={"case": f"Choose one of: {', '.join(demo_bench.CASES)}."})
    out = demo_bench.evaluate(case)
    payload = out["payload"]
    payload["gtm"]["card_url"] = "data:image/png;base64," + base64.b64encode(out["card_bytes"]).decode()
    return ok({"case": case, "title": out["sample"]["title"], "payload": payload, "meter": verdict.meter(payload),
               "view": demo_bench.view(case, payload)})


@api_bp.post("/claims/draft")
@require("claim.create")
@limiter.limit("60/minute")
def autosave_draft():
    """Wizard autosave: create the Draft once step 2 is valid, then keep it in step with the form. Never submits."""
    from src.api.claims import _eligible_products, save_draft
    form = request.form
    product = next((p for p in _eligible_products() if p.product_id == form.get("product_id")), None)
    if product is None:
        return fail(ErrorCode.VALIDATION_FAILED, fields={"product_id": "Choose one of your registered products."})
    authorize_object("claim.create", product)
    values, errors, _ = validator.claim_form(form, product, is_staff=g.user.role == Config.ROLE_STAFF)
    if errors:
        return fail(ErrorCode.VALIDATION_FAILED, " ".join(errors))
    claim = save_draft(product, values, form.get("draft_id"))
    db.session.commit()
    return ok({"claim_id": claim.claim_id, "saved_at": claim.updated_at.strftime("%H:%M"),
               "url": url_for("claims.view_claim", claim_id=claim.claim_id)})


@api_bp.post("/admin/what-if")
@require("settings.manage")
@limiter.limit("60/minute")
def what_if():
    """Replay decisions under proposed thresholds. Read-only: nothing is saved."""
    from src.services import whatif
    try:
        return ok(whatif.simulate(request.get_json(silent=True) or {}))
    except whatif.WhatIfError as exc:
        return fail(ErrorCode.VALIDATION_FAILED, str(exc))


def _batch_payload(b):
    from src.services import batch as batch_service
    return {**batch_service.summary(b), "step_url": url_for("api.batch_step", batch_id=b.batch_id),
            "csv_url": url_for("admin.batch_csv", batch_id=b.batch_id)}


@api_bp.post("/admin/batch")
@require("settings.manage")
@limiter.limit("3/hour")
def batch_create():
    """Validate an uploaded CSV and queue it; the page then calls the step endpoint until it is done."""
    from src.services import batch as batch_service
    from src.services.audit import audit
    try:
        filename, rows = batch_service.parse(request.files.get("file"))
    except batch_service.BatchError as exc:
        return fail(ErrorCode.VALIDATION_FAILED, str(exc), fields={"file": str(exc), "rows": exc.rows})
    b = batch_service.create(g.user, filename, rows)
    audit("BATCH_CREATED", "BatchRun", b.batch_id, rows=len(rows), filename=filename)
    db.session.commit()
    return ok(_batch_payload(b), status=201)


@api_bp.post("/admin/batch/<string:batch_id>/step")
@require("settings.manage")
@limiter.limit("120/minute")
def batch_step(batch_id):
    from src.models.entities import BatchRun
    from src.services import batch as batch_service
    from src.services.audit import audit
    b = BatchRun.query.filter_by(batch_id=batch_id).first()
    if b is None:
        return fail(ErrorCode.NOT_FOUND)
    was = b.status
    batch_service.step(b)
    if b.status != was and b.status in ("done", "failed"):
        audit("BATCH_COMPLETED" if b.status == "done" else "BATCH_FAILED", "BatchRun", b.batch_id,
              **{k: v for k, v in batch_service.summary(b).items() if k in ("processed", "decision_accuracy", "error")})
    db.session.commit()
    return ok(_batch_payload(b))
