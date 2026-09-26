"""One helper for every audit row (SRS xlvii). Rows are append-only."""
from __future__ import annotations

import json

from flask import g, has_request_context, request

from database.db import db
from src.models.entities import AuditLog


def audit(action: str, entity_type: str | None = None, entity_id: str | None = None, *, user=None, **details) -> AuditLog:
    actor = user if user is not None else (g.get("user") if has_request_context() else None)
    row = AuditLog(user_id=getattr(actor, "id", None), user_role=getattr(actor, "role", None), action=action,
                   entity_type=entity_type, entity_id=(str(entity_id)[:50] if entity_id else None),
                   ip_address=request.remote_addr if has_request_context() else None,
                   details_json=json.dumps(details, default=str) if details else None)
    db.session.add(row)
    return row
