"""Administration (SRS ix, xxiv, xxvi, xli, xliii, xlv, xlvii, xlviii, l)."""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import (Blueprint, Response, abort, flash, jsonify, redirect, render_template, request,
                   send_file, url_for)
from sqlalchemy import or_

from config.config import Config
from database.db import db
from src.core import decision_table, gtm_classifier_v2 as gtm_mod, python_classifier
from src.core.card_v2 import CARD_POLICY_FIELDS
from src.core.gtm_classifier_v2 import GTM_DIR, GTMUnavailable, find_model_file, parse_labels
from src.core.offline_eval import evaluate_gtm_and_save
from src.core.vocab import CATEGORIES, CLASSES, DAMAGE_TYPES, try_parse_date
from src.models.entities import AuditLog, Claim, Product, ReviewerAction, User
from src.rules import policy_store
from src.security.guards import check, require, scoped_claims, scoped_products
from src.services import analytics_service, export_service
from src.services.alert_service import (alert_days, anomalies, dispatch_anomaly_alerts, dispatch_expiry_alerts,
                                        expiring_warranties, set_alert_days)
from src.services.audit import audit

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_STATS = ROOT / "data" / "dataset_statistics.json"


def _filters():
    a = request.args
    return {"category": a.get("category") if a.get("category") in CATEGORIES else None,
            "start": try_parse_date(a.get("start")), "end": try_parse_date(a.get("end")),
            "status": a.get("status") if a.get("status") in Config.ALL_CLAIM_STATUSES else None}


def model_status() -> dict:
    card = python_classifier.model_card()
    try:
        py = python_classifier.get_python_classifier()
        py_state = {"ok": True, "version": py.version}
    except python_classifier.ModelUnavailable as exc:
        py_state = {"ok": False, "error": str(exc)}
    try:
        gtm = gtm_mod.get_gtm_classifier()
        gtm_state = {"ok": True, "version": gtm.version, "file": gtm.model_file, "quantized": gtm.quantized,
                     "input": f"{gtm.w}×{gtm.h}"}
    except GTMUnavailable as exc:
        gtm_state = {"ok": False, "error": str(exc)}
    return {"python": py_state, "gtm": gtm_state, "card": card, "gtm_eval": gtm_mod.evaluation()}


# ------------------------------------------------------------------ dashboards
@admin_bp.get("/dashboard")
@require("admin.dashboard")
def dashboard():
    f = _filters()
    q = analytics_service.apply_filters(scoped_claims(Claim), **f)
    return render_template("admin/dashboard.html", o=analytics_service.overview(q), x=analytics_service.dashboard_extras(q),
                           filters=request.args,
                           categories=CATEGORIES, statuses=Config.ALL_CLAIM_STATUSES, anomalies=anomalies(),
                           models=model_status(), expiring=expiring_warranties()[:6], window=alert_days(),
                           users=User.query.count(),
                           recent=AuditLog.query.order_by(AuditLog.id.desc()).limit(8).all())


@admin_bp.get("/analytics")
@require("analytics.read")
def analytics():
    f = _filters()
    claims_q = analytics_service.apply_filters(scoped_claims(Claim), **f)
    data = analytics_service.full(claims_q, scoped_products(Product, Claim))
    if request.args.get("format") == "json":
        return jsonify(data)
    stats = json.loads(DATASET_STATS.read_text()) if DATASET_STATS.exists() else {}
    per_model = [["Python model", [data["models"]["python_classes"].get(c, 0) for c in CLASSES]],
                 ["Teachable Machine", [data["models"]["gtm_classes"].get(c, 0) for c in CLASSES]]]
    return render_template("admin/analytics.html", a=data, per_model=per_model, o=analytics_service.overview(claims_q), filters=request.args,
                           categories=CATEGORIES, statuses=Config.ALL_CLAIM_STATUSES, card=python_classifier.model_card(),
                           dataset=stats)


# ------------------------------------------------------------------ policies & decision settings
@admin_bp.route("/policies", methods=["GET", "POST"])
@require("policy.manage")
def policies():
    if request.method == "POST":
        category = request.form.get("category")
        if category not in CATEGORIES:
            abort(400)
        before = policy_store.get_policy(category)
        updates = {k: request.form.get(k) for k in policy_store.EDITABLE}
        updates["excluded_damage_types"] = request.form.getlist("excluded_damage_types")
        updates["rule_severity"] = {rid: request.form.get(f"rule_{rid}", "off") for rid in policy_store.RULE_CATALOG}
        try:
            after = policy_store.save_policy(category, updates)
        except policy_store.PolicyError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin.policies", category=category))
        same = lambda a, b: sorted(a) == sorted(b) if isinstance(a, list) and isinstance(b, list) else a == b  # noqa: E731
        changed = {k: {"from": before.get(k), "to": after.get(k)} for k in after if not same(before.get(k), after.get(k))}
        audit("POLICY_UPDATED", "Policy", category, changes=changed)
        db.session.commit()
        flash(f"{category} policy saved ({len(changed)} change{'s' if len(changed) != 1 else ''}). "
              "New claims use it immediately; past evaluations are unchanged.", "success")
        if set(changed) & set(CARD_POLICY_FIELDS):
            flash("This change alters what the Claim Summary Card shows, so the Teachable Machine model no longer "
                  "matches its training cards. Rebuild the cards, retrain the model and reinstall it before relying "
                  "on its predictions.", "warning")
        return redirect(url_for("admin.policies", category=category))
    selected = request.args.get("category") if request.args.get("category") in CATEGORIES else CATEGORIES[0]
    history = (AuditLog.query.filter(AuditLog.action == "POLICY_UPDATED", AuditLog.entity_id == selected)
               .order_by(AuditLog.id.desc()).limit(15).all())
    decision_history = (AuditLog.query.filter(AuditLog.action == "DECISION_POLICY_UPDATED")
                        .order_by(AuditLog.id.desc()).limit(10).all())
    from src.services.verdict import DETAILS_KEY
    from src.models.entities import SystemSetting
    return render_template("admin/policies.html", policies=policy_store.all_policies(), selected=selected,
                           catalog=policy_store.RULE_CATALOG, damage_types=DAMAGE_TYPES, categories=CATEGORIES,
                           decision=decision_table.load_policy(), window=alert_days(), history=history,
                           decision_history=decision_history, card_fields=CARD_POLICY_FIELDS,
                           show_details=SystemSetting.get_val(DETAILS_KEY, "1") == "1")


@admin_bp.post("/settings/decision")
@require("settings.manage")
def decision_settings():
    policy = decision_table.load_policy()
    before = json.dumps({"consistency": policy["consistency"], "routing": policy["routing"]})
    try:
        for key in ("min_confidence", "strong_max_diff", "acceptable_max_diff"):
            policy["consistency"][key] = round(float(request.form[key]), 3)
        for decision in policy["routing"]:
            policy["routing"][decision] = request.form.get(f"route_{decision}", policy["routing"][decision])
        policy["version"] = datetime.now(timezone.utc).strftime("%Y.%m.%d.%H%M")
        decision_table.save_policy(policy)
    except (KeyError, ValueError) as exc:
        flash(f"Settings not saved: {exc}", "danger")
        return redirect(url_for("admin.policies", _anchor="decision"))
    audit("DECISION_POLICY_UPDATED", "Settings", "decision_policy", before=json.loads(before),
          after={"consistency": policy["consistency"], "routing": policy["routing"]}, version=policy["version"])
    db.session.commit()
    flash(f"Decision settings saved as version {policy['version']}.", "success")
    return redirect(url_for("admin.policies", _anchor="decision"))


@admin_bp.post("/settings/alerts")
@require("settings.manage")
def alert_settings():
    try:
        days = set_alert_days(int(request.form.get("days", "")))
    except ValueError:
        flash("Enter the number of days as a whole number.", "warning")
        return redirect(url_for("admin.policies", _anchor="alerts"))
    audit("ALERT_WINDOW_UPDATED", "Settings", "warranty_expiry_alert_days", days=days)
    db.session.commit()
    flash(f"Owners are now alerted {days} days before a warranty ends.", "success")
    return redirect(url_for("admin.policies", _anchor="alerts"))


@admin_bp.post("/settings/customer-view")
@require("settings.manage")
def customer_view_settings():
    """SRS xix: whether customers see model probabilities and rule IDs on their claim (reviewers always do)."""
    from src.models.entities import SystemSetting
    from src.services.verdict import DETAILS_KEY
    show = request.form.get("show_model_details") == "1"
    SystemSetting.set_val(DETAILS_KEY, "1" if show else "0",
                          description="Customers see model probabilities and rule IDs on their claims")
    audit("SETTING_UPDATED", "Settings", DETAILS_KEY, value=show)
    db.session.commit()
    flash("Customers now see model probabilities and rule IDs." if show else
          "Customers now see the decision and its reasons without model probabilities.", "success")
    return redirect(url_for("admin.policies", _anchor="customer-view"))


@admin_bp.post("/alerts/dispatch")
@require("alert.dispatch")
def dispatch_alerts():
    expiry, anomaly = dispatch_expiry_alerts(), dispatch_anomaly_alerts()
    audit("ALERTS_DISPATCHED", "Notification", None, expiry=expiry, anomaly=anomaly)
    db.session.commit()
    flash(f"Sent {expiry} warranty-expiry alert(s) and {anomaly} monitoring alert(s).", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


# ------------------------------------------------------------------ what-if simulator
@admin_bp.get("/what-if")
@require("settings.manage")
def what_if():
    from src.services import whatif
    return render_template("admin/what_if.html", sim=whatif.simulate(decision_table.load_policy()["consistency"]),
                           version=decision_table.load_policy()["version"])


@admin_bp.post("/what-if/apply")
@require("settings.manage")
def what_if_apply():
    from src.services import whatif
    try:
        proposed = whatif.validate(request.form)
    except whatif.WhatIfError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("admin.what_if"))
    policy = decision_table.load_policy()
    before = dict(policy["consistency"])
    if before == {**before, **proposed}:
        flash("These are already the thresholds in use; nothing changed.", "info")
        return redirect(url_for("admin.what_if"))
    sim = whatif.simulate(proposed, include_live=False)
    policy["consistency"].update(proposed)
    policy["version"] = datetime.now(timezone.utc).strftime("%Y.%m.%d.%H%M")
    decision_table.save_policy(policy)
    audit("DECISION_POLICY_UPDATED", "Settings", "decision_policy", source="what-if", before=before,
          after=policy["consistency"], version=policy["version"],
          simulated={"automation_rate": sim["test"]["proposed"]["automation_rate"],
                     "auto_accuracy": sim["test"]["proposed"]["auto_accuracy"]})
    db.session.commit()
    flash(f"Thresholds applied as decision policy {policy['version']}. New claims use them; past decisions are unchanged.",
          "success")
    return redirect(url_for("admin.what_if"))


# ------------------------------------------------------------------ batch evaluation
@admin_bp.get("/batch")
@require("settings.manage")
def batch():
    from src.models.entities import BatchRun
    from src.services import batch as batch_service
    runs = BatchRun.query.order_by(BatchRun.id.desc()).limit(10).all()
    return render_template("admin/batch.html", runs=[(r, batch_service.summary(r)) for r in runs],
                           required=batch_service.REQUIRED, max_rows=batch_service.MAX_ROWS, chunk=batch_service.CHUNK)


@admin_bp.get("/batch/example.csv")
@require("settings.manage")
def batch_example():
    """The 225-claim test split: a ready-made file to try the batch evaluator with (labels included)."""
    return send_file(ROOT / "data" / "splits" / "test.csv", mimetype="text/csv", as_attachment=True,
                     download_name="assurex_test_split.csv")


@admin_bp.get("/batch/<string:batch_id>.csv")
@require("settings.manage")
def batch_csv(batch_id):
    from src.models.entities import BatchRun
    from src.services import batch as batch_service
    b = BatchRun.query.filter_by(batch_id=batch_id).first_or_404()
    audit("DATA_EXPORTED", "BatchRun", b.batch_id, rows=b.processed, format="csv")
    db.session.commit()
    return Response(batch_service.to_csv(b), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=assurex_{b.batch_id}.csv"})


# ------------------------------------------------------------------ models (SRS xviii-xxi, xlviii)
@admin_bp.get("/models")
@require("settings.manage")
def models():
    stats = json.loads(DATASET_STATS.read_text()) if DATASET_STATS.exists() else {}
    versions = sorted((p.name for p in (GTM_DIR / "versions").glob("*") if p.is_dir()), reverse=True) \
        if (GTM_DIR / "versions").exists() else []
    train = ROOT / "data" / "summary_cards" / "train"
    samples = {f: next((x.name for x in sorted((train / f).glob("*_v1.jpg"))), None) if (train / f).exists() else None
               for f in ("valid", "invalid", "manual_review")}
    return render_template("admin/models.html", m=model_status(), dataset=stats, classes=CLASSES,
                           gtm_versions=versions, sample_cards=samples)


@admin_bp.post("/models/gtm")
@require("settings.manage")
def upload_gtm():
    """Install a Teachable Machine TensorFlow Lite export. The previous one is archived, never overwritten."""
    model, labels = request.files.get("model"), request.files.get("labels")
    if not model or not labels or not model.filename.lower().endswith(".tflite"):
        flash("Upload the .tflite file and labels.txt from the Teachable Machine export.", "warning")
        return redirect(url_for("admin.models"))
    blob, label_text = model.read(), labels.read().decode("utf-8", "replace")
    if len(blob) < 1024 or blob[4:8] != b"TFL3":
        flash("That file is not a TensorFlow Lite model.", "danger")
        return redirect(url_for("admin.models"))
    if sorted(parse_labels(label_text)) != sorted(CLASSES):
        flash(f"labels.txt must contain exactly these classes: {', '.join(CLASSES)}.", "danger")
        return redirect(url_for("admin.models"))
    staging = Path(tempfile.mkdtemp())
    try:
        (staging / "model_unquant.tflite").write_bytes(blob)
        (staging / "labels.txt").write_text(label_text, encoding="utf-8")
        try:
            candidate = gtm_mod.TeachableMachineClassifier(staging)
        except GTMUnavailable as exc:
            flash(f"The model could not be loaded: {exc}", "danger")
            return redirect(url_for("admin.models"))
        gtm_mod.reset()                                         # release the running model before touching files
        try:
            current = find_model_file(GTM_DIR)
            if current is not None:                             # archive the model being replaced
                archive = GTM_DIR / "versions" / gtm_mod.version_of(current.read_bytes())
                archive.mkdir(parents=True, exist_ok=True)
                for name in (current.name, "labels.txt", "evaluation.json"):
                    if (GTM_DIR / name).exists():
                        shutil.copy2(GTM_DIR / name, archive / name)
                        (GTM_DIR / name).unlink()
            GTM_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staging / "model_unquant.tflite", GTM_DIR / "model_unquant.tflite")
            shutil.copy2(staging / "labels.txt", GTM_DIR / "labels.txt")
        except OSError as exc:
            flash(f"The model files could not be written ({exc.strerror or exc}). Stop the app, then try again.",
                  "danger")
            return redirect(url_for("admin.models"))
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    gtm_mod.reset()
    audit("GTM_MODEL_INSTALLED", "Model", candidate.version, size=len(blob), quantized=candidate.quantized)
    db.session.commit()
    flash(f"Teachable Machine model {candidate.version} installed. Run the evaluation to record its accuracy.", "success")
    return redirect(url_for("admin.models"))


@admin_bp.post("/models/gtm/evaluate")
@require("settings.manage")
def evaluate_gtm():
    try:
        result = evaluate_gtm_and_save()
    except GTMUnavailable as exc:
        flash(str(exc), "warning")
        return redirect(url_for("admin.models"))
    audit("GTM_MODEL_EVALUATED", "Model", result["test"]["model_version"],
          test_accuracy=result["test"]["gtm_accuracy"], agreement=result["test"]["agreement_rate"])
    db.session.commit()
    flash(f"Teachable Machine test accuracy {result['test']['gtm_accuracy']:.1%}; agreement with the Python model "
          f"{result['test']['agreement_rate']:.1%}.", "success")
    return redirect(url_for("admin.models"))


@admin_bp.get("/models/training-cards.zip")
@require("settings.manage")
def training_cards():
    """The class folders to drag into Teachable Machine (train split only - val/test never leave the server)."""
    src = ROOT / "data" / "summary_cards" / "train"
    if not src.exists():
        abort(404)
    # An anonymous temporary file: the operating system deletes it as soon as it is closed, and the server closes
    # it after sending. (A named file removed in a cleanup hook fails on Windows, where open files can't be deleted.)
    tmp = tempfile.TemporaryFile(suffix=".zip")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as zf:
        for folder, label in (("valid", "Valid Claim"), ("invalid", "Invalid Claim"), ("manual_review", "Manual Review")):
            for img in sorted((src / folder).glob("*.jpg")):
                zf.write(img, f"{label}/{img.name}")
    tmp.seek(0)
    audit("TRAINING_CARDS_DOWNLOADED", "Model", "summary_cards/train")
    db.session.commit()
    return send_file(tmp, mimetype="application/zip", as_attachment=True,
                     download_name="assurex_teachable_machine_training_cards.zip")


@admin_bp.get("/models/cards/<string:split>/<string:name>")
@require("settings.manage")
def sample_card(split, name):
    if split not in ("train", "val", "test") or not name.endswith(".jpg") or "/" in name or ".." in name:
        abort(404)
    base = ROOT / "data" / "summary_cards" / split
    hits = [base / name] if split != "train" else [base / d / name for d in ("valid", "invalid", "manual_review")]
    path = next((p for p in hits if p.exists()), None)
    if path is None:
        abort(404)
    return send_file(path, mimetype="image/jpeg", max_age=3600)


# ------------------------------------------------------------------ audit & export (SRS xlv, xlvii)
@admin_bp.get("/audit")
@require("audit.read")
def audit_log():
    q = AuditLog.query
    if request.args.get("action"):
        q = q.filter(AuditLog.action == request.args["action"])
    if request.args.get("q"):
        like = f"%{request.args['q'].strip()}%"
        q = q.filter(or_(AuditLog.entity_id.ilike(like), AuditLog.details_json.ilike(like)))
    if request.args.get("role") in Config.ALL_ROLES:
        q = q.filter(AuditLog.user_role == request.args["role"])
    if request.args.get("actor"):
        actor = User.query.filter(or_(User.user_id == request.args["actor"].strip(),
                                      User.email == request.args["actor"].strip().lower())).first()
        q = q.filter(AuditLog.user_id == (actor.id if actor else -1))
    start, end = try_parse_date(request.args.get("start")), try_parse_date(request.args.get("end"))
    if start:
        q = q.filter(AuditLog.timestamp >= datetime.combine(start, datetime.min.time()))
    if end:
        q = q.filter(AuditLog.timestamp < datetime.combine(end, datetime.min.time()) + timedelta(days=1))
    page = max(1, request.args.get("page", 1, type=int))
    rows = q.order_by(AuditLog.id.desc()).paginate(page=page, per_page=40, error_out=False)
    actions = [a for (a,) in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action)]
    return render_template("admin/audit.html", rows=rows, actions=actions, args=request.args, roles=Config.ALL_ROLES)


@admin_bp.get("/export/<string:kind>")
@require("export.data")
def export(kind):
    f = _filters()
    fmt = "xlsx" if request.args.get("format") == "xlsx" else "csv"
    claims_q = analytics_service.apply_filters(scoped_claims(Claim), **f)
    products = scoped_products(Product, Claim).order_by(Product.id).all()
    if kind == "claims":
        body = export_service.claims_csv(claims_q.order_by(Claim.id).all(), fmt)
    elif kind == "products":
        body = export_service.products_csv(products, fmt)
    elif kind == "warranties":
        body = export_service.warranties_csv(products, fmt)
    elif kind == "analytics":
        body = export_service.analytics_csv(analytics_service.full(claims_q, scoped_products(Product, Claim)), fmt)
    elif kind == "overrides":
        ids = [c.id for c in claims_q.all()]
        actions = (ReviewerAction.query.filter(ReviewerAction.claim_id.in_(ids)).order_by(ReviewerAction.id).all()
                   if ids else [])
        body = export_service.overrides_csv(actions, fmt)
    elif kind == "audit" and check("audit.read"):
        body = export_service.audit_csv(AuditLog.query.order_by(AuditLog.id).all(), fmt)
    else:
        abort(404)
    audit("DATA_EXPORTED", "Export", kind, format=fmt, filters={k: str(v) for k, v in f.items() if v})
    db.session.commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    mimetype = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fmt == "xlsx"
                else "text/csv; charset=utf-8")
    return Response(body, mimetype=mimetype,
                    headers={"Content-Disposition": f"attachment; filename=assurex_{kind}_{stamp}.{fmt}"})
