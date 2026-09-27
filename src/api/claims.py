"""Claims: dashboard, intake wizard, detail, tracking, evidence, search (SRS x-xvi, xxxii-xxxv, xxxviii-xlii, xliv)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request,
                   send_file, url_for)

from config.config import Config
from database.db import db
from src.core.features import FeatureError, missing_mandatory, missing_supporting, present_document_types
from src.core.vocab import CATEGORIES, DAMAGE_TYPES, DOCUMENT_LABELS, FAULTS, try_parse_date
from src.models.entities import (Claim, ClaimDocument, ClaimStatusHistory, ModelEvaluation, Notification, Product, ProductWarranty,
                                 User)
from src.rules import validator
from src.rules.policy_store import get_policy
from src.api.errors import ok
from src.security import rbac
from src.security.guards import authorize_object, check, require, scoped_claims, scoped_products
from src.services import analytics_service, claim_service, documents as doc_service, export_service, verdict
from src.services.alert_service import alert_days, dispatch_expiry_alerts
from src.services import receipt_scan
from src.services.audit import audit
from src.services.paging import ListPage
from src.services.explain import explain, summarise
from src.services.report_generator import build_pdf

claim_bp = Blueprint("claims", __name__, url_prefix="/claims")
CLAIM_DOC_TYPES = ("receipt", "warranty_card", "damage_photo", "serial_photo", "product_photo",
                   "fault_video", "diagnostic_report", "other_evidence")
UPLOAD_STATUSES = {Config.STATUS_DRAFT, Config.STATUS_ADDITIONAL_INFO, Config.STATUS_MANUAL_REVIEW}
VERIFIED_FIELDS = ("invoice_number", "purchase_date", "serial_number", "model_number", "retailer",
                   "purchase_amount", "product_name")


def _load(claim_id: str, permission: str, **ctx) -> Claim:
    return authorize_object(permission, Claim.query.filter_by(claim_id=claim_id).first_or_404(), **ctx)


def _upload_dir() -> Path:
    return Path(current_app.config["UPLOAD_DIR"])


# ------------------------------------------------------------------ dashboard (SRS xl)
@claim_bp.get("/")
@require("claim.read")
def dashboard():
    """Three rows: what needs the user now, their product plates, and every claim (20 per page)."""
    user = g.user
    if user.role == Config.ROLE_CUSTOMER and dispatch_expiry_alerts(user.id):
        db.session.commit()
    claims_q = scoped_claims(Claim)
    products_q = scoped_products(Product, Claim)
    window = alert_days()
    attention = []
    for c in claims_q.filter(Claim.status.in_(UPLOAD_STATUSES)).order_by(Claim.updated_at.desc()).all():
        if c.status == Config.STATUS_DRAFT:
            attention.append({"icon": "bi-pencil-square", "tone": "", "title": f"Finish your draft for {c.product.product_name}",
                              "text": "Not submitted yet. Nothing is checked until you submit.", "claim": c, "action": "Finish draft"})
        elif c.status == Config.STATUS_ADDITIONAL_INFO:
            attention.append({"icon": "bi-chat-left-dots", "tone": "review", "title": f"A reviewer needs more from you on {c.claim_id}",
                              "text": c.reviewer_notes or "Open the claim to see what is needed.", "claim": c, "action": "Add evidence"})
        elif c.missing_document_flag:
            attention.append({"icon": "bi-cloud-upload", "tone": "review", "title": f"Missing documents on {c.claim_id}",
                              "text": "Adding them lets the claim move on without a follow-up.", "claim": c, "action": "Add evidence"})
    expiring = analytics_service.expiring_list(products_q, window)
    page = claims_q.order_by(Claim.updated_at.desc()).paginate(page=request.args.get("page", 1, type=int),
                                                               per_page=20, error_out=False)
    products = products_q.order_by(Product.created_at.desc()).limit(6).all()
    counts = dict(db.session.query(Claim.product_id, db.func.count(Claim.id))
                  .filter(Claim.product_id.in_([p.id for p in products])).group_by(Claim.product_id).all())
    receipts = (ClaimDocument.query.filter(ClaimDocument.document_type == "receipt",
                                           ClaimDocument.product_id.in_(products_q.with_entities(Product.id)))
                .order_by(ClaimDocument.created_at.desc()).limit(4).all())
    return render_template(
        "claims/dashboard.html", attention=attention, receipts=receipts, expiring=expiring, window=window, page=page,
        products=products, product_count=products_q.count(), claim_counts=counts,
        buckets=analytics_service.warranty_buckets(products_q))


@claim_bp.post("/notifications/<string:notification_id>/read")
@require()
def read_notification(notification_id):
    n = Notification.query.filter_by(notification_id=notification_id, user_id=g.user.id).first_or_404()
    n.is_read = True
    db.session.commit()
    if n.related_claim_id and request.form.get("open"):
        return redirect(url_for("claims.view_claim", claim_id=n.related_claim_id))
    return redirect(request.referrer or url_for("auth.home"))


@claim_bp.post("/notifications/read-all")
@require()
def read_all_notifications():
    Notification.query.filter_by(user_id=g.user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "info")
    return redirect(request.referrer or url_for("auth.home"))


# ------------------------------------------------------------------ search (SRS xlii)
def _search_query(args):
    q = scoped_claims(Claim).join(Product, Claim.product_id == Product.id) \
        .outerjoin(ProductWarranty, Claim.warranty_id == ProductWarranty.id)
    if args.get("claim_id"):
        q = q.filter(Claim.claim_id.ilike(f"%{args['claim_id'].strip()}%"))
    if args.get("product_id"):
        q = q.filter(Product.product_id.ilike(f"%{args['product_id'].strip()}%"))
    if args.get("serial"):
        q = q.filter(Product.serial_number.ilike(f"%{args['serial'].strip()}%"))
    if args.get("category") in CATEGORIES:
        q = q.filter(Product.category == args["category"])
    if args.get("status") in Config.ALL_CLAIM_STATUSES:
        q = q.filter(Claim.status == args["status"])
    if args.get("decision") in ("Likely Valid", "Likely Invalid", "Manual Review Required"):
        q = q.filter(Claim.final_decision == args["decision"])
    if args.get("risk") in ("Low", "Medium", "High"):
        q = q.filter(Claim.risk_level == args["risk"])
    today = date.today()
    ws = args.get("warranty")
    if ws == "Active":
        q = q.filter(ProductWarranty.expiry_date >= today)
    elif ws == "Expired":
        q = q.filter(ProductWarranty.expiry_date < today)
    elif ws == "Expiring soon":
        q = q.filter(ProductWarranty.expiry_date >= today,
                     ProductWarranty.expiry_date <= today + timedelta(days=alert_days()))
    reviewer = args.get("reviewer")
    if reviewer == "unassigned":
        q = q.filter(Claim.assigned_reviewer_id.is_(None))
    elif reviewer and reviewer.startswith("USR-"):
        r = User.query.filter_by(user_id=reviewer).first()
        q = q.filter(Claim.assigned_reviewer_id == (r.id if r else -1))
    start, end = try_parse_date(args.get("start")), try_parse_date(args.get("end"))
    if start:
        q = q.filter(Claim.claim_submission_date >= start)
    if end:
        q = q.filter(Claim.claim_submission_date <= end)
    claims = q.order_by(Claim.created_at.desc()).all()
    lo, hi = args.get("conf_min", ""), args.get("conf_max", "")
    if lo or hi:                       # confidence range on the latest evaluation's Python top-class confidence
        try:
            lo_v = float(lo) / (100 if float(lo) > 1 else 1) if lo else 0.0
            hi_v = float(hi) / (100 if float(hi) > 1 else 1) if hi else 1.0
            claims = [c for c in claims if c.model_evaluation and c.model_evaluation.python_top is not None
                      and lo_v <= c.model_evaluation.python_top <= hi_v]
        except ValueError:
            flash("Confidence range must be numbers between 0 and 1 (or 0-100).", "warning")
    return claims


@claim_bp.get("/search")
@require("claim.read")
def search():
    claims = _search_query(request.args)
    fmt = request.args.get("export")
    if fmt in ("csv", "xlsx"):
        if not check("export.data"):
            abort(403)
        audit("DATA_EXPORTED", "Claim", None, rows=len(claims), format=fmt, filters=request.args.to_dict())
        db.session.commit()
        mimetype = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fmt == "xlsx"
                    else "text/csv; charset=utf-8")
        return Response(export_service.claims_csv(claims, fmt), mimetype=mimetype,
                        headers={"Content-Disposition": f"attachment; filename=assurex_claims.{fmt}"})
    reviewers = User.query.filter_by(role=Config.ROLE_REVIEWER, is_active=True).order_by(User.full_name).all()
    page = ListPage(claims, request.args.get("page", 1, type=int), per_page=20)
    return render_template("claims/search.html", page=page, categories=CATEGORIES, reviewers=reviewers,
                           statuses=Config.ALL_CLAIM_STATUSES, args=request.args,
                           details=verdict.show_model_details(g.user))


# ------------------------------------------------------------------ intake wizard (SRS x-xii, xxxiii)
def _eligible_products():
    return [p for p in scoped_products(Product, Claim).order_by(Product.product_name).all() if p.warranty]


def _apply_verified_entities(doc, form, prefix="verified_"):
    """SRS vii: values the user confirmed/corrected replace the OCR guesses; changes are audited."""
    before = doc.get_ocr_payload()
    after = dict(before)
    for key in VERIFIED_FIELDS:
        val = (form.get(prefix + key) or "").strip()
        if val:
            after[key] = val
    if after != before:
        doc.ocr_data_json = json.dumps(after)
        audit("EXTRACTED_DATA_CORRECTION", "ClaimDocument", doc.document_id,
              changed={k: {"ocr": before.get(k), "user": after.get(k)} for k in after if after.get(k) != before.get(k)})
    doc.verified_by_user = True


def _wizard(products, selected=None, form=None, code=200):
    data = [{"id": p.product_id, "name": p.product_name, "category": p.category, "serial": p.serial_number,
             "status": p.warranty.status, "expiry": p.warranty.expiry_date.isoformat(),
             "purchase": p.purchase_date.isoformat(), "invoice": p.invoice_number or "", "model": p.model_number,
             "retailer": p.retailer,
             "docs": sorted({d.document_type for d in p.documents if d.claim_id is None})} for p in products]
    policies = {c: {k: get_policy(c)[k] for k in ("policy_name", "grace_period_days", "claim_reporting_period_days",
                                                   "excluded_damage_types", "exclusion_min_diagnostic_confidence")}
                for c in CATEGORIES}
    counts = {"required": ["receipt"], "recommended": ["warranty_card", "serial_photo", "damage_photo"]}
    return render_template("claims/wizard.html", products=products, products_data=data, selected=selected, doc_need=counts,
                           faults=FAULTS, damage_types=DAMAGE_TYPES, doc_types=CLAIM_DOC_TYPES,
                           policies=policies, form=form or {}), code


def own_draft(claim_id: str | None, product) -> Claim | None:
    """The wizard's autosaved draft, if it still is an editable draft of this product that the user may edit."""
    if not claim_id:
        return None
    draft = Claim.query.filter_by(claim_id=claim_id).first()
    if draft is None or draft.status != Config.STATUS_DRAFT or draft.product_id != product.id:
        return None
    return authorize_object("claim.update_draft", draft)


def save_draft(product, values: dict, draft_id: str | None = None) -> Claim:
    """Create the Draft claim, or update the wizard's autosaved one (flushed, not committed)."""
    claim = own_draft(draft_id, product)
    if claim is not None:
        for k, v in values.items():
            setattr(claim, k, v)
        return claim
    claim = Claim(user_id=product.user_id, created_by_id=g.user.id, product=product, warranty=product.warranty,
                  service_center_id=product.service_center_id or g.user.service_center_id, **values)
    db.session.add(claim)
    db.session.flush()
    db.session.add(ClaimStatusHistory(claim=claim, previous_status=None, new_status=Config.STATUS_DRAFT,
                                      changed_by_user_id=g.user.id, reason_comment="Claim created"))
    audit("CLAIM_CREATED", "Claim", claim.claim_id, product=product.product_id,
          on_behalf_of=product.owner.user_id if product.user_id != g.user.id else None)
    return claim


@claim_bp.route("/new", methods=["GET", "POST"])
@require("claim.create")
def new_claim():
    products = _eligible_products()
    if request.method == "GET":
        return _wizard(products, selected=request.args.get("product"))
    form = request.form
    product = next((p for p in products if p.product_id == form.get("product_id")), None)
    if product is None:
        flash("Choose one of your registered products that has a warranty.", "warning")
        return redirect(url_for("claims.new_claim"))
    authorize_object("claim.create", product)
    values, errors, warnings = validator.claim_form(form, product, is_staff=g.user.role == Config.ROLE_STAFF)
    if errors:
        for msg in errors:
            flash(msg, "warning")
        return _wizard(products, selected=product.product_id, form=form, code=400)
    claim = save_draft(product, values, form.get("draft_id"))
    upload_warnings = []
    for kind in CLAIM_DOC_TYPES:
        f = request.files.get(kind)
        if not f or not f.filename:
            continue
        try:
            doc, info = doc_service.store(f, kind, claim=claim, uploader=g.user)
        except doc_service.UploadError as exc:
            upload_warnings.append(str(exc))
            audit("UPLOAD_FAILED", "Claim", claim.claim_id, type=kind, reason=str(exc))
            continue
        db.session.flush()
        if kind == "receipt":
            _apply_verified_entities(doc, form)
        audit("DOCUMENT_UPLOADED", "ClaimDocument", doc.document_id, claim=claim.claim_id, type=kind,
              sha256=doc.file_hash_sha256, ocr=info["ocr_status"])
        if info["reused_in"]:
            upload_warnings.append(f"{DOCUMENT_LABELS[kind]}: this exact file was already used elsewhere.")
    for msg in warnings + upload_warnings:
        flash(msg, "warning")
    if form.get("action") == "draft":
        db.session.commit()
        flash(f"Draft {claim.claim_id} saved. Add the remaining documents and submit when ready.", "success")
        return redirect(url_for("claims.view_claim", claim_id=claim.claim_id))
    try:
        outcome = claim_service.submit(claim, g.user)
    except FeatureError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("claims.new_claim", product=product.product_id))
    db.session.commit()
    flash(f"Claim {claim.claim_id} submitted. Recommendation: {outcome.decision['decision']} → {claim.status}.",
          "success")
    return redirect(url_for("claims.view_claim", claim_id=claim.claim_id, fresh=1))


@claim_bp.post("/preparation-check")
@require("claim.create")
def preparation_check():
    """SRS xxxiii: live checklist while the wizard is filled in."""
    product = next((p for p in _eligible_products() if p.product_id == request.form.get("product_id")), None)
    docs = {k for k in CLAIM_DOC_TYPES if request.form.get(f"has_{k}") == "1"}
    if product:
        docs |= {d.document_type for d in product.documents if d.claim_id is None}
    return ok(validator.readiness(product, request.form, docs))


@claim_bp.post("/ocr-extract")
@require("claim.create")
def ocr_extract():
    """SRS vi/vii: read a receipt in the wizard so the user can check the values before submitting."""
    return receipt_scan.scan(request.files.get("receipt"))


# ------------------------------------------------------------------ claim detail & lifecycle
@claim_bp.get("/<string:claim_id>")
@require("claim.read")
def view_claim(claim_id):
    claim = _load(claim_id, "claim.read")
    docs = list(claim.documents) + [d for d in claim.product.documents if d.claim_id is None]
    reviewers = User.query.filter_by(role=Config.ROLE_REVIEWER, is_active=True).order_by(User.full_name).all()
    present = present_document_types(claim)
    return render_template(
        "claims/detail.html", claim=claim, ev=claim.model_evaluation, log=claim.rule_validation, docs=docs,
        summary=summarise(claim), explanation=explain(claim), missing=missing_mandatory(claim),
        missing_supporting=missing_supporting(claim), present=present,
        doc_types=CLAIM_DOC_TYPES, can_upload=claim.status in UPLOAD_STATUSES, reviewers=reviewers,
        policy=get_policy(claim.product.category), faults=FAULTS, damage_types=DAMAGE_TYPES,
        review_actions=[a for a, target in claim_service.REVIEW_ACTIONS.items()
                        if target in rbac.policy()["review_transitions"].get(claim.status, [])],
        override_pairs=[[d, s] for d, s in claim_service.OVERRIDES], action_targets=claim_service.REVIEW_ACTIONS,
        override_min=rbac.policy()["separation_of_duties"]["override_reason_min_chars"],
        v=verdict.view(claim, fresh=request.args.get("fresh") == "1"), details=verdict.show_model_details(g.user))


@claim_bp.get("/<string:claim_id>/track")
@require("claim.read")
def track_claim(claim_id):
    claim = _load(claim_id, "claim.read")
    return render_template("claims/track.html", claim=claim, stages=Config.ALL_CLAIM_STATUSES)


@claim_bp.post("/<string:claim_id>/update")
@require("claim.update_draft")
def update_claim(claim_id):
    claim = _load(claim_id, "claim.update_draft")
    values, errors, warnings = validator.claim_form(request.form, claim.product,
                                                    is_staff=g.user.role == Config.ROLE_STAFF)
    for msg in errors + warnings:
        flash(msg, "warning")
    if not errors:
        for k, v in values.items():
            setattr(claim, k, v)
        audit("CLAIM_UPDATED", "Claim", claim.claim_id, fields=sorted(values))
        db.session.commit()
        flash("Claim details saved.", "success")
    return redirect(url_for("claims.view_claim", claim_id=claim_id))


@claim_bp.post("/<string:claim_id>/submit")
@require("claim.submit")
def submit_claim(claim_id):
    claim = _load(claim_id, "claim.submit")
    if not claim.is_editable:
        flash("This claim has already been submitted.", "info")
        return redirect(url_for("claims.view_claim", claim_id=claim_id))
    try:
        outcome = claim_service.submit(claim, g.user)
    except FeatureError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("claims.view_claim", claim_id=claim_id))
    db.session.commit()
    flash(f"Claim submitted. Recommendation: {outcome.decision['decision']} → {claim.status}.", "success")
    return redirect(url_for("claims.view_claim", claim_id=claim_id, fresh=1))


@claim_bp.post("/<string:claim_id>/documents")
@require("document.upload")
def upload_claim_document(claim_id):
    claim = _load(claim_id, "document.upload")
    if claim.status not in UPLOAD_STATUSES:
        flash("Documents can't be added to a claim at this stage.", "warning")
        return redirect(url_for("claims.view_claim", claim_id=claim_id))
    kind = request.form.get("document_type", "")
    if kind not in CLAIM_DOC_TYPES:
        abort(400)
    try:
        doc, info = doc_service.store(request.files.get("file"), kind, claim=claim, uploader=g.user)
    except doc_service.UploadError as exc:
        audit("UPLOAD_FAILED", "Claim", claim.claim_id, type=kind, reason=str(exc))
        db.session.commit()
        flash(str(exc), "danger")
        return redirect(url_for("claims.view_claim", claim_id=claim_id, _anchor="evidence"))
    db.session.flush()
    audit("DOCUMENT_UPLOADED", "ClaimDocument", doc.document_id, claim=claim.claim_id, type=kind,
          sha256=doc.file_hash_sha256, ocr=info["ocr_status"])
    claim.missing_document_flag = bool(missing_mandatory(claim))
    db.session.commit()
    if info["reused_in"]:
        flash("This exact file was already used elsewhere; it will be flagged as a possible duplicate.", "warning")
    if info["ocr_status"] == "ok" and info["entities"]:
        flash("We read some details from the file. Check them in the evidence list and correct anything wrong.", "info")
    left = missing_mandatory(claim) + missing_supporting(claim)
    flash(f"{doc.original_filename} uploaded." + (f" Still missing: {', '.join(DOCUMENT_LABELS[m] for m in left)}."
                                                  if left else " Every required and recommended document is present."),
          "success")
    return redirect(url_for("claims.view_claim", claim_id=claim_id, _anchor="evidence"))


@claim_bp.get("/<string:claim_id>/card.png")
@require("claim.read")
def summary_card(claim_id):
    claim = _load(claim_id, "claim.read")
    ev = claim.model_evaluation
    wanted = request.args.get("evaluation")
    if wanted:
        ev = ModelEvaluation.query.filter_by(evaluation_id=wanted, claim_id=claim.id).first_or_404()
    if ev is None or not ev.summary_card_image_path:
        abort(404)
    path = (_upload_dir() / ev.summary_card_image_path).resolve()
    if _upload_dir().resolve() not in path.parents or not path.exists():
        abort(404)
    return send_file(path, mimetype="image/png", max_age=3600)


@claim_bp.get("/<string:claim_id>/report.pdf")
@require("report.download")
def download_report(claim_id):
    claim = _load(claim_id, "report.download")
    audit("REPORT_DOWNLOADED", "Claim", claim.claim_id)
    db.session.commit()
    return Response(build_pdf(claim, _upload_dir()), mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=AssureX_{claim.claim_id}.pdf"})


# ------------------------------------------------------------------ documents (SRS xiv, vii)
def _doc(doc_id: str, permission: str) -> ClaimDocument:
    return authorize_object(permission, ClaimDocument.query.filter_by(document_id=doc_id).first_or_404())


def _back(doc):
    if doc.claim:
        return redirect(url_for("claims.view_claim", claim_id=doc.claim.claim_id, _anchor="evidence"))
    return redirect(url_for("products.view_product", product_id=doc.product.product_id, _anchor="documents"))


@claim_bp.get("/documents/<string:doc_id>")
@require("document.read")
def open_document(doc_id):
    doc = _doc(doc_id, "document.read")
    try:
        path = doc_service.absolute_path(doc)
    except doc_service.UploadError:
        abort(404)
    if not path.exists():
        flash("The stored file for this document is missing. Upload it again.", "warning")
        return _back(doc)
    download = request.args.get("download") == "1"
    return send_file(path, mimetype=doc.mime_type or "application/octet-stream", as_attachment=download,
                     download_name=doc.original_filename, max_age=0)


@claim_bp.post("/documents/<string:doc_id>/correct-data")
@require("document.correct_ocr")
def correct_document(doc_id):
    doc = _doc(doc_id, "document.correct_ocr")
    _apply_verified_entities(doc, request.form, prefix="")
    db.session.commit()
    flash("Extracted details saved. They will be used when the claim is evaluated.", "success")
    return _back(doc)


@claim_bp.post("/documents/<string:doc_id>/replace")
@require("document.replace")
def replace_document(doc_id):
    doc = _doc(doc_id, "document.replace")
    try:
        new, info = doc_service.store(request.files.get("file"), doc.document_type, claim=doc.claim,
                                      product=doc.product, uploader=g.user)
    except doc_service.UploadError as exc:
        flash(str(exc), "danger")
        return _back(doc)
    old_id, back = doc.document_id, _back(doc)
    doc_service.remove(doc)
    db.session.flush()
    audit("DOCUMENT_REPLACED", "ClaimDocument", new.document_id, replaced=old_id, sha256=new.file_hash_sha256)
    db.session.commit()
    flash("Document replaced.", "success")
    return back


@claim_bp.post("/documents/<string:doc_id>/delete")
@require("document.delete")
def delete_document(doc_id):
    doc = _doc(doc_id, "document.delete")
    back = _back(doc)
    audit("DOCUMENT_DELETED", "ClaimDocument", doc.document_id, type=doc.document_type, sha256=doc.file_hash_sha256)
    doc_service.remove(doc)
    db.session.commit()
    flash("Document removed.", "info")
    return back
