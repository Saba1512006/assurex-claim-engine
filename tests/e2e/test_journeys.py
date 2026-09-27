"""Browser journeys on a live seeded server with the real models. Each test also fails on any console error,
page error, 5xx or missing static file (see conftest.open_session)."""
from __future__ import annotations

import re
import sys

import pytest

from tests.e2e.conftest import ACCOUNTS, ROOT

pytestmark = pytest.mark.e2e
sys.path.insert(0, str(ROOT))


def _receipt(tmp_path, serial: str) -> str:
    from tests.conftest import receipt_pdf
    path = tmp_path / "receipt.pdf"
    path.write_bytes(receipt_pdf(["Invoice No: INV-2025-90001", "Date: 23/08/2025", "Product: FrostGuard 450L",
                                  "Model: FG-450", f"Serial No: {serial}", "Grand Total: 1,099.00", "Retailer: Home Center"]))
    return str(path)


def test_landing_bench_runs_the_real_pipeline(open_session):
    s = open_session()
    page = s.go("/")
    for case, expected in (("Clean hardware fault", "Likely Valid"), ("Liquid damage", "Likely Invalid"),
                           ("Warranty ended", "Manual Review Required")):
        page.get_by_text(case).first.click()
        page.get_by_role("button", name="Run the checks").click()
        page.wait_for_function("(t) => document.querySelector('[x-data=bench]').innerText.includes(t)", arg=expected, timeout=15000)
    s.shot("landing")


def test_persona_sign_in_and_customer_dashboard(open_session):
    s = open_session()
    page = s.go("/login")
    assert "CustomerPass123!" not in page.inner_text("body")               # passwords are never shown as text
    page.get_by_role("button", name=re.compile("^Customer")).click()
    page.wait_for_url(re.compile("/claims/"))
    for heading in ("Needs your attention", "Products", "Claims"):
        assert page.get_by_role("heading", name=heading, exact=True).is_visible()
    s.shot("customer-dashboard")


def test_product_registration_reads_the_receipt(open_session, tmp_path):
    s = open_session("customer")
    page = s.go("/products/new")
    page.set_input_files("input[name=receipt]", _receipt(tmp_path, "SN-E2E-0000001"))
    page.wait_for_selector("[data-pstep='2']:not([hidden])", timeout=15000)
    assert page.input_value("input[name=serial_number]") == "SN-E2E-0000001"
    assert "prefilled" in page.get_attribute("input[name=serial_number]", "class")
    page.select_option("select[name=category]", "Home Appliances")
    page.fill("input[name=brand]", "FrostGuard")
    page.get_by_role("button", name="Register product").click()
    page.wait_for_url(re.compile(r"/products/PRD-"))
    assert page.get_by_role("heading", name="FrostGuard 450L").is_visible()


def test_claim_wizard_autosaves_reads_the_receipt_and_shows_the_verdict(open_session, tmp_path):
    s = open_session("customer")
    page = s.go("/claims/new")
    page.locator("label.pick", has_text="SN-FRO-2209381").click()          # the seeded FrostGuard
    page.click("[data-step='0'] [data-next]")
    page.evaluate("""() => { const s = document.querySelector('[data-fault-select]');
        s.value = [...s.options].find(o => o.value && !o.parentElement.disabled).value; s.dispatchEvent(new Event('change', {bubbles: true})); }""")
    page.select_option("select[name=damage_type]", "Manufacturing Defect")
    page.fill("input[name=fault_occurrence_date]", page.evaluate("new Date(Date.now() - 3 * 864e5).toISOString().slice(0, 10)"))
    page.fill("textarea[name=fault_description]", "The compressor stops after ten minutes and the freezer warms up.")
    page.click("[data-step='1'] [data-next]")
    page.wait_for_function("() => document.querySelector('[data-draft-id]').value.startsWith('CLM-')", timeout=10000)
    page.set_input_files("input[name=receipt]", _receipt(tmp_path, "SN-FRO-2209381"))
    page.wait_for_function("() => document.querySelector('[data-ocr-field=serial_number]').value !== ''", timeout=15000)
    assert "Matches the registered product" in page.inner_text("[data-ocr-note=serial_number]")
    s.shot("wizard-ocr")
    page.click("[data-step='2'] [data-next]")
    page.get_by_role("button", name="Submit claim").click()
    page.wait_for_url(re.compile(r"/claims/CLM-"))
    assert page.locator(".panel.verdict").count() == 1 and page.locator(".stamp").is_visible()
    s.shot("verdict")


def test_reviewer_workbench_keyboard_flow_and_double_submit_guard(open_session):
    s = open_session("reviewer")
    page = s.go("/reviewer/next")
    assert "/reviewer/claim/" in page.url
    if page.get_by_role("button", name="Take this claim").count():
        page.get_by_role("button", name="Take this claim").click()
        page.wait_for_load_state("networkidle")
    page.keyboard.press("i")                                              # request information
    assert page.is_checked("input[name=action][data-key=i]")
    assert page.evaluate("document.activeElement.name") == "comments"
    page.keyboard.type("Please upload a photo of the serial-number label.")
    sent = []
    page.on("request", lambda r: sent.append((r.method, r.url)))
    page.dblclick("[data-review-submit]")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    assert len([u for m, u in sent if m == "POST" and u.endswith("/decide")]) == 1   # the second click did nothing
    assert "Additional Information Required" in page.inner_text("main")
    page.keyboard.press("?")
    assert page.locator("dialog[data-help]").evaluate("d => d.open")
    s.shot("workbench")


def test_admin_what_if_and_batch(open_session):
    s = open_session("admin")
    page = s.go("/admin/what-if")
    before = page.inner_text("[data-wi-row=automation_rate] [data-wi-new]")
    page.eval_on_selector("#wi-min_confidence", "e => { e.value = 0.9; e.dispatchEvent(new Event('input', {bubbles: true})); }")
    page.wait_for_function("(b) => document.querySelector('[data-wi-row=automation_rate] [data-wi-new]').textContent !== b", arg=before, timeout=10000)
    assert page.is_enabled("[data-wi-apply]")
    s.shot("what-if")
    page = s.go("/admin/batch")
    lines = (ROOT / "data" / "splits" / "test.csv").read_text(encoding="utf-8").splitlines()[:26]
    page.set_input_files("input[name=file]", files=[{"name": "batch.csv", "mimeType": "text/csv", "buffer": "\n".join(lines).encode()}])
    page.get_by_role("button", name="Run the batch").click()
    page.wait_for_selector("[data-batch-done]:not(.hidden)", timeout=60000)
    assert "25 / 25" in page.inner_text("[data-batch-count]")


def test_role_change_signs_the_person_out_everywhere(open_session):
    victim = open_session()
    victim.go("/login")
    victim.page.fill("input[name=email]", "reviewer2@assurex.local")
    victim.page.fill("input[name=password]", ACCOUNTS["reviewer"][1])
    victim.page.click("form [type=submit]")
    victim.page.wait_for_load_state("networkidle")
    assert victim.go("/reviewer/queue").url.endswith("/reviewer/queue")
    admin = open_session("admin")
    page = admin.go("/admin/access/?q=reviewer2")
    page.on("dialog", lambda d: d.accept())
    with page.expect_navigation():                                       # auto-submits after the confirm dialog
        page.select_option("select[id^=role-]", "customer")               # the row control, not the role filter
    assert "is now Customer" in page.inner_text("[data-toasts]")
    victim.go("/reviewer/queue")
    assert "/login" in victim.page.url                                  # old session no longer valid


def test_reduced_motion_turns_animation_off(open_session):
    s = open_session("customer", reduced_motion=True)
    page = s.go("/claims/")
    href = page.locator("table a.row-link").first.get_attribute("href")
    page = s.go(href + "?fresh=1")
    stamp = page.locator(".stamp").first
    if stamp.count():
        assert stamp.evaluate("e => getComputedStyle(e).animationName") in ("none", "")
    assert page.locator("[data-preloader]").count() == 0


@pytest.mark.parametrize("who,paths", [
    (None, ["/", "/login", "/register", "/model-card", "/blog"]),
    ("customer", ["/claims/", "/products/", "/products/new", "/claims/new", "/claims/search", "/profile"]),
    ("reviewer", ["/reviewer/queue", "/reviewer/next"]),
    ("admin", ["/admin/dashboard", "/admin/what-if", "/admin/batch", "/admin/policies", "/admin/analytics", "/admin/audit",
               "/admin/access/", "/admin/models"]),
])
def test_pages_have_no_serious_accessibility_violations(open_session, who, paths):
    from axe_playwright_python.sync_playwright import Axe
    axe = Axe()
    s = open_session(who)
    found = []
    for path in paths:
        page = s.go(path)
        result = axe.run(page, options={"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa"]}})
        for v in result.response["violations"]:
            if v["impact"] in ("serious", "critical"):
                found.append(f"{path}: {v['id']} ({v['impact']}) x{len(v['nodes'])}: {v['nodes'][0]['target']}")
    assert found == [], "\n".join(found)


def test_phone_width_has_no_horizontal_scroll(open_session):
    s = open_session("customer", width=390)
    for path in ("/claims/", "/products/", "/claims/new", "/claims/search", "/profile"):
        page = s.go(path)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), path
    s.shot("customer-dashboard-phone")
