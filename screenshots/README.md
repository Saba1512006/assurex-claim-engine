# Screenshots

Captured from the running application (`python database/seed.py && python src/app.py`) with Playwright/Chromium
at 1366 px (desktop) and 390 px (phone). The Teachable Machine export was not installed when they were taken,
so the image-model column shows "Model unavailable" and valid-looking claims wait in manual review (rule D04).

| File | Screen |
|---|---|
| 01_landing.jpg | Public landing page with measured model results |
| 02_login.jpg | Sign-in with evaluator accounts |
| 03_customer_dashboard.jpg | Customer dashboard: products, warranties, pending actions, notifications, receipts |
| 04_claim_wizard.jpg | Claim wizard step 1 with readiness checklist |
| 05_claim_manual_review_d04.jpg | Claim page: summary, model comparison, card, decision trace, rules, evidence |
| 06_claim_likely_invalid_d01.jpg | Claim rejected by a hard-fail rule (confirmed excluded damage) |
| 07_claim_tracking.jpg | Eight-stage tracking |
| 08_products.jpg / 09_product_warranty.jpg | Product list and product / warranty page |
| 10_reviewer_queue.jpg / 11_reviewer_decision.jpg | Manual-review queue and decision panel |
| 12_admin_overview.jpg | Administrator dashboard with filters, trend, monitoring |
| 13_analytics_model_evidence.jpg | Analytics and Python model evidence |
| 14_policy_editor.jpg | Warranty policy and rule-severity editor, decision settings |
| 15_models_teachable_machine.jpg | Model status, Teachable Machine installer, sample cards |
| 16_access_control.jpg | Access control: people, roles, permission matrix, blocked attempts |
| 17_audit_trail.jpg | Audit trail |
| 18_mobile_dashboard.jpg / 19_mobile_claim.jpg | Phone layout |
| 20_gtm_training.png | Teachable Machine run 1 (v2 cards): 700 images per class, epochs 50 / batch 16 / lr 0.001, model trained |
| 22_gtm_evaluation.png | Run 1 evaluated in the app: 54.2% test accuracy (below target → card redesigned) |
| 23_gtm_v3_training.png | Teachable Machine run 2 (v3 colour-tile cards), model trained |
| 24_gtm_v3_preview_test.png | Run 2 preview on an unseen card: dates conflict + late reporting + excluded cause → Invalid Claim 99% |
| 25_gtm_v3_evaluation.png | Run 2 evaluated in the app: 93.8% test accuracy, 97.3% validation, 92.9% agreement with Python |
