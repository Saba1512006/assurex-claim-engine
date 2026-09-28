# AI Tool Usage Declaration

Required by SRS §1.8 (item 9) and deliverable 15. Every AI tool used during development is listed
below. **The final claim decision is never produced by a generative-AI service**: it comes from the
team's Python classification model, the Google Teachable Machine model, the warranty rule engine and the
decision table running inside this application. No external AI API is called at runtime.

> **Correction.** An earlier version of this file stated that no AI code generators were used. That is
> not accurate for the v2 upgrade described below, so this declaration replaces it.

---

## 1. Google Teachable Machine (required by the SRS)

| Field | Declaration |
|---|---|
| Tool | Google Teachable Machine (teachablemachine.withgoogle.com), Google LLC |
| Purpose | Image classification of Claim Summary Cards into Valid Claim / Invalid Claim / Manual Review |
| Type of assistance | Browser-based transfer-learning of an image model on the team's training cards; TensorFlow Lite export |
| Files / modules affected | `model/teachable_machine/` (export + `labels.txt` + `evaluation.json`), consumed by `src/core/gtm_classifier_v2.py` |
| Status | Trained by the team in the browser on the v3 cards and installed as `gtm-514702678b8c` (test accuracy 93.8%); see `documentation/GTM_EVIDENCE.md` |
| Testing | `notebooks/evaluate_gtm.py` / Admin › Models › Run evaluation on the 225 validation and 225 test cards |

## 2. Claude Code (Anthropic) — v2 upgrade

| Field | Declaration |
|---|---|
| Tool | Claude Code (Anthropic), an AI coding assistant |
| Date | 26 September 2026 |
| Purpose | Integrate the team's v2 upgrade kit (leakage-free dataset, calibrated model, square cards, RBAC) into the application, fix the defects the kit identified, redesign the web interface, write tests and update documentation |
| Prompt / type of assistance | "Complete the project using the attached v2 upgrade kit, model card and SRS; implement everything fully with a top-quality design." Code generation, refactoring, test writing, documentation drafting, running the training scripts and the test suite |
| Files / modules affected | Almost every module: `src/` (core pipeline, rules, security, services, api), `templates/`, `static/`, `config/`, `policies/`, `dataset_generator/`, `notebooks/`, `database/seed.py`, `tests/`, `reports/`, `documentation/`, `README.md`. Generated data: `data/raw`, `data/splits`, `data/summary_cards`, `model/python_model/` |
| What it did **not** do | Train the Teachable Machine model (requires the browser tool); decide any claim at runtime; invent metrics (every number in the docs is read from files the scripts produce) |
| Testing performed by the tool | 192 automated tests (`python -m pytest -q`), a page-by-page render check of every screen for all four roles, browser screenshots, and an end-to-end seed that submits the 11 demonstration claims through the live pipeline |

## 2b. Claude Code (Anthropic) — frontend rebuild

| Field | Declaration |
|---|---|
| Tool | Claude Code (Anthropic), an AI coding assistant |
| Date | 27 September 2026 |
| Purpose | Rebuild the web interface from the team's written brief, add the explainability, simulation and batch features it asked for, and test them |
| Prompt / type of assistance | The team's *AssureX Frontend Master Prompt* (PDF, 10 parts, prepared by Muhammad Azhar Nawaz), plus the instruction to implement all of it together with three model-explanation additions. Code generation, refactoring, test writing, running the test suites, browser screenshots, accessibility and Lighthouse audits |
| Files / modules affected | `templates/` (every page), `static/css/`, `static/js/`, `src/api/api.py`, `src/api/errors.py`, `src/services/` (`verdict`, `whatif`, `batch`, `model_card_service`, `receipt_scan`, `paging`), `src/core/explain_models.py`, `src/core/pipeline.py` (stored verdict payload and stage timings), `src/app_security.py`, `tests/` (contract, route-matrix and `tests/e2e/` browser tests), `scripts/subset_icons.py`, `README.md`, `documentation/PROJECT_REPORT.md` |
| What it did **not** do | Change the Claim Summary Card design or either model (tests re-render the test cards and fail if Teachable Machine accuracy could drop; the batch evaluator reproduces 89.3% and 93.8% on the test split); decide any claim at runtime |
| Testing performed by the tool | 225 automated tests including a route × role matrix over every guarded route; 13 browser journeys on a live seeded server with axe-core accessibility checks on 21 pages; Lighthouse on the public pages; screenshots at 1440, 1024 and 390 px |

## 2c. Claude Code (Anthropic) — styling pass, input rules and deployment fixes

| Field | Declaration |
|---|---|
| Tool | Claude Code (Anthropic), an AI coding assistant |
| Date | 27–28 September 2026 |
| Purpose | Visual polish requested by the team, form input rules, sign-in lockout countdown, landing-page hero background, dependency fixes for deployment, and updating the documentation to the final state |
| Prompt / type of assistance | The team's instructions, given one change at a time (for example "no numbers in name fields", "show a timer when sign-in is locked", "premium navbar and footer", "preloader like the logo"). Code generation, CSS, tests, browser screenshots, running the test suites |
| Files / modules affected | `templates/` (navbar, footer, base, landing, auth, dashboards, claim detail, workbench, notifications), `static/css/`, `static/js/` (`app.js`, `instrument.js`, `hero_engine.js`, `hero_engine_math.js`), `static/img/brand/`, `src/rules/validator.py`, `src/api/auth.py`, `src/api/access.py`, `src/api/products.py`, `src/app.py`, `config/rbac.json` (lockout minutes), `requirements.txt`, `tests/` (`test_input_rules.py`, `test_hero_engine_math.py`, `tests/js/`, `tests/e2e/test_hero_engine.py`), README and `documentation/` |
| What it did **not** do | Change either model, the dataset or the Claim Summary Card (the accuracy guards re-score both models on every test run: 89.3% and 93.8%); decide any claim at runtime |
| Testing performed by the tool | 295 automated tests and 34 browser tests (overlap, contrast and pixel checks of the hero background at five widths, input rules, lockout countdown, accessibility with axe) |

### Required team entries (SRS: modifications, testing and verifier name)

The SRS requires the **team** to review, modify, test and understand AI output, and to name the member
who verified it. These rows must be filled in by the team — they are deliberately left blank rather than
written on the team's behalf:

| Module | Modifications made by the team | Tests run by the team | Verified by (team member) |
|---|---|---|---|
| Dataset generator & cards (`dataset_generator/`) | | | |
| Python model training (`notebooks/train_python_v2.py`) | | | |
| Teachable Machine training & evaluation | | | |
| Evaluation pipeline (`src/core/`) | | | |
| Rule engine & policies (`src/rules/`, `policies/`) | | | |
| Security & access control (`src/security/`, `config/rbac.json`) | | | |
| Web interface (`templates/`, `static/`) | | | |
| Frontend rebuild features (verdict, workbench, what-if, batch, model card) | | | |
| Styling pass, input rules, lockout countdown, hero background (27–28 Sept) | | | |
| Documentation & report | | | |

## 3. Other tools

| Tool | Use |
|---|---|
| scikit-learn, pandas, NumPy, Pillow, ReportLab, pdfplumber, Tesseract (pytesseract) | Libraries used by the application (not AI assistants) |
| Chart.js, Bootstrap Icons, Alpine.js (CSP build), IBM Plex fonts | Front-end libraries and fonts, self-hosted in `static/vendor/` |
| Playwright, axe-core (axe-playwright-python), Lighthouse | Browser testing, accessibility and performance audits (development only) |
| Mermaid | Rendering the report diagrams from `documentation/diagrams/*.mmd` |

Images: the demo "damage" and "serial" photos created by `database/seed.py` are synthetic drawings made
with Pillow, labelled as such on the image. No AI-generated imagery is used in the application.
