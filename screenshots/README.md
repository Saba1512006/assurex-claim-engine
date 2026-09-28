# Screenshots

Captured on 28 September 2026 from the running application with Playwright/Chromium, at 1440 px (desktop)
and 390 px (phone). Data: a fresh database created with `python database/seed.py` (7 users, 12 products,
12 claims). Both models were installed and loaded: the Python model `v2.0.0` and the Teachable Machine
model `gtm-514702678b8c`. Pages taller than the window are captured in full.

## Public pages

| File | Screen |
|---|---|
| 01_landing.jpg | Landing page: headline, measured results, the live check deciding a real sample claim, and the dual-engine background (Python ML and vision model feeding the decision core, policy engine and outcomes) |
| 02_login.jpg | Sign-in beside a scanned test-split Claim Summary Card, with one-click evaluator accounts |
| 31_register.jpg | Customer self-registration with field rules, password strength and a live match check |
| 27_model_card.jpg | Model card: both models' measured results as a technical report |

## Customer

| File | Screen |
|---|---|
| 03_customer_dashboard.jpg | Customer dashboard: at-a-glance KPIs, pending actions, products and claims |
| 04_claim_wizard.jpg | Claim wizard, step 1, with the readiness checklist |
| 26_claim_likely_valid.jpg | Claim page, *Likely Valid* (rule D07): both models agree, no blocking rule fired |
| 06_claim_likely_invalid_d01.jpg | Claim page, *Likely Invalid* (rule D01): rejected by a hard-fail warranty rule |
| 07_claim_tracking.jpg | Eight-stage claim tracking |
| 08_products.jpg | Registered products with warranty status |
| 09_product_warranty.jpg | Product and warranty page: coverage, documents and repair history |
| 30_notifications.jpg | Notifications page with unread and all tabs |

## Reviewer

| File | Screen |
|---|---|
| 10_reviewer_queue.jpg | Manual-review queue with filters and tabs |
| 11_reviewer_decision.jpg | Reviewer workbench: evidence, the verdict with both models' scores, warranty facts, and the decision bar with keyboard shortcuts |
| 05_claim_manual_review_d04.jpg | Claim page, *Manual Review Required* (rule D04): Δ 0.39, *Uncertain Result* because the image model's top confidence is below 0.60; the decision trace, the Claim Summary Card the image model saw and what moved each model |

## Administrator

| File | Screen |
|---|---|
| 12_admin_overview.jpg | Operations overview: filters, KPI cards, claims per week, recommendations, model agreement and confidence charts |
| 13_analytics_model_evidence.jpg | Analytics and model evidence |
| 14_policy_editor.jpg | Warranty policy and rule-severity editor, decision settings, version history |
| 15_models_teachable_machine.jpg | Model status, Teachable Machine installer and evaluation, sample cards |
| 16_access_control.jpg | Access control: people, roles, invitations, service centers, blocked attempts |
| 17_audit_trail.jpg | Audit trail with filters and export |
| 28_what_if_simulator.jpg | What-if simulator: try consistency thresholds against the stored decisions before applying them |
| 29_batch_evaluation.jpg | Batch evaluation of uploaded claim records through the real pipeline |

## Phone

| File | Screen |
|---|---|
| 18_mobile_dashboard.jpg | Customer dashboard at 390 px |
| 19_mobile_claim.jpg | Claim page at 390 px |

## Teachable Machine (training evidence)

| File | Screen |
|---|---|
| 20_gtm_training.png | Teachable Machine run 1 (v2 cards): 700 images per class, epochs 50 / batch 16 / lr 0.001, model trained |
| 22_gtm_evaluation.png | Run 1 evaluated in the app: 54.2% test accuracy (below target → card redesigned) |
| 23_gtm_v3_training.png | Teachable Machine run 2 (v3 colour-tile cards): the three classes, 700 samples each, model trained |
| 24_gtm_v3_preview_test.png | Run 2 preview on an unseen card: dates conflict + late reporting + excluded cause → Invalid Claim 99% |
| 25_gtm_v3_evaluation.png | Run 2 evaluated in the app: 93.8% test accuracy, 97.3% validation, 92.9% agreement with Python |

`00_system_architecture.jpg` is the system architecture diagram.
