"""Products, warranties and repair history (SRS iii, iv, viii, xiii, xiv)."""
from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy import or_

from config.config import Config
from database.db import db
from src.core.vocab import CATEGORIES, coverage_days, try_parse_date
from src.models.entities import (Claim, Product, ProductWarranty, RepairHistory, ServiceCenter, User,
                                 WarrantyPolicy)
from src.ocr import document_processor as ocr
from src.rules import validator
from src.rules.policy_store import get_policy
from src.security.guards import authorize_object, check, require, scoped_products
from src.services import documents as doc_service
from src.services.alert_service import alert_days
from src.services.audit import audit

product_bp = Blueprint("products", __name__, url_prefix="/products")
PRODUCT_DOC_TYPES = ("receipt", "warranty_card", "serial_photo", "product_photo")


def _load(product_id: str, permission: str) -> Product:
    return authorize_object(permission, Product.query.filter_by(product_id=product_id).first_or_404())


def _policy_row(category: str) -> WarrantyPolicy:
    """Snapshot of the category policy at registration time (the live rules stay in policies/*.json)."""
    row = WarrantyPolicy.query.filter_by(category=category).first()
    if row is None:
        p = get_policy(category)
        row = WarrantyPolicy(category=category, policy_name=p["policy_name"],
                             coverage_duration_months=p["coverage_duration_months"],
                             grace_period_days=p["grace_period_days"],
                             claim_reporting_period_days=p["claim_reporting_period_days"],
                             authorized_service_center_required=p["authorized_service_center_required"])
        db.session.add(row)
    return row


@product_bp.get("/")
@require("product.read")
def list_products():
    q = scoped_products(Product, Claim)
    term = request.args.get("q", "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Product.product_name.ilike(like), Product.serial_number.ilike(like),
                         Product.product_id.ilike(like), Product.brand.ilike(like)))
    if request.args.get("category") in CATEGORIES:
        q = q.filter(Product.category == request.args["category"])
    products = q.order_by(Product.created_at.desc()).all()
    status = request.args.get("warranty")
    if status:
        products = [p for p in products if (p.warranty.status if p.warranty else "No warranty") == status]
    return render_template("products/list.html", products=products, categories=CATEGORIES)


def _owner_for_new_product(form):
    """Customers register their own products; staff register a walk-in customer's product."""
    if g.user.role == Config.ROLE_CUSTOMER:
        return g.user, None
    email = (form.get("customer_email") or "").strip().lower()
    owner = User.query.filter_by(email=email, role=Config.ROLE_CUSTOMER, is_active=True).first()
    return owner, None if owner else "No active customer account uses that email. Ask the customer to sign up first."


@product_bp.route("/new", methods=["GET", "POST"])
@require("product.create")
def register_product():
    centers = ServiceCenter.query.order_by(ServiceCenter.name).all()
    policies = {c: get_policy(c) for c in CATEGORIES}
    if request.method == "POST":
        values, errors, warnings = validator.product_form(request.form)
        owner, owner_err = _owner_for_new_product(request.form)
        if owner_err:
            errors.append(owner_err)
        if g.user.role == Config.ROLE_STAFF:
            center_id = g.user.service_center_id
        else:
            raw = request.form.get("service_center_id", "")
            center_id = int(raw) if raw.isdigit() and db.session.get(ServiceCenter, int(raw)) else None
        if errors:
            for msg in errors:
                flash(msg, "warning")
            return render_template("products/register.html", form=request.form, centers=centers, policies=policies), 400
        product = Product(user_id=owner.id, service_center_id=center_id, product_name=values["product_name"],
                          category=values["category"], brand=values["brand"], model_number=values["model_number"],
                          serial_number=values["serial_number"], purchase_date=values["purchase_date"],
                          purchase_price=values["purchase_price"], retailer=values["retailer"],
                          invoice_number=values["invoice_number"])
        db.session.add(product)
        db.session.flush()
        policy = get_policy(values["category"])
        base = min(policy["standard_terms_months"])
        center = db.session.get(ServiceCenter, center_id) if center_id else None
        db.session.add(ProductWarranty(
            product=product, policy=_policy_row(values["category"]),
            warranty_provider=values["warranty_provider"] or f"{values['brand']} manufacturer warranty",
            start_date=values["purchase_date"],
            expiry_date=values["purchase_date"] + timedelta(days=coverage_days(values["warranty_months"])),
            duration_months=values["warranty_months"], is_extended=values["is_extended"],
            extended_months=max(0, values["warranty_months"] - base) if values["is_extended"] else 0,
            coverage_conditions=f"Covered faults: {', '.join(policy['covered_faults'])}.",
            exclusions="; ".join(policy["exclusions"]), service_center_name=center.name if center else None))
        receipt = request.files.get("receipt")
        if receipt and receipt.filename:
            try:
                _, info = doc_service.store(receipt, "receipt", product=product, uploader=g.user)
                if info["reused_in"]:
                    warnings.append("This receipt file was already used for another product; claims will be reviewed.")
            except doc_service.UploadError as exc:
                db.session.rollback()
                audit("UPLOAD_FAILED", "Product", None, reason=str(exc))
                db.session.commit()
                flash(str(exc), "danger")
                return render_template("products/register.html", form=request.form, centers=centers, policies=policies), 400
        if Product.query.filter(Product.serial_number == product.serial_number, Product.id != product.id).first():
            warnings.append("Another product already uses this serial number. Any claim will get a duplicate check.")
            audit("DUPLICATE_SERIAL_REGISTERED", "Product", product.product_id, serial=product.serial_number)
        audit("PRODUCT_REGISTERED", "Product", product.product_id, owner=owner.user_id, category=product.category,
              warranty_months=values["warranty_months"], extended=values["is_extended"])
        db.session.commit()
        for msg in warnings:
            flash(msg, "warning")
        flash(f"{product.product_name} registered as {product.product_id}. Warranty runs to "
              f"{product.warranty.expiry_date:%d %b %Y}.", "success")
        return redirect(url_for("products.view_product", product_id=product.product_id))
    return render_template("products/register.html", form={}, centers=centers, policies=policies)


@product_bp.post("/scan-receipt")
@require("product.create")
def scan_receipt():
    """Read a receipt for the registration form without storing it (SRS vi, vii)."""
    file = request.files.get("receipt")
    try:
        data, mime, ext = doc_service.validate(file, "receipt")
    except doc_service.UploadError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"receipt.{ext}"
        path.write_bytes(data)
        result = ocr.process(path, mime, "receipt")
    if result["status"] == "unavailable":
        return jsonify(ok=False, status="unavailable",
                       error="Automatic reading isn't available for this file type on this server. "
                             "Type the details from your receipt.")
    if result["status"] != "ok" or not ocr.looks_like_receipt(result["entities"]):
        return jsonify(ok=False, status="unreadable", error="We couldn't find invoice details in this file. "
                                                            "Check that it is the receipt and that it is legible.")
    return jsonify(ok=True, entities=result["entities"])


@product_bp.get("/<string:product_id>")
@require("product.read")
def view_product(product_id):
    product = _load(product_id, "product.read")
    claims = [c for c in product.claims if check("claim.read", c)]
    docs = [d for d in product.documents if d.claim_id is None]
    return render_template("products/detail.html", product=product, claims=claims, docs=docs,
                           policy=get_policy(product.category), doc_types=PRODUCT_DOC_TYPES,
                           alert_window=alert_days(), today=date.today())


@product_bp.post("/<string:product_id>/update")
@require("product.update")
def update_product(product_id):
    product = _load(product_id, "product.update")
    if any(c.status != Config.STATUS_DRAFT for c in product.claims):
        flash("Product details are locked once a claim has been submitted for it.", "warning")
        return redirect(url_for("products.view_product", product_id=product_id))
    form = {**product.to_dict(), "category": product.category, **{k: v for k, v in request.form.items() if v}}
    form["purchase_date"] = request.form.get("purchase_date") or product.purchase_date.isoformat()
    form["warranty_months"] = request.form.get("warranty_months") or product.warranty.duration_months
    form["warranty_type"] = request.form.get("warranty_type") or ("extended" if product.warranty.is_extended else "standard")
    values, errors, _ = validator.product_form(form)
    if errors:
        for msg in errors:
            flash(msg, "warning")
        return redirect(url_for("products.view_product", product_id=product_id))
    for field in ("product_name", "brand", "model_number", "retailer", "invoice_number", "purchase_price", "purchase_date"):
        setattr(product, field, values[field])
    w = product.warranty
    w.start_date = values["purchase_date"]
    w.duration_months, w.is_extended = values["warranty_months"], values["is_extended"]
    w.expiry_date = w.start_date + timedelta(days=coverage_days(values["warranty_months"]))
    if values["warranty_provider"]:
        w.warranty_provider = values["warranty_provider"]
    audit("PRODUCT_UPDATED", "Product", product.product_id, fields=sorted(request.form.keys()))
    db.session.commit()
    flash("Product and warranty updated.", "success")
    return redirect(url_for("products.view_product", product_id=product_id))


@product_bp.post("/<string:product_id>/documents")
@require("document.upload")
def upload_product_document(product_id):
    product = _load(product_id, "product.read")
    authorize_object("document.upload", product)
    kind = request.form.get("document_type", "")
    if kind not in PRODUCT_DOC_TYPES:
        abort(400)
    try:
        doc, info = doc_service.store(request.files.get("file"), kind, product=product, uploader=g.user)
    except doc_service.UploadError as exc:
        audit("UPLOAD_FAILED", "Product", product.product_id, reason=str(exc))
        db.session.commit()
        flash(str(exc), "danger")
        return redirect(url_for("products.view_product", product_id=product_id, _anchor="documents"))
    db.session.flush()
    audit("DOCUMENT_UPLOADED", "ClaimDocument", doc.document_id, product=product.product_id, type=kind,
          sha256=doc.file_hash_sha256, ocr=info["ocr_status"])
    db.session.commit()
    if info["reused_in"]:
        flash("This exact file was already uploaded elsewhere; it will be flagged as a possible duplicate.", "warning")
    flash(f"{doc.original_filename} uploaded.", "success")
    return redirect(url_for("products.view_product", product_id=product_id, _anchor="documents"))


@product_bp.post("/<string:product_id>/repairs")
@require("repair.record")
def add_repair(product_id):
    product = _load(product_id, "repair.record")
    f = request.form
    repair_date = try_parse_date(f.get("repair_date"))
    errors = []
    if repair_date is None or repair_date > date.today():
        errors.append("Enter a repair date that is not in the future.")
    if not f.get("repair_center", "").strip():
        errors.append("Enter the repair center.")
    try:
        cost = round(float(f.get("repair_cost") or 0), 2)
        if cost < 0:
            raise ValueError
    except ValueError:
        errors.append("Repair cost must be a positive number.")
        cost = 0
    if errors:
        for msg in errors:
            flash(msg, "warning")
        return redirect(url_for("products.view_product", product_id=product_id, _anchor="repairs"))
    rec = RepairHistory(product=product, recorded_by_id=g.user.id, repair_date=repair_date,
                        repair_center=f["repair_center"].strip()[:120],
                        replaced_parts=f.get("replaced_parts", "").strip()[:255] or None,
                        outcome=f.get("outcome") if f.get("outcome") in ("Repaired", "Replaced", "Not repairable", "Pending") else "Repaired",
                        repair_cost=cost, is_authorized_center=f.get("is_authorized_center") == "1",
                        serial_number_seen=f.get("serial_number_seen", "").strip().upper() or None,
                        notes=f.get("notes", "").strip() or None)
    db.session.add(rec)
    db.session.flush()
    audit("REPAIR_RECORDED", "Product", product.product_id, repair=rec.repair_id, authorised=rec.is_authorized_center)
    db.session.commit()
    flash("Repair recorded.", "success")
    return redirect(url_for("products.view_product", product_id=product_id, _anchor="repairs"))
