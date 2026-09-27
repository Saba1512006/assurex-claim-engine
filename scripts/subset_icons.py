"""Write static/vendor/bootstrap-icons/bootstrap-icons.subset.css with only the icons the app uses.

The full stylesheet is 86 KB and almost all of it unused. Every `bi-*` name found in templates, JavaScript and
Python (icon maps in src/web.py and ui macros) is kept. Run after adding an icon:  python scripts/subset_icons.py
A test fails if a used icon is missing from the subset.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "static" / "vendor" / "bootstrap-icons" / "bootstrap-icons.min.css"
SUBSET = FULL.with_name("bootstrap-icons.subset.css")
SOURCES = [*ROOT.glob("templates/**/*.html"), *ROOT.glob("static/js/*.js"), *ROOT.glob("src/**/*.py")]
NAME = re.compile(r"\bbi-[a-z0-9]+(?:-[a-z0-9]+)*")


def used_icons() -> set[str]:
    return {m for path in SOURCES for m in NAME.findall(path.read_text(encoding="utf-8"))}


def build() -> tuple[int, int]:
    css = FULL.read_text(encoding="utf-8")
    head_end = css.index(".bi-")                                     # license, @font-face and the shared ::before rule
    head = css[:head_end]
    rules = dict(re.findall(r'\.(bi-[a-z0-9-]+)::before\{content:"(\\[0-9a-f]+)"\}', css[head_end:]))
    keep = sorted(n for n in used_icons() if n in rules)
    body = "".join(f'.{n}::before{{content:"{rules[n]}"}}' for n in keep)
    SUBSET.write_text(head + body + "\n", encoding="utf-8")
    return len(keep), SUBSET.stat().st_size


if __name__ == "__main__":
    n, size = build()
    print(f"{n} icons, {size / 1024:.1f} KB -> {SUBSET.relative_to(ROOT)}")
