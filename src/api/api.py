"""JSON endpoints for live UI parts. Every response uses the envelope in src/api/errors.py."""
from __future__ import annotations

from flask import Blueprint

from src.api.errors import ok
from src.models.entities import Claim
from src.security.guards import authorize_object, require
from src.services import verdict

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/claims/<string:claim_id>/evaluation")
@require("claim.read")
def claim_evaluation(claim_id):
    """Stored verdict payload (never re-runs a model), or the pending stages while evaluation runs."""
    claim = authorize_object("claim.read", Claim.query.filter_by(claim_id=claim_id).first_or_404())
    return ok(verdict.api_payload(claim))
