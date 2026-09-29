# SRS submission checklist — where every deliverable is

Group **NN_DevStorm** · AssureX Claim Engine — NextWave AI and ML · Batch 2609E2' · Faculty: Sir Minhaj

Each row follows SRS §1.10 *Project Deliverables* (items 1–16). Paths are relative to the project folder.

**Start here:** `documentation/AssureX_Project_Documentation.pdf` contains every item below in 16 chapters (report, dataset, both models' evidence, comparison report, policies, test cases and results, installation, execution guide with screens, deployment, video, blog, security, AI usage, team record, this checklist).

## 16. Final submission checklist

| SRS item | Where |
|---|---|
| **Complete documentation (all deliverables in one file)** | `documentation/AssureX_Project_Documentation.pdf` (106 pages) and `.docx` — built by `python reports/build_documentation.py` |
| Project report | `reports/AssureX_Project_Report.pdf` (source: `documentation/PROJECT_REPORT.md`); also chapter 1 of the complete documentation |
| Public GitHub repository URL | https://github.com/Saba1512006/assurex-claim-engine |
| Complete source code | `src/`, `templates/`, `static/`, `database/`, `config/`, `wsgi.py` |
| Structured warranty claim dataset | `data/raw/common_warranty_claims_1500.csv`; splits `data/splits/{train,val,test}.csv` |
| Claim Summary Card image dataset | `data/summary_cards/train/{valid,invalid,manual_review}/` (700 each), `data/summary_cards/val/` (225), `data/summary_cards/test/` (225) |
| Python model files | `model/python_model/` (model, label encoder, preprocessing pipeline, feature schema, model card, sample predictions) |
| Google Teachable Machine model files | `model/teachable_machine/model_unquant.tflite`, `labels.txt`, `evaluation.json` |
| Warranty-policy files | `policies/consumer_electronics.json`, `home_appliances.json`, `industrial_tools.json` |
| Model-comparison report | `reports/model_comparison_report.md` and `.csv` (225 unseen test claims) |
| Test cases and results | `documentation/TEST_CASES.md`, `tests/`, results in `reports/test_results.txt` |
| Installation instructions | `documentation/INSTALLATION.md` |
| Execution instructions | `README.md` (*Quick start*, *How to use it*) |
| Deployment URL | https://assurex.pythonanywhere.com (free-tier limitation in `README.md` › *Known limitations*) |
| Demonstration video | `demo_video/AssureX_Demo.mp4`; also https://github.com/Saba1512006/assurex-claim-engine/blob/demo-video/AssureX_Demo.mp4; chapters in `documentation/DEMO_VOICEOVER.md` |
| Technical blog link | https://medium.com/@sabarajput672/building-assurex-two-models-one-rulebook-and-why-our-first-100-was-a-bug-bb8b9858b11c |
| AI_USAGE.md declaration | `AI_USAGE.md` |
| Team contribution record | `documentation/TEAM_CONTRIBUTIONS.md`; dated log in `documentation/DEVELOPMENT_LOG.md` |

## Detail by deliverable

| # | Deliverable | Where |
|---|---|---|
| 1 | Project report (all 35 required sections, with DFD, use case, activity, sequence and decision-flow diagrams) | `documentation/PROJECT_REPORT.md`, `reports/AssureX_Project_Report.pdf`, diagrams in `documentation/diagrams/` |
| 2 | Required folders: README.md, AI_USAGE.md, requirements.txt, LICENSE, src/, templates/, static/, data/, notebooks/, model/, policies/, dataset_generator/, database/, tests/, sample_claims/, documentation/, screenshots/, reports/, config/ | All present at the project root |
| 2 | Dataset-generation, pre-processing and training scripts | `dataset_generator/generator_v2.py`, `src/core/features.py`, `notebooks/train_python_v2.py` |
| 2 | Claim Summary Card generation | `src/core/card_v2.py`, `dataset_generator/build_cards_v2.py` |
| 2 | Rule engine, OCR and document processing | `src/rules/`, `src/ocr/`, `src/services/documents.py`, `src/services/receipt_scan.py` |
| 3 | Scenario definitions, labels, statistics, data dictionary, Claim ID ↔ image mapping | `data/claim_scenarios.json`, `data/labels.csv`, `data/dataset_statistics.json`, `data/data_dictionary.json`, `data/claim_id_to_card_mapping.csv` |
| 4 | Python model evidence (three algorithms compared, cross-validation, confusion matrix, per-class metrics, feature importance) | `documentation/PYTHON_MODEL_EVIDENCE.md`, `model/python_model/model_card_v2.json` |
| 5 | Teachable Machine evidence (classes, samples, configuration, observations, misclassified samples, retraining, screenshots) | `documentation/GTM_EVIDENCE.md`, `screenshots/20_*`–`25_*`, `reports/gtm_misclassified_*.csv` |
| 6 | Model prediction and confidence comparison (≥ 30 unseen claims; match status, confidence difference, consistency, rules, final decision) | `reports/model_comparison_report.md` / `.csv` (225 claims) |
| 7 | Three configurable warranty policies (coverage, start conditions, covered faults, exclusions, reporting period, repair and replacement conditions, authorised centers, grace period, mandatory documents, hard-fail / warning / manual-review rules) | `policies/*.json`, editable in Admin › Policies |
| 8 | Test cases (functional, integration, boundary, negative, security, database, OCR, both models, comparison, rules, contradiction, missing-document, duplicate, serial mismatch, low confidence, disagreement, hidden-test readiness) | `documentation/TEST_CASES.md`, `tests/` |
| 8 | The 11 demonstration claims | `sample_claims/01_…` to `11_…`, loaded by `python database/seed.py`; shown in the video, Part 4 |
| 9 | Installation instructions (prerequisites, OS, Python version, virtual environment, dependencies, database, seed, model placement, OCR, environment variables, folders, run and test commands, default administrator, troubleshooting) | `documentation/INSTALLATION.md` |
| 10 | Execution instructions (every step from registration to report export and tests) | `README.md` › *How to use it* |
| 11 | GitHub requirements (public, commit history, screenshots, test results, evaluator logins, limitations, assumptions, report, blog and video links) | `README.md`, `screenshots/`, `reports/test_results.txt` |
| 12 | Deployed application with evaluator and administrator logins | https://assurex.pythonanywhere.com, accounts in `README.md` › *Evaluator accounts* |
| 13 | Demonstration video (.mp4) | `demo_video/AssureX_Demo.mp4`, `documentation/DEMO_VOICEOVER.md` |
| 14 | Technical blog (≥ 2,000 words) | Medium link above; text in `documentation/TECHNICAL_BLOG.md` |
| 15 | AI tool usage declaration | `AI_USAGE.md` |

## Known gaps, stated openly

* **Commits from all team members** (SRS §1.10 item 11): commits exist under two GitHub accounts
  (Saba1512006, sami2515). Muhammad Ghanyan (Figma designs) and Muhammad Sami ur Rehman (testing)
  contributed outside the repository; see `documentation/TEAM_CONTRIBUTIONS.md`.
* **Deployment**: the free PythonAnywhere account runs Python 3.10 with a 512 MB disk quota, so both models
  can show as *Unavailable* there and claims then go to manual review. The full pipeline runs locally
  (`documentation/INSTALLATION.md`) and is shown working in the demonstration video.

## Sharing the project folder

Before uploading the folder (for example to Google Drive), leave out `venv/` (machine-specific, several
hundred MB) and `__pycache__/` folders. Everything else, including `demo_video/AssureX_Demo.mp4`, belongs in
the submission. The evaluator creates a fresh virtual environment with the *Quick start* commands in
`README.md`.
