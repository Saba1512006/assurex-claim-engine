"""AssureX Claim Engine - application factory."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask, render_template  # noqa: E402

from config.config import Config  # noqa: E402
from database.db import db, init_db  # noqa: E402
from src.app_security import harden  # noqa: E402
from src.web import register_template_helpers  # noqa: E402


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
    app.config.from_object(config_class)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    harden(app)
    init_db(app)

    from src.models.entities import AuditLog, User
    from src.security.guards import init_rbac
    init_rbac(app, db, User, AuditLog)

    from src.api.access import access_bp
    from src.api.admin import admin_bp
    from src.api.auth import auth_bp
    from src.api.claims import claim_bp
    from src.api.products import product_bp
    from src.api.public import public_bp
    from src.api.reviewer import reviewer_bp
    for bp in (public_bp, auth_bp, product_bp, claim_bp, reviewer_bp, admin_bp, access_bp):
        app.register_blueprint(bp)

    register_template_helpers(app)

    @app.errorhandler(404)
    def _not_found(_e):
        return render_template("components/error.html", code=404, title="We couldn't find that page",
                               message="The link may be old, or the record may not be visible to your account."), 404

    @app.errorhandler(413)
    def _too_large(_e):
        return render_template("components/error.html", code=413, title="Upload too large",
                               message="Files can be at most 10 MB each (16 MB for a fault video)."), 413

    @app.errorhandler(429)
    def _rate_limited(_e):
        return render_template("components/error.html", code=429, title="Slow down a little",
                               message="Too many attempts in a short time. Wait a minute and try again."), 429

    @app.errorhandler(500)
    def _server_error(_e):
        db.session.rollback()
        return render_template("components/error.html", code=500, title="Something went wrong on our side",
                               message="Your data is safe. Please try again; if it keeps happening, contact support."), 500

    return app


if __name__ == "__main__":                                        # python src/app.py  (production: wsgi.py)
    application = create_app()
    application.config["SESSION_COOKIE_SECURE"] = False          # local development server is plain http
    application.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)
