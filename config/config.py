"""Application configuration. Secrets come from the environment (or a local .env file)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # pragma: no cover
    pass

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")          # required outside tests (see src/app_security.py)
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true")
    TESTING = False

    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "data" / "uploads"))
    MODEL_DIR = BASE_DIR / "model"
    POLICY_DIR = BASE_DIR / "policies"
    REPORT_DIR = BASE_DIR / "reports"

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database' / 'assurex.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    MAX_CONTENT_LENGTH = 40 * 1024 * 1024               # whole request (wizard can carry several files)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    WTF_CSRF_TIME_LIMIT = None                           # token lives as long as the session
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # ----- domain constants (SRS)
    CLAIM_CLASS_VALID, CLAIM_CLASS_INVALID, CLAIM_CLASS_MANUAL_REVIEW = "Valid Claim", "Invalid Claim", "Manual Review"
    ALL_CLAIM_CLASSES = [CLAIM_CLASS_VALID, CLAIM_CLASS_INVALID, CLAIM_CLASS_MANUAL_REVIEW]

    STATUS_DRAFT = "Draft"
    STATUS_SUBMITTED = "Submitted"
    STATUS_UNDER_EVALUATION = "Under Evaluation"
    STATUS_ADDITIONAL_INFO = "Additional Information Required"
    STATUS_MANUAL_REVIEW = "Manual Review"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_CLOSED = "Closed"
    ALL_CLAIM_STATUSES = [STATUS_DRAFT, STATUS_SUBMITTED, STATUS_UNDER_EVALUATION, STATUS_ADDITIONAL_INFO,
                          STATUS_MANUAL_REVIEW, STATUS_APPROVED, STATUS_REJECTED, STATUS_CLOSED]

    ROLE_CUSTOMER = "customer"
    ROLE_STAFF = "service_center_staff"
    ROLE_REVIEWER = "claim_reviewer"
    ROLE_ADMIN = "administrator"
    ALL_ROLES = [ROLE_CUSTOMER, ROLE_STAFF, ROLE_REVIEWER, ROLE_ADMIN]

    # Default expiry-alert window; administrators change it at runtime (SystemSetting).
    WARRANTY_EXPIRY_ALERT_DAYS = int(os.environ.get("WARRANTY_EXPIRY_ALERT_DAYS", "30"))


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
