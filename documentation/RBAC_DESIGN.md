# AssureX access control (RBAC + record scope)

## Model
Every request passes three checks, in order. Any failure denies.

1. **Permission** — the role holds the permission (`config/rbac.json`). Nothing is implied: deny by default.
2. **Scope** — the record is inside the role's reach: `own`, `service_center`, `assigned_or_queue`, `all`.
   Out-of-scope records return **404**, so IDs can't be probed.
3. **Constraints** — separation of duties, claim state machine, edit locks, admin self-protection.

The same scope drives list queries (`scoped_claims`) and single-record checks (`authorize_object`), so a
record hidden on the detail page can never leak through search, dashboards or CSV export.

## Roles
| Role | Reaches | Can't |
|---|---|---|
| Customer | own products, claims, documents | see others' records, edit a submitted claim, review |
| Service-center staff | records of their service center | other centers, decisions, policies |
| Claim reviewer | unassigned queue + claims assigned to them | decide a claim they filed, skip states, override without a reason |
| Administrator | everything, read | decide claims (config owners don't adjudicate), change own role, remove the last admin |

## Loopholes found in v1 and how v2 closes them
| # | v1 behaviour | v2 |
|---|---|---|
| 1 | `/register` accepted `role=Admin` | public sign-up creates customers only; others are invited |
| 2 | role read from the session cookie; role change / disable took effect only after logout | user reloaded from DB each request; `session_version` revokes old sessions |
| 3 | `/claims/documents/<id>/correct-data` had no ownership check (any user could edit any OCR data) | `authorize_object("document.correct_ocr", doc)` |
| 4 | object checks existed only for customers (`if role == customer and curr_user ...`) | scope check for every role |
| 5 | staff and reviewers saw every product, claim and document | service-center and assignment scopes |
| 6 | reviewer could approve own claim, re-open closed claims, override without reason | SoD + transition table + 20-char reason |
| 7 | login said whether an email exists; no lockout; session not rotated | one generic message, 5-try lockout, `session.clear()` on login |
| 8 | a new route was public unless someone added a decorator | before-request hook blocks any unguarded endpoint |
| 9 | no CSRF on state-changing forms | Flask-WTF CSRFProtect (`src/app_security.py`) |

## Evidence
`tests/test_rbac_policy.py` (32 cases, pure) and `tests/test_rbac_routes.py` (app-level: unguarded-route
inventory, escalation, enumeration, session revocation, role x endpoint matrix, IDOR).
