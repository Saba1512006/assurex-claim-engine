"""Build a Medium-ready copy of documentation/TECHNICAL_BLOG.md.

Medium's editor has no tables and cannot fetch local images, so this script:
  * renders the blog to HTML with only the elements Medium keeps on paste
    (headings, paragraphs, bold/italic, lists, inline code, links);
  * turns every Markdown table into a bulleted list;
  * inserts a clearly marked placeholder where each image in images/ belongs.

Open medium_article.html in a browser, select all, copy, paste into a new Medium story, then replace each
yellow placeholder with its image (see README.md in this folder).

Run:  python documentation/medium/build_medium.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
BLOG = HERE.parent / "TECHNICAL_BLOG.md"
REPO_URL = "https://github.com/Saba1512006/assurex-claim-engine"

# (heading the image follows, file, caption) — the image goes at the END of that section.
IMAGES = [
    ("Application architecture", "01_architecture.png",
     "AssureX architecture: every request passes access control; every evaluation runs the same pipeline."),
    ("Google Teachable Machine training and the Claim Summary Card", "02_card_v2_vs_v3.png",
     "The same claim drawn as a v2 card (54.2% image-model accuracy) and a v3 card (93.8%)."),
    ("Confidence-score comparison", "03_claim_page.jpg",
     "A claim page: both models' predictions, the consistency status, the card and the decision trace."),
    ("Model disagreement cases", "04_model_evaluation.png",
     "Both models evaluated on 225 unseen test claims: Python 89.3%, Teachable Machine 93.8%."),
    ("Warranty-rule design", "05_decision_flow.png",
     "The decision table, read top to bottom: first matching row wins."),
]


def table_to_list(md: str) -> str:
    """Markdown table -> bullet list ('**first cell** — header: value; …')."""
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            head = [c.strip() for c in lines[i].strip("|").split("|")]
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                rest = "; ".join(f"{h}: {v}" for h, v in zip(head[1:], cells[1:]))
                out.append(f"* **{cells[0].strip('*')}** — {rest}")
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def placeholder(n: int, name: str, caption: str) -> str:
    return (f'<p class="ph"><b>[ IMAGE {n} — upload <code>images/{html.escape(name)}</code> here ]</b><br>'
            f'<i>Caption:</i> {html.escape(caption)}</p>')


def build() -> str:
    text = BLOG.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").strip()
    body = text.split("\n", 1)[1]
    lead = re.match(r"\s*\*(.+?)\*\s*\n", body, re.S)            # italic standfirst under the title
    subtitle, body = lead.group(1).replace("\n", " "), body[lead.end():]
    body = table_to_list(body)

    sections = re.split(r"(?m)^(## .+)$", body)
    out, n = [sections[0]], 0
    for k in range(1, len(sections), 2):
        heading, content = sections[k], sections[k + 1]
        out += [heading, content]
        for target, name, caption in IMAGES:
            if heading[3:].strip() == target:
                n += 1
                out.append("\n" + placeholder(n, name, caption) + "\n")
    body = "".join(out)
    body += (f"\n\n---\n\n*The full source code, dataset, both trained models, evaluation reports and tests are on "
             f"GitHub: [{REPO_URL.split('//')[1]}]({REPO_URL}).*\n")
    content = markdown.markdown(body, extensions=["sane_lists"])
    content = content.replace("<h2>", "<h3>").replace("</h2>", "</h3>")   # Medium: H3 = large heading
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Medium copy</title>
<style>
  body {{ max-width: 720px; margin: 40px auto; padding: 0 16px; font: 19px/1.6 Georgia, serif; color: #242424; background: #fff; }}
  h1 {{ font: 700 38px/1.2 -apple-system, Segoe UI, sans-serif; margin-bottom: 6px; }}
  h2.sub {{ font: 400 22px/1.4 -apple-system, Segoe UI, sans-serif; color: #6b6b6b; margin-top: 0; }}
  h3 {{ font: 700 26px/1.3 -apple-system, Segoe UI, sans-serif; margin-top: 40px; }}
  code {{ font: 15px Menlo, Consolas, monospace; background: #f2f2f2; padding: 1px 4px; border-radius: 3px; }}
  .ph {{ background: #fff5c2; border: 2px dashed #d4a800; padding: 12px 14px; border-radius: 8px; font-family: sans-serif; font-size: 16px; }}
  .note {{ font: 15px/1.5 sans-serif; background: #eef4ff; border-radius: 8px; padding: 12px 14px; }}
</style></head>
<body>
<p class="note">Copy from the title down to the last line (Ctrl+A, Ctrl+C) and paste into a new Medium story.
Then replace each yellow box with its image from <code>documentation/medium/images/</code>. This note is not part
of the article — delete it after pasting.</p>
<h1>{html.escape(title)}</h1>
<h2 class="sub">{html.escape(subtitle)}</h2>
{content}
</body></html>
"""


if __name__ == "__main__":
    out = HERE / "medium_article.html"
    out.write_text(build(), encoding="utf-8")
    print(f"written {out}")
