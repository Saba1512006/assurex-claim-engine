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
who verified it:

| Module | Modifications made by the team | Tests run by the team | Verified by (team member) |
|---|---|---|---|
| Dataset generator & cards (`dataset_generator/`) | Saba Noor reviewed the generated dataset (class-independent attributes, 4% label noise, stratified 1,050 / 225 / 225 split) and the v3 card design adopted after the first Teachable Machine run | Checked that no validation or test claim appears in training (CSV or image) and that each card matches its CSV record, Claim ID and label | Saba Noor |
| Python model training (`notebooks/train_python_v2.py`) | Saba Noor ran the training script, reviewed the three-algorithm comparison and the selection on the validation split | Checked the test metrics (89.3% accuracy, 89.2% macro F1), the leakage audit and the saved-model accuracy guard in the test suite | Saba Noor |
| Teachable Machine training & evaluation | Saba Noor trained the image model in the browser on the 2,100 training cards (epochs 50, batch 16, learning rate 0.001), retrained after the card redesign (v2 → v3), and installed the export through Admin › Models | Evaluated on the 225 validation and 225 test cards (93.8% test accuracy, 97.3% validation) and reviewed the misclassified samples | Saba Noor |
| Evaluation pipeline (`src/core/`) | Muhammad Sami wrote the first pipeline (OCR, comparison, decision engine) before the v2 upgrade; the team kept the v2 decision table and thresholds after review | Deployed and ran the app on PythonAnywhere and locally; Saba Noor compared the live-check results with the model card figures | Muhammad Sami, Saba Noor |
| Rule engine & policies (`src/rules/`, `policies/`) | Muhammad Sami wrote the original rule set, multi-category policies, serial verification and contradiction/duplicate checks; kept as the basis of the config-driven v2 rules | Muhammad Sami created the `sample_claims/` suite covering the SRS demonstration cases; Sami ur Rehman ran all 11 through the app and reported the defects found | Muhammad Sami, Sami ur Rehman |
| Security & access control (`src/security/`, `config/rbac.json`) | Saba Noor reviewed the role permissions and asked for the one-minute lockout and the server-side input rules | Signed in as each of the four roles and checked what each can open; tested the lockout countdown and the rate-limit page | Saba Noor |
| Web interface (`templates/`, `static/`) | Muhammad Sami tuned the live check card height and hero padding (28 Sept); Saba Noor requested and reviewed every page change | Saba Noor ran the app locally on Windows and checked each page for all four roles; Sami ur Rehman tested the pages in Chrome and on mobile; Muhammad Ghanyan checked the mobile view | Saba Noor, Sami ur Rehman |
| Frontend rebuild features (verdict, workbench, what-if, batch, model card) | Built from the team's written brief; Muhammad Ghanyan's Figma designs for the login and dashboard pages and colour palette guided the look | Sami ur Rehman ran the 11 sample claims through the app and tested the pages in Chrome and on mobile; Muhammad Ghanyan checked the mobile view | Saba Noor, Sami ur Rehman |
| Styling pass, input rules, lockout countdown, hero background (27–28 Sept) | Saba Noor specified each change and asked for corrections after testing (menu scrolling, notifications link, footer layout, hero placement, text clipping, lockout time) | Typed digits into name fields and letters into phone fields, locked an account with five wrong passwords and watched the countdown, checked the landing page at several window sizes | Saba Noor |
| Documentation & report | Saba Noor corrected links, figures and wording; the blog was published on Medium from her account | Checked every figure against `reports/` and the model files | Saba Noor |

## 3. Other tools

| Tool | Use |
|---|---|
| scikit-learn, pandas, NumPy, Pillow, ReportLab, pdfplumber, Tesseract (pytesseract) | Libraries used by the application (not AI assistants) |
| Chart.js, Bootstrap Icons, Alpine.js (CSP build), IBM Plex fonts | Front-end libraries and fonts, self-hosted in `static/vendor/` |
| Playwright, axe-core (axe-playwright-python), Lighthouse | Browser testing, accessibility and performance audits (development only) |
| Mermaid | Rendering the report diagrams from `documentation/diagrams/*.mmd` |

Images: the demo "damage" and "serial" photos created by `database/seed.py` are synthetic drawings made
with Pillow, labelled as such on the image. No AI-generated imagery is used in the application.
