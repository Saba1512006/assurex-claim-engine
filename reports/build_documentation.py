"""Build the complete project documentation as one PDF and one Word file.

    python reports/build_documentation.py

Output: documentation/AssureX_Project_Documentation.pdf and .docx. Every chapter comes from the project's own
sources (the Markdown documents, the data and policy files, the evaluation reports and the screenshots), so
the combined document never drifts from them. The PDF is printed with Chromium (Playwright); the Word file is
converted from the same HTML with LibreOffice when it is installed.
"""
from __future__ import annotations

import base64
import csv
import html
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import markdown
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DOC = ROOT / "documentation"
OUT_PDF = DOC / "AssureX_Project_Documentation.pdf"
OUT_DOCX = DOC / "AssureX_Project_Documentation.docx"
REPO = "https://github.com/Saba1512006/assurex-claim-engine"

TEAM = [("Student1525913", "Saba Noor", "Team lead · integration, frontend direction, QA, documentation"),
        ("Student1524867", "Muhammad Sami", "Backend and ML pipeline developer · deployment"),
        ("Student1509222", "Muhammad Ghanyan", "Frontend design (Figma, colour palette, mobile checks)"),
        ("Student1505677", "Muhammad Sami ur Rehman", "Testing (sample claims, Chrome and mobile)")]


# ---------------------------------------------------------------- helpers
def img_uri(path: Path, max_w: int = 1500) -> tuple[str, int, int]:
    """Embed an image as a data URI, downscaled so the documents stay small; returns (uri, width, height)."""
    im = Image.open(path)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    if path.suffix.lower() == ".png" and im.mode in ("RGBA", "P", "LA") or "diagrams" in path.parts:
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=80, optimize=True)
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}", im.width, im.height


def img_tag(path: Path, alt: str, max_w: int = 1500, box_w: int = 640, box_h: int = 820) -> str:
    """<img> with explicit display size (px at 96 dpi) that fits the A4 text block; Word ignores CSS max-width."""
    uri, w, h = img_uri(path, max_w)
    scale = min(1.0, box_w / w, box_h / h)
    return f'<img src="{uri}" width="{round(w * scale)}" height="{round(h * scale)}" alt="{html.escape(alt)}">'


def figure(path: Path, caption: str, max_w: int = 1500, cls: str = "", box_w: int = 640) -> str:
    return (f'<figure class="{cls}">{img_tag(path, caption, max_w, box_w)}'
            f"<figcaption>{html.escape(caption)}</figcaption></figure>")


def md(text: str, base: Path) -> str:
    """Markdown -> HTML: drop the document's own H1, embed images, keep only absolute links."""
    text = re.sub(r"\A\s*# .*\n", "", text)

    def image(m):
        p = (base / m.group(2)).resolve()
        return f"\n\n<figure>{img_tag(p, m.group(1))}<figcaption>{html.escape(m.group(1))}</figcaption></figure>\n\n" if p.exists() else m.group(0)

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image, text)
    text = re.sub(r"(?<!!)\[([^\]]+)\]\((?!https?:)[^)]+\)", r"\1", text)      # relative links -> plain text
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])


def table(headers, rows, cls="") -> str:
    head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def section_of(text: str, heading: str) -> str:
    """One '## heading' section (with its sub-sections) of a Markdown document."""
    m = re.search(rf"^## {re.escape(heading)}.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return f"## {heading}\n{m.group(1)}" if m else ""


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------- generated chapters
def data_dictionary_html() -> str:
    dd = json.loads(read("data/data_dictionary.json"))
    out = ["<h3>Dataset data dictionary (<code>data/data_dictionary.json</code>)</h3>",
           table(["Column", "Description"], dd.items())]
    from src.models.entities import db  # noqa: F401  (registers every table on the metadata)
    rows = []
    for name, t in db.metadata.tables.items():
        cols = []
        for c in t.columns:
            tag = " (PK)" if c.primary_key else (" (FK → " + next(iter(c.foreign_keys)).column.table.name + ")" if c.foreign_keys else "")
            cols.append(c.name + tag)
        rows.append((name, len(t.columns), ", ".join(cols)))
    out += [f"<h3>Database tables ({len(rows)}, <code>src/models/entities.py</code>)</h3>",
            table(["Table", "Columns", "Fields (PK primary key, FK foreign key)"], rows, "small")]
    return "\n".join(out)


def dataset_chapter() -> str:
    stats = json.loads(read("data/dataset_statistics.json"))
    scen = json.loads(read("data/claim_scenarios.json"))
    parts = ["<p>One common dataset of synthetic warranty claims in two linked forms: structured CSV records for the "
             "Python model and Claim Summary Card images for Google Teachable Machine. Each CSV record and its card "
             "carry the same Claim ID, claim details and class label. Splits are made before any card is rendered, "
             "so a validation or test claim never appears in training in either form.</p>"]
    files = [("Raw dataset (1,500 claims)", "data/raw/common_warranty_claims_1500.csv"),
             ("Training / validation / test CSV", "data/splits/train.csv, val.csv, test.csv (1,050 / 225 / 225)"),
             ("Model-ready feature matrices", "data/processed/{train,val,test}_features.csv"),
             ("Card images", "data/summary_cards/train/{valid,invalid,manual_review}/ (700 each), val/ (225), test/ (225)"),
             ("Claim ID ↔ image mapping", "data/claim_id_to_card_mapping.csv"),
             ("Labels", "data/labels.csv"),
             ("Scenario definitions", "data/claim_scenarios.json"),
             ("Statistics", "data/dataset_statistics.json"),
             ("Data dictionary", "data/data_dictionary.json"),
             ("Generation scripts", "dataset_generator/generator_v2.py, dataset_generator/build_cards_v2.py")]
    parts.append(table(["Item", "File"], files))
    parts.append("<h2>Dataset statistics</h2>")
    parts.append(table(["Class", "Claims"], stats.get("by_class", {}).items()))
    for key, val in stats.items():
        if key in ("total", "by_class", "by_scenario"):
            continue
        if isinstance(val, dict) and val and all(not isinstance(v, (dict, list)) for v in val.values()):
            parts.append(f"<h3>{html.escape(key.replace('_', ' ').capitalize())}</h3>" + table(["Value", "Count"], val.items()))
    parts.append("<h2>Claim scenarios and labelling rules</h2>")
    parts.append(f"<p>{html.escape(scen.get('precedence', ''))}. {html.escape(scen.get('label_noise', ''))}.</p>")
    parts.append(table(["Scenario", "Class", "Definition", "Claims"],
                       [(s["scenario"], s["class"], s["definition"], s.get("claims", "")) for s in scen["scenarios"]]))
    with open(ROOT / "data/claim_id_to_card_mapping.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    parts.append("<h2>Claim ID and image filename mapping (first rows)</h2>")
    parts.append(table(rows[0], rows[1:9], "small"))
    parts.append("<h2>Sample Claim Summary Cards</h2><p>One training card per class. A card shows claim facts only — "
                 "never the Python prediction, a confidence score or the final decision.</p><div class=\"cards\">")
    for cls, label in (("valid", "Valid Claim"), ("invalid", "Invalid Claim"), ("manual_review", "Manual Review")):
        first = sorted((ROOT / "data/summary_cards/train" / cls).glob("*.jpg"))[0]
        parts.append(figure(first, f"{label}: {first.name}", 600, box_w=200))
    parts.append("</div>")
    return "\n".join(parts)


def policies_chapter() -> str:
    parts = ["<p>Warranty rules are configuration, not code: one JSON file per category in <code>policies/</code>, "
             "loaded by <code>src/rules/policy_store.py</code> and editable (with preview and version history) in "
             "Admin › Policies.</p>"]
    for p in sorted((ROOT / "policies").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        rows = [(k.replace("_", " "), ", ".join(map(str, v)) if isinstance(v, list) else v) for k, v in d.items()]
        parts.append(f"<h2>{html.escape(d.get('category', p.stem))} — <code>policies/{p.name}</code></h2>")
        parts.append(table(["Field", "Value"], rows))
    return "\n".join(parts)


def comparison_chapter(limit: int | None = 30) -> str:
    text = read("reports/model_comparison_report.md")
    text = text.split("## Per-claim results")[0]
    parts = [md(text, ROOT / "reports")]
    with open(ROOT / "reports/model_comparison_report.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    keep = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 18]
    shown = rows[1:] if limit is None else rows[1:limit + 1]
    title = f"all {len(shown)} unseen test claims" if limit is None else f"first {len(shown)} of {len(rows) - 1} unseen test claims"
    parts.append(f'<section class="wide"><h2>Per-claim results ({title})</h2>'
                 "<p>Every column, including the warranty-rule result, missing documents, contradictions, duplicate "
                 "indicators and the explanation of each disagreement, is in "
                 "<code>reports/model_comparison_report.csv</code>.</p>")
    parts.append(table([rows[0][i] for i in keep], [[r[i] for i in keep] for r in shown], "tiny"))
    parts.append("</section>")
    return "\n".join(parts)


def tests_chapter() -> str:
    res = read("reports/test_results.txt").splitlines()
    summary = [ln for ln in res[:8] if ln.strip()]
    files = {}
    for ln in res:
        m = re.match(r"\s+(PASSED|FAILED|ERROR)\s+(tests/[^:]+)::", ln)
        if m:
            files.setdefault(m.group(2), [0, 0])[0 if m.group(1) == "PASSED" else 1] += 1
    return (md(read("documentation/TEST_CASES.md"), DOC)
            + "<h2>Latest test run</h2><pre>" + html.escape("\n".join(summary)) + "</pre>"
            + table(["Test file", "Passed", "Failed"], [(k, v[0], v[1]) for k, v in sorted(files.items())], "small")
            + "<p>Per-test results: <code>reports/test_results.txt</code>.</p>")


def guide_chapter() -> str:
    readme = read("README.md")
    quick = section_of(readme, "Quick start").split("### Testing the deployed application")[0]
    parts = [md(quick + "\n".join(section_of(readme, h) for h in (
        "How to use it", "How a claim is decided", "Security", "Repository layout", "Known limitations")), ROOT)]
    parts.append("<h2>Screens of the working application</h2>")
    caps = {}
    for ln in read("screenshots/README.md").splitlines():
        m = re.match(r"\|\s*([0-9]{2}_[^|]+?\.(?:jpg|png))\s*\|\s*(.+?)\s*\|$", ln)
        if m:
            caps[m.group(1)] = m.group(2)
    for f in sorted((ROOT / "screenshots").glob("*")):
        if f.suffix.lower() not in (".jpg", ".png") or f.name.startswith(("20_", "22_", "23_", "24_", "25_")):
            continue
        cap = caps.get(f.name, f.stem.split("_", 1)[1].replace("_", " ").capitalize())
        im = Image.open(f)
        if im.height > im.width * 2.2:                      # full-page captures: show the top part
            crop = f.with_suffix(".crop.jpg")
            im.convert("RGB").crop((0, 0, im.width, int(im.width * 1.25))).save(crop, "JPEG", quality=85)
            parts.append(figure(crop, f"{f.name} — {cap} (top of the page)", 1300, "shot"))
            crop.unlink()
        else:
            parts.append(figure(f, f"{f.name} — {cap}", 1300, "shot"))
    return "\n".join(parts)


def gtm_chapter() -> str:
    out = [md(read("documentation/GTM_EVIDENCE.md"), DOC), "<h2>Teachable Machine screenshots</h2>"]
    for name, cap in (("23_gtm_v3_training.png", "Run 2 (v3 cards): the three classes, 700 images each, model trained"),
                      ("24_gtm_v3_preview_test.png", "Run 2: preview test on an unseen card"),
                      ("25_gtm_v3_evaluation.png", "Run 2: evaluation of the installed model in the application"),
                      ("20_gtm_training.png", "Run 1 (v2 cards): training"),
                      ("22_gtm_evaluation.png", "Run 1: evaluation (54.2% test accuracy, replaced)")):
        p = ROOT / "screenshots" / name
        if p.exists():
            out.append(figure(p, cap, 1400, "shot"))
    return "\n".join(out)


def deployment_chapter() -> str:
    quick = section_of(read("README.md"), "Quick start")
    testing = quick.split("### Testing the deployed application", 1)[-1] if "### Testing" in quick else ""
    return md("| Item | Value |\n|---|---|\n"
              "| Public application URL | https://assurex.pythonanywhere.com |\n"
              f"| Source code | {REPO} |\n"
              "| Production server | `gunicorn wsgi:app` (Render: `render.yaml`; PythonAnywhere: the WSGI file imports "
              "`application` from `wsgi.py`) |\n"
              "| Health check | `/healthz` reports whether both models are loaded |\n"
              "| Free-tier limitation | The free PythonAnywhere account runs Python 3.10 with a 512 MB disk quota, so both "
              "models can show as *Unavailable* there and claims then go to manual review; the full pipeline runs "
              "locally (see the installation instructions) and is shown in the demonstration video |\n\n"
              "## Testing the deployed application" + testing, ROOT)


# ---------------------------------------------------------------- document
def chapters():
    report = read("documentation/PROJECT_REPORT.md")
    report = re.sub(r"\A# .*?(?=^## 1\. )", "", report, flags=re.S | re.M)          # cover page replaces the header
    report_html = md(report, DOC).replace("<h2>13. Data dictionary</h2>", "<h2>13. Data dictionary</h2>" + data_dictionary_html())
    return [
        ("Project report", report_html),
        ("Dataset", dataset_chapter()),
        ("Python classification model evidence", md(read("documentation/PYTHON_MODEL_EVIDENCE.md"), DOC)),
        ("Google Teachable Machine evidence", gtm_chapter()),
        ("Model prediction and confidence comparison report", comparison_chapter()),
        ("Warranty policy files", policies_chapter()),
        ("Test cases and results", tests_chapter()),
        ("Installation instructions", md(read("documentation/INSTALLATION.md"), DOC)),
        ("Execution instructions and user guide", guide_chapter()),
        ("Deployed application", deployment_chapter()),
        ("Demonstration video", md(read("documentation/DEMO_VOICEOVER.md"), DOC)),
        ("Technical blog", md(read("documentation/BLOG_PUBLICATION.md"), DOC) + md(read("documentation/TECHNICAL_BLOG.md"), DOC)),
        ("Security and access-control design", md(read("documentation/RBAC_DESIGN.md"), DOC)),
        ("AI tool usage declaration", md(read("AI_USAGE.md"), ROOT)),
        ("Team contribution record and development log", md(read("documentation/TEAM_CONTRIBUTIONS.md"), DOC)
         + "<h2>Development log</h2>" + md(read("documentation/DEVELOPMENT_LOG.md"), DOC)),
        ("Submission checklist", md(read("documentation/SUBMISSION_CHECKLIST.md"), DOC)),
    ]


CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
@page wide { size: A4 landscape; margin: 14mm 12mm; }
body { font-family: 'DejaVu Sans', 'Liberation Sans', Arial, sans-serif; font-size: 9.6pt; line-height: 1.45; color: #0f172a; }
h1 { font-size: 20pt; color: #0b3b8c; border-bottom: 2px solid #1d5bd8; padding-bottom: 4px; margin: 0 0 12px; break-before: page; }
h2 { font-size: 13pt; color: #1d5bd8; margin: 16px 0 6px; break-after: avoid; }
h3 { font-size: 11pt; color: #0f172a; margin: 12px 0 4px; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.4pt; color: #1447b3; overflow-wrap: anywhere; }
pre { background: #f1f5f9; padding: 8px; font-size: 8pt; white-space: pre-wrap; border-radius: 4px; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 8.2pt; }
th, td { border: 1px solid #cbd5e1; padding: 3px 5px; vertical-align: top; text-align: left; overflow-wrap: break-word; hyphens: manual; }
td:first-child { min-width: 22mm; }
th { background: #e8eefc; }
tr { break-inside: avoid; }
table.small { font-size: 7.4pt; } table.tiny { font-size: 6.4pt; }
figure { margin: 8px 0 12px; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; height: auto; max-height: 205mm; border: 1px solid #e2e8f0; }
figcaption { font-size: 8pt; color: #64748b; margin-top: 3px; }
.cards { display: flex; gap: 8px; } .cards figure { flex: 1; }
section.wide { page: wide; break-before: page; }
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: center; }
.cover .brand { color: #1d5bd8; font-weight: bold; letter-spacing: .2em; font-size: 10pt; }
.cover h1.title { font-size: 34pt; border: 0; color: #0f172a; margin: 10px 0 4px; break-before: auto; }
.cover .sub { font-size: 14pt; color: #475569; margin-bottom: 26px; }
.toc ol { columns: 1; font-size: 10.5pt; line-height: 1.9; } .toc a { color: #0f172a; text-decoration: none; }
.toc h1 { break-before: page; }
"""


ABSTRACT = (
    "AssureX Claim Engine evaluates warranty claims for consumer electronics, home appliances and "
    "industrial tools. A customer or service center registers a product from its receipt (read by OCR), files a "
    "claim with evidence, and the application pre-processes the claim into model features. A calibrated Python "
    "classification model (HistGradientBoosting, 89.3% test accuracy on 225 unseen claims) scores the structured "
    "record; the same claim is drawn as a Claim Summary Card and classified by a Google Teachable Machine model "
    "(93.8% test accuracy). The two predictions and their confidences are compared (Strong Match, Acceptable Match, "
    "Weak Match, Model Disagreement, Uncertain Result), the category's warranty policy is executed from JSON "
    "configuration, contradictions, missing documents and duplicates are detected, and a decision table produces "
    "Likely Valid, Likely Invalid or Manual Review Required. Anything uncertain goes to a human reviewer, and every "
    "step is recorded in an audit trail. The application has four roles (customer, service-center staff, claim "
    "reviewer, administrator), 295 automated tests and 34 browser tests.")


def build_html(chs=None, doc_title: str = "Project documentation", about: str | None = None) -> str:
    """Cover, abstract, contents and numbered chapters as one printable HTML page."""
    chs = chapters() if chs is None else chs
    about = about or ("This document brings every deliverable of the SRS (§1.10) together: the project report, "
                      "dataset, both models' evidence, the comparison report, warranty policies, test cases and "
                      "results, installation and execution instructions with screens of the working application, "
                      "deployment, the demonstration video, the technical blog, the AI usage declaration and the team "
                      "contribution record.")
    cover = f"""<div class="cover">
<div class="brand">APTECH LIMITED · NEXTWAVE AI AND ML</div>
<h1 class="title">AssureX Claim Engine</h1>
<div class="sub">{html.escape(doc_title)}</div>
{table(["", ""], [("Group", "NN_DevStorm"), ("Batch", "2609E2'"), ("Faculty", "Sir Minhaj"),
                   ("Repository", REPO), ("Live application", "https://assurex.pythonanywhere.com"),
                   ("Date", date.today().strftime("%d %B %Y"))])}
{table(["Student ID", "Name", "Role"], TEAM)}
</div>"""
    abstract = md(f"## Abstract\n\n{ABSTRACT}\n\n{about}", DOC)
    toc = ('<div class="toc"><h1>Contents</h1><ol>' + "".join(
        f'<li><a href="#ch{i}">{html.escape(t)}</a></li>' for i, (t, _) in enumerate(chs, 1)) + "</ol></div>") if len(chs) > 1 else ""
    body = "".join(f'<h1 id="ch{i}">{i}. {html.escape(t)}</h1>\n{h}\n' for i, (t, h) in enumerate(chs, 1))
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>AssureX Claim Engine — {html.escape(doc_title)}</title>"
            f"<style>{CSS}</style></head><body>{cover}{abstract}{toc}{body}</body></html>")


def _chromium(pw):
    """Playwright's own Chromium, or a pre-installed one when the versions differ."""
    try:
        return pw.chromium.launch()
    except Exception:
        for exe in sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome")):
            return pw.chromium.launch(executable_path=str(exe))
        raise


def render(page_html: str, out_pdf: Path, footer: str, out_docx: Path | None = None) -> None:
    """Print the HTML to PDF with Chromium and, when LibreOffice is installed, convert it to Word."""
    from playwright.sync_api import sync_playwright
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / (out_pdf.stem + ".html")
        src.write_text(page_html, encoding="utf-8")
        with sync_playwright() as pw:
            b = _chromium(pw)
            pg = b.new_page()
            pg.goto(src.as_uri())
            pg.pdf(path=str(out_pdf), prefer_css_page_size=True, print_background=True, display_header_footer=True,
                   header_template="<span></span>",
                   footer_template='<div style="font-size:7pt;color:#64748b;width:100%;padding:0 16mm;display:flex;'
                                   f'justify-content:space-between"><span>AssureX Claim Engine — {html.escape(footer)} · '
                                   'Group NN_DevStorm</span><span>Page <span class="pageNumber"></span> of '
                                   '<span class="totalPages"></span></span></div>')
            b.close()
        print("written", out_pdf.relative_to(ROOT), f"{out_pdf.stat().st_size / 1e6:.1f} MB")
        if out_docx is None:
            return
        office = shutil.which("soffice") or shutil.which("libreoffice")
        if office:
            subprocess.run([office, "--headless", "--convert-to", "docx:MS Word 2007 XML", "--outdir", tmp, str(src)],
                           check=True, capture_output=True, timeout=600)
            shutil.copy(Path(tmp) / (out_pdf.stem + ".docx"), out_docx)
            print("written", out_docx.relative_to(ROOT), f"{out_docx.stat().st_size / 1e6:.1f} MB")
        else:
            print("LibreOffice not found: Word file skipped")


def build() -> None:
    render(build_html(), OUT_PDF, "Project Documentation", OUT_DOCX)


if __name__ == "__main__":
    build()
