"""AssureX Claim Engine - application factory."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask, render_template, request  # noqa: E402

from config.config import Config  # noqa: E402
from database.db import db, init_db  # noqa: E402
from src.app_security import harden  # noqa: E402
from src.web import register_template_helpers  # noqa: E402


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
    app.config.from_object(config_class)
    app.json.sort_keys = False                      # probability dicts keep the fixed class order (Valid, Invalid, Manual Review)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    harden(app)
    init_db(app)

    from src.models.entities import AuditLog, User
    from src.security.guards import init_rbac
    init_rbac(app, db, User, AuditLog)

    from src.api.access import access_bp
    from src.api.api import api_bp
    from src.api.admin import admin_bp
    from src.api.auth import auth_bp
    from src.api.claims import claim_bp
    from src.api.products import product_bp
    from src.api.public import public_bp
    from src.api.reviewer import reviewer_bp
    for bp in (public_bp, auth_bp, product_bp, claim_bp, reviewer_bp, admin_bp, access_bp, api_bp):
        app.register_blueprint(bp)
    if app.config.get("DEBUG") or os.environ.get("ASSUREX_STYLEGUIDE") == "1":   # style guide: development only
        from src.api.dev import dev_bp
        app.register_blueprint(dev_bp)

    register_template_helpers(app)

    from src.api.errors import ErrorCode, fail, reference

    def _page(code, title, message, **extra):
        if request.path.startswith("/api/"):
            api_code = {404: ErrorCode.NOT_FOUND, 413: ErrorCode.TOO_LARGE, 429: ErrorCode.RATE_LIMITED}.get(code, ErrorCode.SERVER_ERROR)
            return fail(api_code)
        return render_template("components/error.html", code=code, title=title, message=message, **extra), code

    @app.errorhandler(404)
    def _not_found(_e):
        return _page(404, "We couldn't find that page",
                     "The link may be out of date, or the record isn't visible to your account.")

    @app.errorhandler(413)
    def _too_large(_e):
        return _page(413, "That upload is too large", "Each file can be at most 16 MB. Compress the file or upload a "
                     "smaller photo, then try again.")

    @app.errorhandler(429)
    def _rate_limited(e):
        import time
        from src.app_security import limiter
        hit = limiter.current_limit
        wait = max(1, int(hit.reset_at - time.time())) if hit else 60
        back = request.referrer if (request.referrer or "").startswith(request.host_url) else None
        return _page(429, "Too many attempts", f"You reached the limit of {getattr(e, 'description', 'requests')}. "
                     "The countdown shows when you can try again.", retry_in=wait,
                     retry_url=back or (request.path if request.method == "GET" else None))

    @app.errorhandler(500)
    def _server_error(_e):
        db.session.rollback()
        ref = reference()
        app.logger.exception("Unhandled error %s on %s", ref, request.path)
        if request.path.startswith("/api/"):
            return fail(ErrorCode.SERVER_ERROR)
        return render_template("components/error.html", code=500, title="Something went wrong on our side",
                               message="Your data is safe. Try again in a moment.", ref=ref), 500

    return app


if __name__ == "__main__":                                        # python src/app.py  (production: wsgi.py)
    application = create_app()
    application.config["SESSION_COOKIE_SECURE"] = False          # local development server is plain http
    application.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)
