"""Render the Mermaid sources in this folder to PNG (used by the project report).

    python documentation/diagrams/render.py path/to/mermaid.min.js

Needs Playwright + Chromium and a local copy of mermaid.min.js (npm pack mermaid@10).
The .mmd files are the source of truth; GitHub also renders them natively.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
HTML = """<!doctype html><html><body style="margin:0;background:#fff">
<pre class="mermaid">{src}</pre><script>{lib}</script>
<script>mermaid.initialize({{startOnLoad:true, theme:'neutral', fontFamily:'DejaVu Sans, sans-serif',
flowchart:{{curve:'basis', htmlLabels:true}}, securityLevel:'loose'}});</script></body></html>"""


def main(lib_path: str) -> None:
    lib = Path(lib_path).read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(**({"executable_path": sys.argv[2]} if len(sys.argv) > 2 else {}))
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
        for src in sorted(HERE.glob("*.mmd")):
            page.set_content(HTML.format(src=src.read_text(encoding="utf-8"), lib=lib))
            page.wait_for_selector("pre.mermaid svg")
            page.locator("pre.mermaid svg").screenshot(path=str(src.with_suffix(".png")))
            print("rendered", src.with_suffix(".png").name)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1])
