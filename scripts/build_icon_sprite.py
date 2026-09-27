"""Build static/img/icons.svg: a sprite of the Lucide icons the templates use (ISC licence, static/vendor/lucide/).

Icons are referenced in templates with the ui macro  icon('name')  and in JavaScript with  data-icon="name".
Icons whose name is chosen at render time are declared in a template comment:  {# icons: check x eye #}.
Run after using a new icon (needs the lucide-static npm package once, not at runtime):

    npm install lucide-static && python scripts/build_icon_sprite.py node_modules/lucide-static/icons
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPRITE = ROOT / "static" / "img" / "icons.svg"
USE = re.compile(r"""icon\(\s*['"]([a-z0-9-]+)['"]|data-icon=["']([a-z0-9-]+)["']""")
DECLARED = re.compile(r"\{#\s*icons:\s*([a-z0-9 -]+?)\s*#\}")


def used_icons() -> set[str]:
    names = set()
    for path in [*ROOT.glob("templates/**/*.html"), *ROOT.glob("static/js/*.js")]:
        text = path.read_text(encoding="utf-8")
        for a, b in USE.findall(text):
            names.add(a or b)
        for group in DECLARED.findall(text):
            names.update(group.split())
    return names


def build(icon_dir: Path) -> list[str]:
    symbols, missing = [], []
    for name in sorted(used_icons()):
        src = icon_dir / f"{name}.svg"
        if not src.exists():
            missing.append(name)
            continue
        body = re.search(r"<svg[^>]*>(.*)</svg>", src.read_text(encoding="utf-8"), re.S).group(1)
        body = re.sub(r"\s+", " ", body).strip()
        symbols.append(f'<symbol id="i-{name}" viewBox="0 0 24 24">{body}</symbol>')
    if missing:
        raise SystemExit(f"not in Lucide: {', '.join(missing)}")
    SPRITE.parent.mkdir(parents=True, exist_ok=True)
    SPRITE.write_text('<svg xmlns="http://www.w3.org/2000/svg"><!-- Lucide icons, ISC licence (static/vendor/lucide/LICENSE) -->'
                      + "".join(symbols) + "</svg>\n", encoding="utf-8")
    return sorted(used_icons())


if __name__ == "__main__":
    names = build(Path(sys.argv[1]))
    print(f"{len(names)} icons -> {SPRITE.relative_to(ROOT)}")
