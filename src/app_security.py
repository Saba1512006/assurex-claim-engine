"""HTTP hardening: secret key, CSRF, rate limiting, cookies and security headers."""
from __future__ import annotations

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError, CSRFProtect

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["600/hour"])

# No inline or third-party scripts: all JavaScript is served from /static, so script-src is just 'self'.
CSP = ("default-src 'self'; img-src 'self' data: blob:; object-src 'none'; base-uri 'self'; "
       "form-action 'self'; frame-ancestors 'none'; "
       "script-src 'self'; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' data: https://fonts.gstatic.com")


def harden(app) -> None:
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set. Run `python database/seed.py` once (it writes a .env with a "
                           "random key) or export SECRET_KEY before starting the app.")
    app.config.setdefault("SESSION_COOKIE_SECURE", not (app.debug or app.testing))
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_NAME="assurex_session")
    csrf.init_app(app)
    limiter.init_app(app)

    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        resp.headers.setdefault("Content-Security-Policy", CSP)
        if request.is_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if resp.mimetype == "text/html":
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(CSRFError)
    def _csrf_error(_e):
        from flask import render_template
        return render_template("components/error.html", code=400, title="This form expired",
                               message="For your security the form could not be accepted. Reload the page and try again."), 400
