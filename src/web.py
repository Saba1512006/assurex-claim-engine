"""Jinja filters and globals shared by every template."""
from __future__ import annotations

from datetime import date, datetime, timezone

from flask import request, url_for

from src.core.vocab import DOCUMENT_LABELS

STATUS_TONE = {"Draft": "neutral", "Submitted": "info", "Under Evaluation": "info",
               "Additional Information Required": "warn", "Manual Review": "warn", "Approved": "good",
               "Rejected": "bad", "Closed": "neutral"}
DECISION_TONE = {"Likely Valid": "good", "Likely Invalid": "bad", "Manual Review Required": "warn"}
CLASS_TONE = {"Valid Claim": "good", "Invalid Claim": "bad", "Manual Review": "warn"}
CONSISTENCY_TONE = {"Strong Match": "good", "Acceptable Match": "good", "Weak Match": "warn",
                    "Model Disagreement": "bad", "Uncertain Result": "warn"}
WARRANTY_TONE = {"Active": "good", "Expiring soon": "warn", "Expired": "bad", "Not started": "neutral"}
RISK_TONE = {"Low": "good", "Medium": "warn", "High": "bad"}
NOTIF_ICON = {"warranty_expiry": "bi-hourglass-split", "claim_submission": "bi-send-check",
              "missing_documents": "bi-file-earmark-excel", "additional_info_required": "bi-chat-left-dots",
              "status_change": "bi-arrow-repeat", "review_complete": "bi-clipboard-check",
              "claim_approval": "bi-patch-check", "claim_rejection": "bi-x-octagon", "anomaly_alert": "bi-activity"}
SEVERITY_TONE = {"hard_fail": "bad", "manual_review": "warn", "warning": "info"}


def _date(value, fmt="%d %b %Y"):
    if not value:
        return "—"
    if isinstance(value, str):
        return value
    return value.strftime(fmt)


def _ago(value):
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    secs = int((datetime.now(timezone.utc) - value).total_seconds())
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit} ago"
    return "just now"


def _pct(value, digits=0):
    return "—" if value is None else f"{value * 100:.{digits}f}%"


TAG_KIND = {"good": "valid", "bad": "invalid", "warn": "review", "info": "teal", "neutral": ""}
DECISION_KIND = {"Likely Valid": "valid", "Likely Invalid": "invalid", "Manual Review Required": "review"}
DECISION_ICON = {"valid": "bi-check-lg", "invalid": "bi-x-lg", "review": "bi-eye"}


def _money(value):
    return "—" if value is None else f"USD {value:,.2f}"


def warranty_life(w) -> dict | None:
    """Numbers behind a product plate's life bar: days used of the cover, the grace period, what is left."""
    if w is None:
        return None
    from src.rules.policy_store import get_policy
    today = date.today()
    total = max(1, (w.expiry_date - w.start_date).days)
    used = max(0, (today - w.start_date).days)
    try:
        grace = int(get_policy(w.product.category).get("grace_period_days", 0))
    except Exception:                                   # unknown legacy category: no grace drawn
        grace = 0
    left = (w.expiry_date - today).days
    return {"used": used, "total": total, "grace": grace, "left": max(0, left), "over": max(0, -left),
            "in_grace": 0 < -left <= grace, "status": w.status}


_GTM_VERSION_CACHE: dict = {}


def model_versions() -> dict:
    """Short versions of the two installed models for the footer (GTM hash cached per file mtime)."""
    from src.core.gtm_classifier_v2 import find_model_file, version_of
    from src.core.python_classifier import model_card
    card = model_card() or {}
    gtm_file = find_model_file()
    gtm = "not installed"
    if gtm_file:
        key = (str(gtm_file), gtm_file.stat().st_mtime)
        if key not in _GTM_VERSION_CACHE:
            _GTM_VERSION_CACHE.clear()
            _GTM_VERSION_CACHE[key] = version_of(gtm_file.read_bytes())
        gtm = _GTM_VERSION_CACHE[key]
    return {"python": (card.get("version") or "not installed").split("+")[0], "gtm": gtm}


def register_template_helpers(app) -> None:
    app.jinja_env.filters.update(date=_date, ago=_ago, pct=_pct, money=_money)
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    def tone(kind: str, value) -> str:
        table = {"status": STATUS_TONE, "decision": DECISION_TONE, "class": CLASS_TONE,
                 "consistency": CONSISTENCY_TONE, "warranty": WARRANTY_TONE, "risk": RISK_TONE,
                 "severity": SEVERITY_TONE}[kind]
        return table.get(value, "neutral")

    def tag_kind(kind: str, value) -> str:
        """Colour of a serial-plate tag: verdict colours only for decisions, classes, risk and statuses."""
        return TAG_KIND[tone(kind, value)]

    def url_with(**changes):
        """Current URL with some query arguments replaced (filters, pagination)."""
        args = request.args.to_dict()
        args.update({k: v for k, v in changes.items() if v is not None})
        for k in [k for k, v in changes.items() if v is None]:
            args.pop(k, None)
        return url_for(request.endpoint, **(request.view_args or {}), **args)

    def unread_notifications():
        from flask import g
        from src.models.entities import Notification
        user = g.get("user")
        if user is None:
            return []
        return (Notification.query.filter_by(user_id=user.id, is_read=False)
                .order_by(Notification.id.desc()).limit(20).all())

    def asset(filename: str) -> str:
        """Static URL with the file's modification time, so browsers fetch new CSS/JS after a deploy."""
        from pathlib import Path
        path = Path(app.static_folder) / filename
        version = int(path.stat().st_mtime) if path.exists() else 0
        return url_for("static", filename=filename, v=version)

    # globals (not a context processor) so imported macros can use them too
    app.jinja_env.globals.update(
        email_pattern=r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,24}",   # HTML twin of EMAIL_RE
        tone=tone, tag_kind=tag_kind, url_with=url_with, unread_notifications=unread_notifications, asset=asset,
        decision_kind=lambda d: DECISION_KIND.get(d, "none"), decision_icon=lambda k: DECISION_ICON.get(k, "bi-dash"),
        model_versions=model_versions, warranty_life=warranty_life, medium_url=app.config.get("MEDIUM_URL"), github_url=app.config.get("GITHUB_URL"),
        doc_label=lambda t: DOCUMENT_LABELS.get(t, t.replace("_", " ").title()),
        notif_icon=lambda kind: NOTIF_ICON.get(kind, "bi-bell"))

    @app.context_processor
    def _today():
        return {"today": date.today()}
