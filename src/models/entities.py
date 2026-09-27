"""Relational schema (SRS xlvi). SQLite by default, any SQLAlchemy URL via DATABASE_URL."""
import json
import uuid
from datetime import date, datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from config.config import Config
from database.db import db


def utcnow():
    return datetime.now(timezone.utc)


def generate_uuid(prefix=""):
    """Short, non-sequential public identifier (IDs cannot be enumerated or leak order)."""
    raw = uuid.uuid4().hex[:10].upper()
    return f"{prefix}-{raw}" if prefix else raw


def _loads(text, default):
    try:
        return json.loads(text) if text else default
    except (TypeError, ValueError):
        return default


class ServiceCenter(db.Model):
    """Authorised service center. Staff and products belong to one (drives record scope)."""
    __tablename__ = "service_centers"

    id = db.Column(db.Integer, primary_key=True)
    center_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("SC"))
    name = db.Column(db.String(120), unique=True, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("USR"))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=Config.ROLE_CUSTOMER)
    phone_number = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    # security (see src/security/guards.py)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    failed_logins = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    service_center_id = db.Column(db.Integer, db.ForeignKey("service_centers.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    service_center = db.relationship("ServiceCenter")
    products = db.relationship("Product", backref="owner", lazy=True, foreign_keys="Product.user_id")
    claims = db.relationship("Claim", backref="claimant", lazy=True, foreign_keys="Claim.user_id")
    notifications = db.relationship("Notification", backref="recipient", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_locked(self) -> bool:
        if not self.locked_until:
            return False
        until = self.locked_until if self.locked_until.tzinfo else self.locked_until.replace(tzinfo=timezone.utc)
        return until > utcnow()

    @property
    def first_name(self) -> str:
        return (self.full_name or "").split(" ")[0]

    def to_dict(self):
        return {"user_id": self.user_id, "email": self.email, "full_name": self.full_name, "role": self.role,
                "phone_number": self.phone_number, "address": self.address,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("PRD"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_center_id = db.Column(db.Integer, db.ForeignKey("service_centers.id"), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)
    brand = db.Column(db.String(60), nullable=False)
    model_number = db.Column(db.String(60), nullable=False)
    serial_number = db.Column(db.String(80), nullable=False, index=True)
    purchase_date = db.Column(db.Date, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    retailer = db.Column(db.String(100), nullable=False)
    invoice_number = db.Column(db.String(80), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    service_center = db.relationship("ServiceCenter")
    warranty = db.relationship("ProductWarranty", backref="product", uselist=False, cascade="all, delete-orphan")
    claims = db.relationship("Claim", backref="product", lazy=True)
    repair_records = db.relationship("RepairHistory", backref="product", lazy=True, cascade="all, delete-orphan",
                                     order_by="RepairHistory.repair_date")
    documents = db.relationship("ClaimDocument", backref="product", lazy=True, cascade="all, delete-orphan")

    @property
    def has_unauthorized_repairs(self) -> bool:
        return any(not r.is_authorized_center for r in self.repair_records)

    def to_dict(self):
        return {"product_id": self.product_id, "product_name": self.product_name, "category": self.category,
                "brand": self.brand, "model_number": self.model_number, "serial_number": self.serial_number,
                "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
                "purchase_price": self.purchase_price, "retailer": self.retailer,
                "invoice_number": self.invoice_number}


class WarrantyPolicy(db.Model):
    """Snapshot of the category policy a warranty was issued under (the live rules are in policies/*.json)."""
    __tablename__ = "warranty_policies"

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("POL"))
    category = db.Column(db.String(60), unique=True, nullable=False)
    policy_name = db.Column(db.String(100), nullable=False)
    coverage_duration_months = db.Column(db.Integer, nullable=False, default=12)
    grace_period_days = db.Column(db.Integer, nullable=False, default=7)
    claim_reporting_period_days = db.Column(db.Integer, nullable=False, default=30)
    authorized_service_center_required = db.Column(db.Boolean, default=True)
    policy_rules_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, default=utcnow)

    warranties = db.relationship("ProductWarranty", backref="policy", lazy=True)


class ProductWarranty(db.Model):
    """Standard or extended warranty attached to a product (SRS iv, viii)."""
    __tablename__ = "product_warranties"

    id = db.Column(db.Integer, primary_key=True)
    warranty_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("WAR"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey("warranty_policies.id"), nullable=True)
    warranty_provider = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    duration_months = db.Column(db.Integer, nullable=False, default=12)
    is_extended = db.Column(db.Boolean, default=False)
    extended_months = db.Column(db.Integer, default=0)
    coverage_conditions = db.Column(db.Text, nullable=True)
    exclusions = db.Column(db.Text, nullable=True)
    service_center_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    claims = db.relationship("Claim", backref="warranty", lazy=True)

    def is_active(self, on_date=None) -> bool:
        target = on_date or date.today()
        return self.start_date <= target <= self.expiry_date

    def remaining_days(self, on_date=None) -> int:
        return max(0, (self.expiry_date - (on_date or date.today())).days)

    def is_approaching_expiry(self, threshold_days=None, on_date=None) -> bool:
        if threshold_days is None:
            threshold_days = SystemSetting.get_int("warranty_expiry_alert_days", Config.WARRANTY_EXPIRY_ALERT_DAYS)
        rem = (self.expiry_date - (on_date or date.today())).days
        return 0 <= rem <= threshold_days and self.is_active(on_date)

    @property
    def status(self) -> str:
        """Active | Expiring soon | Expired | Not started."""
        today = date.today()
        if today < self.start_date:
            return "Not started"
        if today > self.expiry_date:
            return "Expired"
        return "Expiring soon" if self.is_approaching_expiry() else "Active"

    @property
    def life_used(self) -> float:
        total = max(1, (self.expiry_date - self.start_date).days)
        return min(1.0, max(0.0, (date.today() - self.start_date).days / total))

    def to_dict(self):
        return {"warranty_id": self.warranty_id, "provider": self.warranty_provider,
                "start_date": self.start_date.isoformat(), "expiry_date": self.expiry_date.isoformat(),
                "duration_months": self.duration_months, "is_extended": self.is_extended,
                "remaining_days": self.remaining_days(), "status": self.status}


class Claim(db.Model):
    __tablename__ = "claims"

    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.String(32), unique=True, nullable=False, index=True, default=lambda: generate_uuid("CLM"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    warranty_id = db.Column(db.Integer, db.ForeignKey("product_warranties.id"), nullable=True)
    service_center_id = db.Column(db.Integer, db.ForeignKey("service_centers.id"), nullable=True, index=True)

    fault_occurrence_date = db.Column(db.Date, nullable=False)
    fault_description = db.Column(db.Text, nullable=False)
    fault_category = db.Column(db.String(60), nullable=False)
    damage_type = db.Column(db.String(60), nullable=False)
    diagnostic_confidence = db.Column(db.Float, nullable=False, default=0.5)
    diagnosis_source = db.Column(db.String(40), nullable=False, default="Not assessed")
    previous_replacement_details = db.Column(db.String(255), nullable=True)
    claim_submission_date = db.Column(db.Date, nullable=True)

    status = db.Column(db.String(40), nullable=False, default=Config.STATUS_DRAFT, index=True)
    risk_level = db.Column(db.String(20), nullable=True)
    final_decision = db.Column(db.String(30), nullable=True)
    decision_reason = db.Column(db.Text, nullable=True)
    decision_rule_id = db.Column(db.String(10), nullable=True)
    decision_policy_version = db.Column(db.String(20), nullable=True)

    is_duplicate_flag = db.Column(db.Boolean, default=False)
    contradiction_flag = db.Column(db.Boolean, default=False)
    missing_document_flag = db.Column(db.Boolean, default=False)

    assigned_reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    reviewer_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    assigned_reviewer = db.relationship("User", foreign_keys=[assigned_reviewer_id])
    service_center = db.relationship("ServiceCenter")
    documents = db.relationship("ClaimDocument", backref="claim", lazy=True, cascade="all, delete-orphan")
    status_history = db.relationship("ClaimStatusHistory", backref="claim", lazy=True, cascade="all, delete-orphan",
                                     order_by="ClaimStatusHistory.id")
    evaluations = db.relationship("ModelEvaluation", backref="claim", lazy=True, cascade="all, delete-orphan",
                                  order_by="ModelEvaluation.id")
    rule_logs = db.relationship("RuleValidationLog", backref="claim", lazy=True, cascade="all, delete-orphan",
                                order_by="RuleValidationLog.id")
    reviewer_actions = db.relationship("ReviewerAction", backref="claim", lazy=True, cascade="all, delete-orphan",
                                       order_by="ReviewerAction.id")

    @property
    def model_evaluation(self):
        """Latest evaluation. Earlier ones are kept untouched (SRS xlviii)."""
        return self.evaluations[-1] if self.evaluations else None

    @property
    def rule_validation(self):
        return self.rule_logs[-1] if self.rule_logs else None

    @property
    def is_editable(self) -> bool:
        return self.status in (Config.STATUS_DRAFT, Config.STATUS_ADDITIONAL_INFO)

    def transition_status(self, new_status, actor_id=None, notes=None):
        """Every status change leaves a history row and an audit row (SRS xxxviii, xlvii)."""
        prev = self.status
        self.status = new_status
        db.session.add(ClaimStatusHistory(claim=self, previous_status=prev, new_status=new_status,
                                          changed_by_user_id=actor_id,
                                          reason_comment=notes or f"{prev} → {new_status}"))
        db.session.add(AuditLog(user_id=actor_id, action="STATUS_CHANGE", entity_type="Claim", entity_id=self.claim_id,
                                details_json=json.dumps({"from": prev, "to": new_status, "note": notes})))

    def to_dict(self):
        ev = self.model_evaluation
        return {"claim_id": self.claim_id, "status": self.status,
                "submission_date": self.claim_submission_date.isoformat() if self.claim_submission_date else None,
                "fault_category": self.fault_category, "damage_type": self.damage_type,
                "final_decision": self.final_decision, "risk_level": self.risk_level,
                "python_class": ev.python_predicted_class if ev else None,
                "gtm_class": ev.gtm_predicted_class if ev else None,
                "consistency": ev.model_consistency_status if ev else None}


class ClaimDocument(db.Model):
    __tablename__ = "claim_documents"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("DOC"))
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    document_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)     # relative to UPLOAD_DIR
    original_filename = db.Column(db.String(150), nullable=False)
    mime_type = db.Column(db.String(40), nullable=True)
    file_size_bytes = db.Column(db.Integer, nullable=False, default=0)
    file_hash_sha256 = db.Column(db.String(64), nullable=False, index=True)

    ocr_status = db.Column(db.String(20), nullable=False, default="not_applicable")  # ok|unreadable|unavailable|not_applicable
    ocr_extracted_text = db.Column(db.Text, nullable=True)
    ocr_data_json = db.Column(db.Text, nullable=True)
    verified_by_user = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    uploaded_by = db.relationship("User")

    def get_ocr_payload(self) -> dict:
        return _loads(self.ocr_data_json, {})

    @property
    def is_image(self) -> bool:
        return (self.mime_type or "").startswith("image/")


class RepairHistory(db.Model):
    __tablename__ = "repair_histories"

    id = db.Column(db.Integer, primary_key=True)
    repair_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("REP"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    repair_date = db.Column(db.Date, nullable=False)
    repair_center = db.Column(db.String(120), nullable=False)
    replaced_parts = db.Column(db.String(255), nullable=True)
    outcome = db.Column(db.String(80), nullable=False)
    repair_cost = db.Column(db.Float, nullable=False, default=0.0)
    is_authorized_center = db.Column(db.Boolean, default=True)
    serial_number_seen = db.Column(db.String(80), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {"repair_id": self.repair_id, "repair_date": self.repair_date.isoformat(),
                "repair_center": self.repair_center, "replaced_parts": self.replaced_parts,
                "outcome": self.outcome, "repair_cost": self.repair_cost,
                "is_authorized_center": self.is_authorized_center}


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("NOT"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    related_claim_id = db.Column(db.String(32), nullable=True)
    related_product_id = db.Column(db.String(32), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class ClaimStatusHistory(db.Model):
    __tablename__ = "claim_status_histories"

    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False)
    previous_status = db.Column(db.String(40), nullable=True)
    new_status = db.Column(db.String(40), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reason_comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    changed_by = db.relationship("User", foreign_keys=[changed_by_user_id])


class ModelEvaluation(db.Model):
    """One immutable row per evaluation: both predictions, versions, card, comparison, decision trace."""
    __tablename__ = "model_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("EVL"))
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False)

    features_json = db.Column(db.Text, nullable=False, default="{}")        # exact model inputs

    python_available = db.Column(db.Boolean, nullable=False, default=True)
    python_model_version = db.Column(db.String(64), nullable=True)
    python_predicted_class = db.Column(db.String(30), nullable=True)
    python_conf_valid = db.Column(db.Float, nullable=True)
    python_conf_invalid = db.Column(db.Float, nullable=True)
    python_conf_manual = db.Column(db.Float, nullable=True)

    gtm_available = db.Column(db.Boolean, nullable=False, default=False)
    gtm_model_version = db.Column(db.String(64), nullable=True)
    gtm_predicted_class = db.Column(db.String(30), nullable=True)
    gtm_conf_valid = db.Column(db.Float, nullable=True)
    gtm_conf_invalid = db.Column(db.Float, nullable=True)
    gtm_conf_manual = db.Column(db.Float, nullable=True)
    model_errors_json = db.Column(db.Text, nullable=True)

    is_class_match = db.Column(db.Boolean, nullable=True)
    top_confidence_difference = db.Column(db.Float, nullable=True)
    model_consistency_status = db.Column(db.String(40), nullable=False)
    consistency_thresholds_json = db.Column(db.Text, nullable=True)

    decision = db.Column(db.String(30), nullable=True)
    decision_rule_id = db.Column(db.String(10), nullable=True)
    decision_trace_json = db.Column(db.Text, nullable=True)
    decision_policy_version = db.Column(db.String(20), nullable=True)

    summary_card_image_path = db.Column(db.String(255), nullable=True)
    summary_card_sha256 = db.Column(db.String(64), nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    payload_json = db.Column(db.Text, nullable=True)      # full verdict payload incl. stage timings + explanations
    evaluation_timestamp = db.Column(db.DateTime, default=utcnow)

    def python_scores(self) -> dict:
        if not self.python_available:
            return {}
        return {"Valid Claim": self.python_conf_valid, "Invalid Claim": self.python_conf_invalid,
                "Manual Review": self.python_conf_manual}

    def gtm_scores(self) -> dict:
        if not self.gtm_available:
            return {}
        return {"Valid Claim": self.gtm_conf_valid, "Invalid Claim": self.gtm_conf_invalid,
                "Manual Review": self.gtm_conf_manual}

    @property
    def python_top(self):
        s = self.python_scores()
        return max(s.values()) if s else None

    @property
    def gtm_top(self):
        s = self.gtm_scores()
        return max(s.values()) if s else None

    @property
    def features(self) -> dict:
        return _loads(self.features_json, {})

    @property
    def decision_trace(self) -> list:
        return _loads(self.decision_trace_json, [])

    @property
    def model_errors(self) -> dict:
        return _loads(self.model_errors_json, {})

    @property
    def thresholds(self) -> dict:
        return _loads(self.consistency_thresholds_json, {})


class RuleValidationLog(db.Model):
    __tablename__ = "rule_validation_logs"

    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False)
    evaluation_id = db.Column(db.Integer, db.ForeignKey("model_evaluations.id"), nullable=True)
    policy_name = db.Column(db.String(120), nullable=True)
    rules_json = db.Column(db.Text, default="[]")              # every rule with severity + fired + message
    contradictions_json = db.Column(db.Text, default="[]")
    duplicate_flags_json = db.Column(db.Text, default="[]")
    missing_documents_json = db.Column(db.Text, default="[]")
    overall_rule_status = db.Column(db.String(20), nullable=False, default="PASS")
    execution_timestamp = db.Column(db.DateTime, default=utcnow)

    @property
    def rules(self) -> list:
        return _loads(self.rules_json, [])

    def of(self, severity: str) -> list:
        return [r for r in self.rules if r.get("fired") and r.get("severity") == severity]

    @property
    def passed(self) -> list:
        return [r for r in self.rules if not r.get("fired")]

    @property
    def contradictions(self) -> list:
        return _loads(self.contradictions_json, [])

    @property
    def duplicate_flags(self) -> list:
        return _loads(self.duplicate_flags_json, [])

    @property
    def missing_documents(self) -> list:
        return _loads(self.missing_documents_json, [])


class ReviewerAction(db.Model):
    """Human decision. The AI recommendation it overrode stays on the claim's evaluation rows."""
    __tablename__ = "reviewer_actions"

    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    previous_status = db.Column(db.String(40), nullable=False)
    previous_recommendation = db.Column(db.String(40), nullable=True)
    reviewer_decision = db.Column(db.String(40), nullable=False)
    is_override = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.Text, nullable=True)
    comments = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow)

    reviewer = db.relationship("User", foreign_keys=[reviewer_id])


class AuditLog(db.Model):
    """Append-only audit trail (SRS xlvii). Nothing in the app updates or deletes rows."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user_role = db.Column(db.String(30), nullable=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.String(50), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=utcnow, index=True)

    actor = db.relationship("User", foreign_keys=[user_id])

    @property
    def details(self) -> dict:
        return _loads(self.details_json, {})


class SystemSetting(db.Model):
    """Administrator-managed settings (e.g. expiry alert window, SRS ix)."""
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    @classmethod
    def get_val(cls, key: str, default: str = None) -> str:
        row = cls.query.filter_by(setting_key=key).first()
        return row.setting_value if row else default

    @classmethod
    def get_int(cls, key: str, default: int = 30) -> int:
        try:
            return int(cls.get_val(key, str(default)))
        except (TypeError, ValueError):
            return default

    @classmethod
    def set_val(cls, key: str, value, description: str = None):
        row = cls.query.filter_by(setting_key=key).first()
        if row is None:
            row = cls(setting_key=key, setting_value=str(value), description=description)
            db.session.add(row)
        else:
            row.setting_value = str(value)
            if description:
                row.description = description
        return row


class BatchRun(db.Model):
    """Admin batch evaluation of an uploaded CSV. Processed a chunk per poll (no background worker needed);
    nothing is written to claims; results are kept for download."""
    __tablename__ = "batch_runs"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_uuid("BAT"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="queued")      # queued | running | done | failed
    total = db.Column(db.Integer, nullable=False, default=0)
    processed = db.Column(db.Integer, nullable=False, default=0)
    rows_json = db.Column(db.Text, nullable=False, default="[]")
    results_json = db.Column(db.Text, nullable=False, default="[]")
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    created_by = db.relationship("User")

    def rows(self) -> list:
        return json.loads(self.rows_json or "[]")

    def results(self) -> list:
        return json.loads(self.results_json or "[]")
