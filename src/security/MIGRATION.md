# RBAC schema changes (run once)

```sql
ALTER TABLE users  ADD COLUMN session_version   INTEGER  NOT NULL DEFAULT 1;
ALTER TABLE users  ADD COLUMN failed_logins     INTEGER  NOT NULL DEFAULT 0;
ALTER TABLE users  ADD COLUMN locked_until      DATETIME NULL;
ALTER TABLE users  ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE users  ADD COLUMN last_login_at    DATETIME NULL;
ALTER TABLE users  ADD COLUMN service_center_id INTEGER  NULL;   -- staff scope
ALTER TABLE claims ADD COLUMN service_center_id INTEGER  NULL;   -- set from product/staff at creation
ALTER TABLE claims ADD COLUMN created_by_id     INTEGER  NULL;   -- who filed it (SoD)
ALTER TABLE products ADD COLUMN service_center_id INTEGER NULL;
```

Model fields: add the same columns to `User`, `Claim`, `Product` in `src/models/entities.py`.

## Wiring (src/app.py)
```python
from src.security.guards import init_rbac
init_rbac(app, db, User, AuditLog)     # after init_db(app), before blueprints are used
```

## Route migration pattern
```python
# before
@claim_bp.route("/documents/<string:doc_id>/correct-data", methods=["POST"])
@login_required
def correct_extracted_data(doc_id):
    doc = ClaimDocument.query.filter_by(document_id=doc_id).first_or_404()

# after
@claim_bp.route("/documents/<string:doc_id>/correct-data", methods=["POST"])
@require("document.correct_ocr")
def correct_extracted_data(doc_id):
    doc = authorize_object("document.correct_ocr",
                           ClaimDocument.query.filter_by(document_id=doc_id).first_or_404())
```

Reviewer decision:
```python
@require("review.decide")
def adjudicate(claim_id):
    claim = Claim.query.filter_by(claim_id=claim_id).first_or_404()
    target = ACTION_TO_STATUS[request.form["action"]]
    perm = "review.override" if is_override(claim, target) else "review.decide"
    authorize_object(perm, claim, target_status=target, reason=request.form.get("override_reason"))
```

Lists, search, dashboards, CSV export: always start from `scoped_claims(Claim)`, never `Claim.query`.

Registration: `role = registration_role(request.form.get("role"))` and delete the Staff / Reviewer /
Administrator cards from `templates/auth/register.html`. Remove `login_required` / `role_required`
from `src/api/auth.py` once every route uses `require`.
