"""In-app notifications (SRS xxxix). Created in the same transaction as the event they describe."""
from __future__ import annotations

from database.db import db
from src.models.entities import Notification

TYPES = {"warranty_expiry", "claim_submission", "missing_documents", "additional_info_required",
         "status_change", "review_complete", "claim_approval", "claim_rejection", "anomaly_alert"}


def notify(user_id: int, kind: str, title: str, message: str, *, claim=None, product=None) -> Notification:
    if kind not in TYPES:
        raise ValueError(f"unknown notification type {kind!r}")
    row = Notification(user_id=user_id, notification_type=kind, title=title[:160], message=message,
                       related_claim_id=getattr(claim, "claim_id", None),
                       related_product_id=getattr(product, "product_id", None) or
                       getattr(getattr(claim, "product", None), "product_id", None))
    db.session.add(row)
    return row
