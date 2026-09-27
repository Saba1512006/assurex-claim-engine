"""Public pages: landing page, technical blog, health check."""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from flask import Blueprint, current_app, g, jsonify, redirect, render_template, url_for

from src.core.gtm_classifier_v2 import evaluation as gtm_evaluation, find_model_file
from src.core.python_classifier import model_card

public_bp = Blueprint("public", __name__)
MEDIUM_URL = "https://medium.com/@sabarajput672/building-assurex-two-models-one-rulebook-and-why-our-first-100-was-a-bug-bb8b9858b11c"
BLOG = Path(__file__).resolve().parent.parent.parent / "documentation" / "TECHNICAL_BLOG.md"

DEMO_ACCOUNTS = [
    ("Customer", "customer@assurex.local", "CustomerPass123!", "Register products, file claims, track progress"),
    ("Service-center staff", "staff@assurex.local", "StaffPass123!", "File claims for walk-in customers, log repairs"),
    ("Claim reviewer", "reviewer@assurex.local", "ReviewerPass123!", "Work the manual-review queue and decide claims"),
    ("Administrator", "admin@assurex.local", "AdminPass123!", "Dashboards, policies, models, access control"),
]


def measured_metrics() -> dict:
    """Numbers shown on the landing page come from the saved evaluation files, never literals."""
    card = model_card()
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
    return render_template("public/blog.html", html=html, toc=md.toc_tokens, words=words, medium_url=MEDIUM_URL,
                           minutes=max(1, round(words / 220)))


@public_bp.get("/healthz")
def health():
    """Liveness + model availability for uptime monitoring (SRS NFR availability)."""
    return jsonify(status="ok", python_model=bool(model_card()), gtm_model=find_model_file() is not None)
