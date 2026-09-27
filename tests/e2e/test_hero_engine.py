"""The hero engine background: it never touches the foreground, follows the live check, and reads at every size.

Snapshots of each breakpoint (idle and reduced motion) are written to $E2E_SNAPSHOT_DIR (default: a temp folder)
for visual review; set $E2E_BASELINE_DIR to a folder of earlier snapshots to also compare against them."""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image, ImageChops

pytestmark = pytest.mark.e2e

SIZES = [(1440, 800), (1280, 720), (1024, 768), (768, 1024), (390, 844)]
SNAPS = Path(os.environ.get("E2E_SNAPSHOT_DIR") or Path(tempfile.gettempdir()) / "assurex-engine-snapshots")
BASELINE = os.environ.get("E2E_BASELINE_DIR")

GEOMETRY = """() => {
  const H = document.querySelector('.hero').getBoundingClientRect();
  const rel = (r) => ({ l: r.left - H.left, t: r.top - H.top, r: r.right - H.left, b: r.bottom - H.top });
  const shown = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { if (getComputedStyle(e).display === 'none') return false; } return true; };
  const avoid = {};
  document.querySelectorAll('[data-engine-avoid]').forEach((el) => { avoid[el.dataset.engineAvoid] = rel(el.getBoundingClientRect()); });
  const parts = [];
  const add = (sel, kind) => document.querySelectorAll(sel).forEach((el) => {
    if (!shown(el)) return;
    const r = el.getBoundingClientRect();
    const host = el.closest('[data-he-node]');
    if (r.width || r.height) parts.push({ kind, id: (host && host.dataset.heNode) || el.dataset.heLabel || el.dataset.hePath || el.dataset.heBranch || el.dataset.heTerm || kind, ...rel(r) });
  });
  add('.he-node [data-he-scale]', 'ring'); add('.he-node text', 'caption'); add('.he-core [data-he-scale]', 'core');
  add('.he-label', 'label'); add('.he-path', 'path'); add('.he-branch', 'branch'); add('.he-term', 'term'); add('.he-policy', 'policy');
  return { avoid, parts, tier: document.querySelector('[data-hero-engine]').dataset.tier };
}"""


def _open(browser, base_url, w, h, reduced=False):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce" if reduced else "no-preference")
    ctx.add_init_script("try { sessionStorage.setItem('ax-seen', 'off') } catch (e) {}")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => document.querySelector('[data-hero-engine]').classList.contains('is-ready')")
    page.wait_for_timeout(700)
    return ctx, page, errors


def _overlap(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]


@pytest.mark.parametrize("w,h", SIZES)
def test_engine_never_overlaps_the_foreground(browser, base_url, w, h):
    ctx, page, errors = _open(browser, base_url, w, h)
    g = page.evaluate(GEOMETRY)
    clashes = []
    for part in g["parts"]:
        for name, rect in g["avoid"].items():
            if name == "card" and part["kind"] == "ring" and part["id"] == "tm":
                continue                                   # the vision ring tucks behind the solid card by design
            if _overlap(part, rect):
                clashes.append(f"{part['kind']}:{part['id']} × {name}")
    ctx.close()
    assert clashes == [], f"{w}x{h} ({g['tier']}): " + ", ".join(clashes)
    assert errors == []


@pytest.mark.parametrize("w,h", [(1440, 800), (390, 844)])
def test_foreground_keeps_full_opacity(browser, base_url, w, h):
    ctx, page, _ = _open(browser, base_url, w, h)
    ops = page.evaluate("""() => [...document.querySelectorAll('[data-engine-avoid]')].map((el) => {
        let o = 1; for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
        return [el.dataset.engineAvoid, o]; })""")
    ctx.close()
    assert all(o == 1 for _, o in ops), ops


def _lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def test_text_contrast_over_the_rendered_background(browser, base_url):
    ctx, page, _ = _open(browser, base_url, 1440, 800, reduced=True)
    report = {}
    for sel in ["#hero-h", ".hero .lede", ".hero-metrics"]:
        el = page.locator(sel).first
        color = page.evaluate("(s) => getComputedStyle(document.querySelector(s)).color", sel)
        fg = tuple(int(x) for x in color[color.index("(") + 1:color.index(")")].split(",")[:3])
        page.evaluate("(s) => document.querySelectorAll(s + ', ' + s + ' *').forEach((e) => e.style.setProperty('color', 'transparent', 'important'))", sel)
        box = el.bounding_box()
        bg = Image.open(io.BytesIO(page.screenshot(clip=box))).convert("RGB")
        brightest = max(_lum(px) for px in bg.getdata())
        report[sel] = (_lum(fg) + 0.05) / (brightest + 0.05)
    ctx.close()
    assert all(ratio >= 4.5 for ratio in report.values()), report


def test_foreground_pixels_are_identical_with_and_without_the_layer(browser, base_url):
    ctx, page, _ = _open(browser, base_url, 1440, 800, reduced=True)
    rects = page.evaluate("""() => [...document.querySelectorAll('[data-engine-avoid]')].map((el) => {
        const r = el.getBoundingClientRect(), inset = el.dataset.engineAvoid === 'card' ? 18 : 0;   // skip the card's rounded corners
        return { x: r.left + inset, y: r.top + inset, width: r.width - 2 * inset, height: r.height - 2 * inset, name: el.dataset.engineAvoid }; })""")
    shots = {}
    for state in ("visible", "hidden"):
        page.evaluate("(v) => { document.querySelector('[data-hero-engine]').style.visibility = v; }", state)
        page.wait_for_timeout(100)
        shots[state] = {r["name"]: Image.open(io.BytesIO(page.screenshot(clip={k: r[k] for k in ("x", "y", "width", "height")}))).convert("RGB") for r in rects}
    ctx.close()
    diffs = [name for name in shots["visible"] if ImageChops.difference(shots["visible"][name], shots["hidden"][name]).getbbox()]
    assert diffs == [], f"foreground pixels changed in: {diffs}"


def test_running_a_check_lights_the_matching_outcome(browser, base_url):
    ctx, page, errors = _open(browser, base_url, 1440, 800)
    tone = {"Likely Valid": "valid", "Likely Invalid": "invalid", "Manual Review Required": "review"}
    for case in ("Liquid damage", "Grace +4 d", "Clean fault"):
        page.get_by_text(case, exact=True).click()
        expected = tone[page.locator("[data-im-stamp-text]").text_content()]
        page.wait_for_selector(f".he-term.{expected}.is-on", timeout=8000)
    with page.expect_response(lambda r: "/api/demo/evaluate" in r.url and r.status == 200, timeout=15000):
        page.get_by_role("button", name="Run the checks again").click()
    page.wait_for_function("() => !document.querySelector('[data-im-run]').disabled")
    expected = tone[page.locator("[data-im-stamp-text]").text_content()]
    page.wait_for_selector(f".he-term.{expected}.is-on", timeout=8000)
    on = page.evaluate("() => [...document.querySelectorAll('.he-term.is-on')].map((e) => e.dataset.heTerm)")
    ctx.close()
    assert on == [expected]
    assert errors == []


def test_reduced_motion_shows_a_still_diagram(browser, base_url):
    ctx, page, _ = _open(browser, base_url, 1440, 800, reduced=True)
    page.get_by_text("Liquid damage", exact=True).click()
    page.wait_for_timeout(300)
    state = page.evaluate("""() => ({ packets: document.querySelectorAll('.he-packet').length,
        spin: getComputedStyle(document.querySelector('.he-spin')).animationName,
        on: [...document.querySelectorAll('.he-term.is-on')].map((e) => e.dataset.heTerm) })""")
    ctx.close()
    assert state == {"packets": 0, "spin": "none", "on": ["invalid"]}


@pytest.mark.parametrize("w,h", SIZES)
@pytest.mark.parametrize("reduced", [False, True], ids=["idle", "reduced"])
def test_snapshots(browser, base_url, w, h, reduced):
    ctx, page, _ = _open(browser, base_url, w, h, reduced=reduced)
    page.evaluate("() => document.querySelectorAll('.he-packet').forEach((p) => p.remove())")
    SNAPS.mkdir(parents=True, exist_ok=True)
    name = f"hero-{w}x{h}-{'reduced' if reduced else 'idle'}.png"
    png = page.locator(".hero").screenshot(animations="disabled")
    (SNAPS / name).write_bytes(png)
    ctx.close()
    if BASELINE and reduced and (Path(BASELINE) / name).exists():
        a = Image.open(Path(BASELINE) / name).convert("RGB")
        b = Image.open(io.BytesIO(png)).convert("RGB")
        assert a.size == b.size, f"{name}: size changed {a.size} → {b.size}"
        diff = ImageChops.difference(a, b).convert("L")
        changed = sum(1 for px in diff.getdata() if px > 24) / (a.size[0] * a.size[1])
        assert changed < 0.01, f"{name}: {changed:.2%} of pixels changed"
