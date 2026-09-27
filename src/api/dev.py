"""Development-only pages. Registered only when DEBUG is on or ASSUREX_STYLEGUIDE=1; never in production."""
from __future__ import annotations

from flask import Blueprint, render_template

from src.services import model_card_service

dev_bp = Blueprint("dev", __name__)


@dev_bp.get("/_styleguide")
def styleguide():
    """Every base component in every state, on both surfaces (the bench and the workspace)."""
    return render_template("dev/styleguide.html", mc=model_card_service.build())
