"""Warranty-expiry alerts (SRS ix) and monitoring / anomaly alerts (SRS l)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func

from config.config import Config
from database.db import db
from src.core.consistency import thresholds
from src.models.entities import (AuditLog, Claim, ClaimDocument, ModelEvaluation, Notification, Product,
                                 ProductWarranty, SystemSetting, User)

ALERT_KEY = "warranty_expiry_alert_days"


def alert_days() -> int:
    return SystemSetting.get_int(ALERT_KEY, Config.WARRANTY_EXPIRY_ALERT_DAYS)


def set_alert_days(days: int) -> int:
    days = max(1, min(int(days), 365))
    SystemSetting.set_val(ALERT_KEY, days, "Days before warranty expiry when owners are alerted")
    return days


def expiring_warranties(product_query=None, days: int | None = None) -> list:
    """Active warranties that end within the alert window (optionally limited to a product query)."""
    days = alert_days() if days is None else days
    today = date.today()
    q = ProductWarranty.query.join(Product).filter(ProductWarranty.expiry_date >= today,
                                                   ProductWarranty.expiry_date <= today + timedelta(days=days),
                                                   ProductWarranty.start_date <= today)
    if product_query is not None:
        q = q.filter(Product.id.in_(product_query.with_entities(Product.id)))
    return q.order_by(ProductWarranty.expiry_date).all()


def dispatch_expiry_alerts(user_id: int | None = None) -> int:
    """Create one unread expiry notification per expiring product (idempotent). Caller commits."""
    q = Product.query.filter(Product.user_id == user_id) if user_id else None
    created = 0
    for w in expiring_warranties(q):
        p = w.product
        exists = Notification.query.filter_by(user_id=p.user_id, notification_type="warranty_expiry",
                                              related_product_id=p.product_id, is_read=False).first()
        if exists:
            continue
        left = w.remaining_days()
        db.session.add(Notification(
            user_id=p.user_id, notification_type="warranty_expiry", related_product_id=p.product_id,
            title=f"Warranty for {p.product_name} ends in {left} day{'s' if left != 1 else ''}",
            message=f"Coverage for serial {p.serial_number} ends on {w.expiry_date:%d %b %Y}. "
                    "File any claim for an existing fault before then."))
        created += 1
    return created


def anomalies(hours: int = 72) -> list:
    """Monitoring signals for administrators over a rolling window."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []

    def events(*actions):
        return AuditLog.query.filter(AuditLog.action.in_(actions), AuditLog.timestamp >= since)

    n = events("UPLOAD_FAILED").count()
    if n:
        out.append(("Failed uploads", "warning", n, f"{n} upload(s) were refused (wrong type, size or unreadable receipt).",
                    "Check whether a user needs help or someone is probing the upload endpoint."))
    fails = events("LOGIN_FAILED", "LOGIN_LOCKED").all()
    if fails:
        per_ip = {}
        for f in fails:
            per_ip[f.ip_address] = per_ip.get(f.ip_address, 0) + 1
        worst = max(per_ip.values())
        out.append(("Repeated sign-in failures", "critical" if worst >= 5 else "warning", len(fails),
                    f"{len(fails)} failed sign-in(s) from {len(per_ip)} address(es); busiest address {worst}.",
                    "Accounts lock for a minute after 5 failures. Force a sign-out if an account looks compromised."))
    reused = db.session.query(ClaimDocument.file_hash_sha256).group_by(ClaimDocument.file_hash_sha256) \
        .having(func.count(func.distinct(ClaimDocument.product_id)) > 1).count()
    if reused:
        out.append(("Duplicate documents", "warning", reused, f"{reused} file(s) appear on more than one product.",
                    "Open the claims flagged as duplicates and compare the receipts."))
    bursts = db.session.query(Claim.user_id, func.count(Claim.id)).filter(Claim.created_at >= since) \
        .group_by(Claim.user_id).having(func.count(Claim.id) >= 3).all()
    if bursts:
        out.append(("Unusual claim activity", "warning", len(bursts),
                    f"{len(bursts)} account(s) filed 3 or more claims in {hours} hours.",
                    "Review those claimants' recent claims together."))
    n = events("MODEL_UNAVAILABLE").count()
    if n:
        out.append(("Model unavailable", "critical", n, f"{n} evaluation(s) ran without one of the models.",
                    "Open Admin › Models to see which model is missing and install it."))
    recent = ModelEvaluation.query.filter(ModelEvaluation.evaluation_timestamp >= since).all()
    min_conf = thresholds()["min_confidence"]
    low = [e for e in recent if (e.python_top is not None and e.python_top < min_conf)
           or (e.gtm_top is not None and e.gtm_top < min_conf)]
    if low:
        out.append(("Low-confidence predictions", "warning", len(low),
                    f"{len(low)} prediction(s) had a top-class confidence below {min_conf:.2f}.",
                    "These claims are in the manual-review queue; recurring cases may need more training data."))
    compared = [e for e in recent if e.is_class_match is not None]
    disagree = [e for e in compared if not e.is_class_match]
    if disagree:
        rate = len(disagree) / len(compared)
        out.append(("Model disagreement", "critical" if rate > 0.3 else "warning", len(disagree),
                    f"The two models disagreed on {len(disagree)} of {len(compared)} claims ({rate:.0%}).",
                    "A rate above 30% suggests the Teachable Machine model needs retraining."))
    return [dict(zip(("title", "severity", "count", "description", "recommendation"), a)) for a in out]


def dispatch_anomaly_alerts() -> int:
    """Notify every active administrator once per unread anomaly title. Caller commits."""
    items = anomalies()
    admins = User.query.filter_by(role=Config.ROLE_ADMIN, is_active=True).all()
    created = 0
    for admin in admins:
        for a in items:
            title = f"Monitoring: {a['title']}"
            if Notification.query.filter_by(user_id=admin.id, notification_type="anomaly_alert",
                                            title=title, is_read=False).first():
                continue
            db.session.add(Notification(user_id=admin.id, notification_type="anomaly_alert", title=title,
                                        message=f"{a['description']} {a['recommendation']}"))
            created += 1
    return created
