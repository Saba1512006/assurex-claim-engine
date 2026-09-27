"""Route × role matrix generated from the app itself and config/rbac.json.

For every guarded endpoint and every role: a role without the endpoint's permission gets 403 (JSON for /api/),
a role with it never does; signed-out visitors are sent to sign in (401 JSON for /api/). New routes are covered
automatically, so a route can't ship with the wrong guard.
"""
import pytest

from src.security import rbac
from tests.conftest import login, make_center, make_user

ROLES = ["customer", "service_center_staff", "claim_reviewer", "administrator"]
SKIP = {"static", "auth.logout"}                      # logout would end the session mid-matrix


def _fill(pattern: str, values: dict) -> str:
    import re
    return re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", lambda m: values[m.group(1)], pattern)


def _cases(app):
    out = []
    for rule in app.url_map.iter_rules():
        view = app.view_functions.get(rule.endpoint)
        if rule.endpoint in SKIP or not getattr(view, "_rbac_guarded", False):
            continue
        for method in sorted((rule.methods or set()) & {"GET", "POST"}):
            # path parameters get values that exist nowhere, so allowed roles reach the object lookup (404)
            values = {a: ("x.csv" if a == "name" else "test" if a == "split" else "NOPE-0000") for a in rule.arguments}
            out.append((rule.endpoint, method, _fill(rule.rule, values), view._rbac_permission))
    return out


@pytest.fixture()
def people(app):
    center = make_center()
    return {r: make_user(f"{r}@x.io", r, center=center if r == "service_center_staff" else None) for r in ROLES}


def test_every_guarded_route_answers_each_role_as_rbac_json_says(app, people):
    cases = _cases(app)
    assert len(cases) > 60                                                # the matrix really covers the app
    wrong = []
    for role in ROLES:
        client = app.test_client()
        login(client, f"{role}@x.io")
        for endpoint, method, url, perm in cases:
            r = client.open(url, method=method, data={} if method == "POST" else None)
            allowed = perm is None or rbac.has_permission(people[role], perm)
            if allowed and r.status_code == 403:
                wrong.append((role, method, url, perm, "denied but rbac.json allows it"))
            if not allowed and r.status_code != 403:
                wrong.append((role, method, url, perm, f"got {r.status_code}, rbac.json denies it"))
            if not allowed and url.startswith("/api/") and (r.get_json() or {}).get("error", {}).get("code") != "NO_PERMISSION":
                wrong.append((role, method, url, perm, "API 403 without the JSON envelope"))
    assert wrong == [], "\n".join(map(str, wrong))


def test_signed_out_visitors_are_sent_to_sign_in(app):
    client = app.test_client()
    wrong = []
    for endpoint, method, url, perm in _cases(app):
        r = client.open(url, method=method, data={} if method == "POST" else None)
        if url.startswith("/api/"):
            ok = r.status_code == 401 and r.get_json()["error"]["code"] == "NOT_AUTHENTICATED"
        else:
            ok = r.status_code == 302 and "/login" in r.headers["Location"]
        if not ok:
            wrong.append((method, url, r.status_code))
    assert wrong == [], wrong
