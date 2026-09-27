"""End-to-end fixtures: a real server on a fresh seeded database (real models), a Chromium page per test, and a
console guard that fails any test whose pages logged an error or a failed request.

Run:  python -m pytest -m e2e tests/e2e            (screenshots land in docs/screenshots/)
Needs: pip install -r requirements-dev.txt && python -m playwright install chromium
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "docs" / "screenshots"
ACCOUNTS = {"customer": ("customer@assurex.local", "CustomerPass123!"), "staff": ("staff@assurex.local", "StaffPass123!"),
            "reviewer": ("reviewer@assurex.local", "ReviewerPass123!"), "admin": ("admin@assurex.local", "AdminPass123!")}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    port = _free_port()
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp / 'e2e.db'}", "UPLOAD_DIR": str(tmp / "uploads"),
           "RATELIMIT_ENABLED": "0", "SECRET_KEY": "e2e-only-secret", "PYTHONPATH": str(ROOT)}
    subprocess.run([sys.executable, "database/seed.py"], cwd=ROOT, env=env, check=True, capture_output=True)
    server = subprocess.Popen([sys.executable, "-c", f"from src.app import create_app; create_app().run(port={port}, use_reloader=False)"],
                              cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            urllib.request.urlopen(url + "/healthz", timeout=1)
            break
        except OSError:
            time.sleep(0.25)
    else:
        server.kill()
        pytest.fail("the e2e server did not start")
    yield url
    server.terminate()
    server.wait(10)


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or next(iter(sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))), None)
        b = p.chromium.launch(executable_path=str(path) if path else None)
        yield b
        b.close()


class Session:
    """A browser context for one person, with the problems its pages reported."""

    def __init__(self, browser, base_url, width=1440, reduced_motion=False):
        self.base = base_url
        self.ctx = browser.new_context(viewport={"width": width, "height": 900},
                                       reduced_motion="reduce" if reduced_motion else "no-preference")
        self.ctx.add_init_script("try { sessionStorage.setItem('ax-seen', '1') } catch (e) {}")
        self.page = self.ctx.new_page()
        self.problems: list[str] = []
        self.page.on("console", lambda m: self.problems.append(f"console: {m.text}") if m.type == "error" else None)
        self.page.on("pageerror", lambda e: self.problems.append(f"pageerror: {e}"))
        self.page.on("response", lambda r: self.problems.append(f"{r.status} {r.url}")
                     if r.status >= 500 or (r.status >= 400 and "/static/" in r.url) else None)

    def go(self, path: str):
        self.page.goto(self.base + path)
        self.page.wait_for_load_state("networkidle")
        return self.page

    def login(self, who: str):
        email, password = ACCOUNTS[who]
        self.go("/login")
        self.page.fill("input[name=email]", email)
        self.page.fill("input[name=password]", password)
        self.page.click("form [type=submit]")
        self.page.wait_for_load_state("networkidle")
        return self

    def shot(self, name: str):
        SHOTS.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


@pytest.fixture()
def open_session(browser, base_url):
    made = []

    def factory(who: str | None = None, **kw) -> Session:
        s = Session(browser, base_url, **kw)
        made.append(s)
        return s.login(who) if who else s
    yield factory
    problems = [p for s in made for p in s.problems]
    for s in made:
        s.ctx.close()
    assert problems == [], "pages reported errors:\n" + "\n".join(problems)
