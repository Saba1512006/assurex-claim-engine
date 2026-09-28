# Development log (SRS §1.8 item 3)

Entries record work completed, problems encountered, model failures, changes made and tests performed.
They are written from the Git history (`git log`); team members can add their own notes under each day.

## Commit activity by day

| Day | Commits | Accounts |
|---|---|---|
| 23 September 2026 | 3 | Muhammad Sami |
| 24 September 2026 | 18 | Muhammad Sami |
| 25 September 2026 | 15 | Muhammad Sami |
| 26 September 2026 | 19 | Muhammad Sami (13), Saba1512006 (6) |
| 27 September 2026 | 59 | Saba1512006 |
| 28 September 2026 | 6 | Muhammad Sami (3), Saba1512006 (3) |

## 23 September 2026 — first working version

**Work completed**
- Deployment files (gunicorn, Procfile, `render.yaml`); architecture diagram; database state synced.
- Product lookup mismatch fixed in the claim wizard; document upload inside the wizard.
- LICENSE, the `sample_claims/` suite, screenshots and export fixes; password confirmation on sign-up.

## 24 September 2026 — SRS functional requirements

**Work completed**
- Multi-role registration, profile management and navigation (SRS 1.6 i–ii); product registration and the
  common warranty interface (iii–iv); receipt/invoice upload and OCR extraction (v–vi); extracted-data
  verification and warranty tracking (vii–viii); expiry alerts and claim registration by staff and users
  (ix–x); claim information, fault evidence upload and repair history (xi–xiii).
- Document organisation, data validation and pre-processing (xiv–xvi); algorithm comparison on the admin
  dashboard (xviii); Claim Summary Card endpoint, Teachable Machine preview and prediction comparison UI.
- Confidence comparison with consistency thresholds; the warranty rule set; multi-category policies,
  serial verification from four sources and contradiction detection; missing-document and duplicate checks.

**Problems encountered and fixed**
- Quick-login reference error; a Jinja2 syntax error in the claim inspection page; demo claims not kept for
  the reviewer workbench; test clean-up leaking between tests.

## 25 September 2026 — decisions, dashboards and deployment fixes

**Work completed**
- Claim summary, preparation assistance and the final decision engine; decision explanation, manual-review
  workflow and reviewer override audit trail; claim tracking and notifications; admin duplicate alerts,
  search and analytics; reporting and audit coverage; model version tracking and error handling.
- UI clean-up (navbar, signed-in welcome card, user-facing labels).

**Problems encountered and fixed**
- PythonAnywhere startup failures: a missing `typing.Any` import and the `reportlab` import at start-up.
- Cross-platform model loading; strict OCR receipt validation (unreadable invoice images refused); a
  500 error in the intake wizard; OCR mock fallback.

## 26 September 2026 — v2 upgrade (AI-assisted, see AI_USAGE.md)

**Work completed**
- Replaced the dataset generator: attributes sampled independently of the class, labels derived from the
  policy files, 4% label noise, IDs assigned after shuffling, stratified 1,050/225/225 split.
- Retrained the Python model: three algorithms, selection on validation, sigmoid calibration, leakage audit,
  permutation importance, model card. Test accuracy 89.3% (macro-F1 89.2%, ROC-AUC 0.948).
- Redesigned the Claim Summary Card (600×600, bundled fonts, visual encoding of every feature) and rendered
  2,100 training / 225 validation / 225 test cards.
- Replaced the scikit-learn stand-in for Teachable Machine with a TFLite runtime, an admin installer and an
  evaluation script. The browser training itself is still to be done.
- Rule engine rewritten around config: 16 checks, severity per category in `policies/*.json`; decision table
  and routing in `config/decision_policy.json`; admin editors for both.
- Integrated role- and record-scoped access control, login hardening, CSRF, rate limits, CSP, upload
  sniffing. New UI for every page.

**Problems encountered**
- v1 scored 100%: `damage_type` was a relabelled class and claim IDs were ordered by class (leakage).
- v1 selected the model on the test split; v1 probabilities were near 1.000, so every comparison was a
  "Strong Match".
- Form options did not match training values; unknown values were silently encoded as zeros.
- OCR relied on hard-coded retailer/product lists; `Invoice` was read as an invoice number.
- Landscape cards were centre-cropped by Teachable Machine; fonts differed on Linux.

**Model failures observed**
- Invalid claims predicted as Manual Review (8/75 on test); 5 of 14 missed Invalid claims are the rare
  late-reporting scenario. Covered by the LATE_REPORTING hard-fail rule.
- Boundary claim (4 days into grace) gets 57% confidence → *Uncertain Result*; correctly routed to review.

**Changes made after testing**
- Warnings made advisory (blocking rules belong in `manual_review_rules`); receipt made the only mandatory
  document, with rules for missing supporting documents — aligns the decision table with the policy.
- Receipts with readable text but no invoice details are refused; scanned PDFs without text are accepted.

**Tests performed**
- 192 automated tests passing; every page rendered for all four roles; browser screenshots desktop/mobile;
  seed run submitting the 11 demonstration claims through the live pipeline.

**Teachable Machine, first run (card v2)**
- Trained in the browser on the 2,100 v2 cards (epochs 50, batch 16, learning rate 0.001) and installed
  as `gtm-ec95b4aa49b5`. Test accuracy 54.2% (validation 52.9%, macro F1 45.1%): below the 85% target.
- The TensorFlow 2.20 package on Windows no longer ships `tf.lite.Interpreter`; the runtime uses
  `ai-edge-litert`, which installed fine on Windows.
- Root cause found with an offline replica of Teachable Machine's trainer (`notebooks/tm_replica_check.py`):
  frozen MobileNet features cannot separate the v2 card's thin grey shapes (replica 58–66%).
- Card redesigned (v3, policy-relative colour tiles); replica test accuracy 92.9–94.2%. Training cards
  regenerated.

**Teachable Machine, second run (card v3)**
- Retrained in the browser on the 2,100 v3 cards with the same settings; installed as `gtm-514702678b8c`.
- Test accuracy 93.8% (macro F1 93.8%), validation 97.3%, agreement with the Python model 92.9%.
- Installing over the running model returned a 500 on Windows (memory-mapped .tflite could not be
  archived). Fixed by loading models from bytes; regression test added.

**Accuracy guards**
- Tests now re-score both saved models on every run: Teachable Machine on test cards rendered with the
  current card code and policy files (must stay ≥ 85% and equal to the recorded 93.8%), the Python model on
  the test split (≥ 85%, equal to 89.3%). A deliberate one-colour change to the card dropped the image model
  to 77.8% and failed the test, as intended.
- The policy editor warns when a limit drawn on the card is changed (the image model then needs retraining).

**Requirement audit against SRS §1.10**
- Added the standalone label encoder, preprocessing pipeline, feature schema, processed train/val/test CSVs,
  labels file, scenario definitions and all 225 sample test predictions (extracted from the saved model;
  a test proves they match it).
- Excel (.xlsx) export next to CSV for claims, analytics, audit and search, with the same formula guard.
- Test results file (`reports/test_results.txt`), team contribution record template, demo-video script,
  deployed-app testing guide in the README; a seeded demonstration claim where the two real models
  disagree.
- Teachable Machine error analysis: 12 of its 14 test errors are deliberately flipped labels.


## 27 September 2026 — frontend rebuild, styling and input rules (AI-assisted, see AI_USAGE.md)

**Work completed**
- Teachable Machine v3 results recorded (93.8% test accuracy) with evaluation screenshots, misclassified
  samples and the comparison report; accuracy guards for both models in the test suite; technical blog
  published on Medium and linked; seeded model-disagreement case; demo video script.
- Frontend rebuilt from the team's written brief: design tokens and app shell, verdict screen with agreement
  meter, landing live bench, model card, claim wizard with autosave and OCR split view, reviewer workbench,
  admin overview, what-if simulator, batch evaluator, policy editor with history, analytics, audit, access
  and models pages.
- Styling pass: premium navbar, sign-in and register with the card scanner, dashboards with KPI cards and
  validated chart colours, claim detail and workbench, new AssureX logo, footer, back-to-top button, animated
  preloader, and a hero engine background that follows the live check.
- Input rules on every form: no digits in names, cities, brands or retailers; no letters in phone or number
  fields; strict email format — enforced in the browser and on the server.
- Sign-in pause shortened to one minute after five wrong passwords, with a live countdown on the sign-in and
  rate-limit pages.

**Problems encountered and fixed**
- The Notifications item in the account menu opened the profile page; the account menu did not scroll on
  short screens; the admin menu had lost the Models, What-if and Batch links.
- Training-card download failed on Windows.
- A blurred, translucent card over the animated background made the live check slow enough to fail its browser
  test; the blur was removed.
- The rate-limit (5 per minute) message conflicted with the "15-minute lockout" hint; both now say one minute.

**Tests performed**
- 295 automated tests and 34 browser tests (route × role matrix, accessibility with axe, no overlap of the
  hero background with text at five screen widths, text contrast, input rules and lockout countdown).

## 28 September 2026 — deployment

**Work completed**
- Live check card height and hero padding tuned on the landing page (Muhammad Sami).
- Requirements: `tflite-runtime` on Linux and `ai-edge-litert` on Windows (Muhammad Sami).
- The rate-limit page made compatible with older Flask-Limiter releases; scikit-learn pinned back to 1.9.1
  so the saved Python model loads (Saba1512006). Work from a separate fork was merged into the main
  repository.

**Problems encountered**
- On the PythonAnywhere free account both models showed as *Unavailable*: the account runs Python 3.10,
  whose newest scikit-learn (1.7.2) cannot load the model trained with 1.9.1, and the TFLite runtime was
  not installed. Creating a Python 3.11 virtualenv failed on the account's system image, and installing the
  TFLite runtime hit the 512 MB disk quota.
- Render needed a payment card even for the free instance, so it was not used.
- Claims on the live site therefore go to manual review (the designed fallback). The full pipeline runs
  locally with the pinned requirements; see *Known limitations* in the README.

**Tests performed**
- 295 automated tests and 34 browser tests pass locally with Python 3.11 and scikit-learn 1.9.1
  (`reports/test_results.txt`).

## Open items
- Record and link the demonstration video (.mp4).
- Complete the team rows in `AI_USAGE.md` and `documentation/TEAM_CONTRIBUTIONS.md`.
- Add the Teachable Machine project link to `documentation/GTM_EVIDENCE.md`.
