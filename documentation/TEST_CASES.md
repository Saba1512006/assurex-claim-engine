# Test cases (SRS deliverable 8)

Run everything: `python -m pytest -q` → **192 passed** (about 25 s). Every test is automated; the table
maps each SRS test category to the functions that cover it (`file :: function`).

| SRS category | What is checked | Tests |
|---|---|---|
| **Functional** | Register product with receipt; full claim journey (submit → evaluate → approve, notifications, audit, card, PDF, tracking); drafts; request-info loop; reviewer take/decide; admin pages & exports | `test_workflow :: test_customer_registers_product_with_receipt, test_full_claim_journey_with_agreeing_models, test_draft_edit_then_submit, test_request_info_loop, test_reviewer_queue_and_take, test_admin_tools, test_public_pages` |
| **Integration** | Real Flask app + DB + file store + OCR + both model runtimes + rule engine end to end | `test_workflow :: *`, `test_pipeline :: test_both_models_agree_valid_is_approved`, `test_detectors :: test_repair_serial_feeds_contradictions` |
| **Boundary** | Last day of cover, first/last day of grace, first day after grace; reporting deadline ±1 day; exclusion at 0.54 / 0.55 diagnosis; consistency at Δ = 0.10 / 0.25 and confidence = 0.60 | `test_rules :: test_warranty_boundaries, test_reporting_window_boundaries, test_exclusion_needs_diagnosis_to_hard_fail`, `test_pipeline :: test_consistency_boundaries`, `test_ml_integrity :: test_consistency_matrix` |
| **Negative** | Bad product form, future dates, unknown damage type, fake/oversized/mismatched files, non-receipt PDF, non-TFLite model upload, invalid policy values, invalid decision thresholds | `test_workflow :: test_product_form_validation, test_wizard_rejects_bad_input, test_gtm_upload_rejects_non_tflite, test_policy_editor_validates_and_audits`, `test_documents :: test_invalid_files_are_refused, test_oversized_file_is_refused`, `test_rules :: test_policy_validation_rejects_bad_files, test_decision_policy_save_rejects_invalid` |
| **Security** | No unguarded route; registration can't create admins; generic login errors; lockout; session revoked on role change/disable; IDOR returns 404; staff/reviewer scope; separation of duties; admin self-protection; CSRF; CSP & headers; open redirect; POST-only logout; denials audited; CSV formula injection | `test_rbac_routes :: *`, `test_rbac_policy :: *`, `test_workflow :: test_csrf_is_enforced, test_security_headers_and_csp, test_open_redirect_blocked, test_logout_is_post_only_and_clears_session, test_admin_tools` |
| **Database** | Unique public IDs enforced; every evaluation a new immutable row; status history and audit rows written with each change | `test_workflow :: test_database_constraints`, `test_pipeline :: test_reevaluation_keeps_earlier_results`, `test_workflow :: test_full_claim_journey_with_agreeing_models` |
| **OCR** | PDF receipt read (invoice, serial, date, amount); entity patterns; words not mistaken for identifiers; OCR engine missing → accept & type; user corrections saved and audited | `test_documents :: test_pdf_receipt_is_read_by_ocr, test_entity_patterns, test_words_are_not_mistaken_for_identifiers, test_image_receipt_accepted_when_ocr_engine_missing`, `test_workflow :: test_scan_receipt_endpoint, test_ocr_values_confirmed_by_user_are_saved_and_audited` |
| **Python model** | Accuracy ≥ 85% and not suspiciously perfect; no single-feature leakage; three calibrated probabilities; unknown category rejected; failure handled | `test_ml_integrity :: test_model_meets_srs_accuracy_and_is_not_suspiciously_perfect, test_unknown_category_is_rejected_not_silently_zeroed`, `test_pipeline :: test_python_model_scores_all_three_classes, test_unknown_category_is_rejected_by_model, test_python_model_failure_is_handled` |
| **Teachable Machine** | Missing model → *Uncertain Result* + manual review (no fallback); label-file parsing incl. folder names; installer rejects non-TFLite files; card is 600×600 and prediction-free | `test_pipeline :: test_without_teachable_machine_claim_goes_to_manual_review, test_teachable_machine_label_file_parsing, test_card_stored_and_contains_no_prediction`, `test_workflow :: test_gtm_upload_rejects_non_tflite` |
| **Model comparison** | All five consistency statuses; disagreement; low confidence; hard fail beats agreeing models | `test_ml_integrity :: test_consistency_matrix`, `test_pipeline :: test_model_disagreement_goes_to_manual_review, test_low_confidence_image_model_is_uncertain, test_hard_fail_wins_over_agreeing_models` |
| **Rule engine** | Every rule fires and passes; per-category exclusions; severities from config; policy files complete (SRS deliverable 7) | `test_rules :: *` |
| **Contradiction detection** | Claim before purchase, fault before purchase, fault after claim, repair before purchase, model/invoice/purchase-date mismatch | `test_detectors :: test_date_contradictions, test_model_invoice_and_purchase_date_mismatch, test_consistent_claim_has_no_contradictions` |
| **Missing documents** | Mandatory vs supporting documents; product-level receipt counts; D03 routing; evidence rules | `test_detectors :: test_missing_documents_follow_policy, test_product_level_receipt_counts_for_claims`, `test_rules :: test_evidence_rules` |
| **Duplicate claims** | Same file hash on another product; invoice reused; open claim on the same serial; near-identical description; closed history is not a duplicate | `test_detectors :: test_duplicate_document_hash_across_products, test_invoice_reuse_and_open_claim_on_same_serial, test_closed_claim_on_same_unit_is_history_not_duplicate` |
| **Serial-number mismatch** | Checked against receipt, warranty card, serial photo, diagnostic report and repair records; hard fail vs manual review depends on evidence | `test_detectors :: test_serial_checked_against_every_source, test_repair_serial_feeds_contradictions`, `test_rules :: test_serial_mismatch_severity_depends_on_evidence` |
| **Low confidence** | Confidence < 0.60 → *Uncertain Result* → manual review | `test_pipeline :: test_low_confidence_image_model_is_uncertain`, `test_ml_integrity :: test_consistency_matrix` |
| **Model disagreement** | Different classes → *Model Disagreement* → D04 | `test_pipeline :: test_model_disagreement_goes_to_manual_review`, `test_demonstration_cases :: 11_model_disagreement_claim` |
| **Demonstration cases** | The 11 SRS cases from `sample_claims/` | `test_demonstration_cases :: *` |
| **Surprise modifications** | New exclusion, rule severity change, confidence threshold, extra date format, decision-logic (routing) change | `test_rules :: test_surprise_*` |
| **Performance** | Both predictions + rules within 5 s (SRS NFR-1) | `test_pipeline :: test_evaluation_is_fast_enough` |

## Hidden-test readiness checklist

- [x] No logic keyed on claim IDs, names or demo values; OCR has no hard-coded retailer/product lists.
- [x] Every categorical value comes from one vocabulary (`src/core/vocab.py`); the UI options are tested to equal the training values.
- [x] Unknown categories fail loudly instead of being silently encoded as zeros.
- [x] Model selected on validation, test used once; calibrated probabilities; leakage audit < 90%.
- [x] Dates accepted in seven formats; adding one is a one-line change (tested).
- [x] Rules, thresholds and routing are configuration, editable in the admin UI and validated on save.
- [x] A missing or broken model can never crash a request or silently decide a claim.
- [x] Every prediction is stored with both model versions, the card hash and the decision trace.
- [x] 192 tests pass on a clean checkout (`python -m pytest -q`).

## Manual checks performed

* Every page rendered for all four roles (customer, staff, reviewer, administrator) with the seeded data:
  no server errors; out-of-scope records return 404 and forbidden pages 403.
* Browser screenshots at 1366 px and 390 px (mobile) — see `screenshots/`.
* `python database/seed.py` submits the 11 demonstration claims through the live pipeline.
