"""Public pages: landing page, model card, technical blog, public test-card images, health check."""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from flask import Blueprint, abort, current_app, g, jsonify, redirect, render_template, send_file, url_for

from src.core.gtm_classifier_v2 import evaluation as gtm_evaluation, find_model_file
from src.core.python_classifier import model_card as python_model_card
from src.services import model_card_service

public_bp = Blueprint("public", __name__)
ROOT = Path(__file__).resolve().parent.parent.parent
BLOG = ROOT / "documentation" / "TECHNICAL_BLOG.md"
TEST_CARDS = ROOT / "data" / "summary_cards" / "test"

DEMO_ACCOUNTS = [
    ("Customer", "customer@assurex.local", "CustomerPass123!", "Register products, file claims, track progress"),
    ("Service-center staff", "staff@assurex.local", "StaffPass123!", "File claims for walk-in customers, log repairs"),
    ("Claim reviewer", "reviewer@assurex.local", "ReviewerPass123!", "Work the manual-review queue and decide claims"),
    ("Administrator", "admin@assurex.local", "AdminPass123!", "Dashboards, policies, models, access control"),
]


def measured_metrics() -> dict:
    """Numbers shown on the landing page come from the saved evaluation files, never literals."""
    card = python_model_card()
    test = card.get("test", {})
    gtm = gtm_evaluation().get("test", {})
    return {"python_accuracy": test.get("accuracy"), "python_f1": test.get("f1_macro"),
            "python_auc": test.get("roc_auc_ovr_macro"), "python_model": test.get("selected_model"),
            "gtm_accuracy": gtm.get("gtm_accuracy"), "gtm_installed": find_model_file() is not None}


@public_bp.get("/")
def index():
    if g.get("user"):
        return redirect(url_for("auth.home"))
    return render_template("public/index.html", metrics=measured_metrics(),
                           demo_accounts=DEMO_ACCOUNTS if current_app.config.get("SHOW_DEMO_ACCOUNTS", True) else [])


@public_bp.get("/blog")
def blog():
    text = BLOG.read_text(encoding="utf-8") if BLOG.exists() else "# Blog not found"
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"],
                           extension_configs={"toc": {"toc_depth": "2"}})
    html = md.convert(text)
    words = len(re.findall(r"\w+", text))
    return render_template("public/blog.html", html=html, toc=md.toc_tokens, words=words, medium_url=current_app.config["MEDIUM_URL"],
                           minutes=max(1, round(words / 220)))


@public_bp.get("/model-card")
def model_card():
    return render_template("public/model_card.html", mc=model_card_service.build())


@public_bp.get("/cards/test/<string:name>")
def test_card(name):
    """Canonical test-split cards (synthetic data, never used for training) for the model card and sign-in page."""
    path = TEST_CARDS / name
    if not name.endswith("_v0.jpg") or "/" in name or ".." in name or not path.is_file():
        abort(404)
    return send_file(path, mimetype="image/jpeg", max_age=86400)


@public_bp.get("/healthz")
def health():
    """Liveness + model availability for uptime monitoring (SRS NFR availability)."""
    return jsonify(status="ok", python_model=bool(python_model_card()), gtm_model=find_model_file() is not None)
