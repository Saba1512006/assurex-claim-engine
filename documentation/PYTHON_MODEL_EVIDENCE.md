# Python classification model — evidence (SRS deliverable 4)

Source of every number below: `model/python_model/model_card_v2.json`, written by
`notebooks/train_python_v2.py` (seed 42, deterministic — re-running gives the same artefact hash
`514e2fb68286…`). The live values are also shown in the app under Admin › Analytics.

## Data

| Item | Value |
|---|---|
| Dataset | `data/raw/common_warranty_claims_1500.csv` — 1,500 claims, 500 per class |
| Split (stratified, before any card was rendered) | train 1,050 · validation 225 · test 225, 350/75/75 per class |
| Isolation | a claim ID belongs to exactly one split (asserted in the generator and by `tests/test_ml_integrity.py`) |
| Label noise | 4% of labels flipped on purpose (reviewer disagreement) → realistic ceiling ≈ 96% |

## Features (20) and pre-processing

| Group | Features | Handling |
|---|---|---|
| Numeric (8) | purchase_price, warranty_duration_months, product_age_days, days_to_expiry, reporting_delay_days, diagnostic_confidence, previous_repairs_count, missing_document_count | Standardised (StandardScaler) for the linear model; raw for tree models |
| Binary (10) | is_extended_warranty, has_receipt, has_warranty_card, has_damage_photo, has_serial_photo, has_repair_report, serial_number_match, unauthorized_repair_flag, duplicate_invoice_flag, claim_date_conflict_flag | Passed through as 0/1 |
| Categorical (2) | product_category (3 values), damage_type (7 values) | One-hot with the **fixed** vocabulary from `src/core/vocab.py`; an unseen value raises an error instead of being silently zeroed |

Never features: claim_id, scenario, claim_class, fault_description, identifiers (asserted in the trainer).

**Missing values.** In the web app, absent documents become 0, no repairs 0, and an unassessed diagnosis
takes the neutral prior 0.5 (the mean of the non-defect training distribution). Categories outside the
vocabulary are rejected with a message. **Derived fields**: product age, days to expiry, remaining
warranty, reporting delay, missing-document count, conflict / mismatch / duplicate flags —
`src/core/features.py` builds them with exactly the training column names.

**Encoder / pre-processing files.** The `ColumnTransformer` (scaler + one-hot encoder with its category
lists = the "label encoder") is saved *inside* the single pipeline artefact
`model/python_model/claim_classifier_v2.joblib`, so pre-processing and model can never drift apart.

## Leakage audit

A depth-3 decision tree trained on **one feature at a time** (validation accuracy; chance = 33%):

| Feature | Accuracy alone |
|---|---|
| days_to_expiry | 52.9% |
| product_age_days | 49.8% |
| missing_document_count | 45.3% |
| has_receipt | 42.7% |
| unauthorized_repair_flag | 40.9% |

The trainer refuses to continue if any single feature exceeds 90% (v1's `damage_type` was a renamed label
and scored 100%).

## Algorithms tested (5-fold stratified CV on train, then the validation split)

| Algorithm | Hyper-parameters | CV macro-F1 | Val accuracy | Val precision | Val recall | Val macro-F1 |
|---|---|---|---|---|---|---|
| Logistic regression | C=1.0, max_iter=2000, scaled inputs | 0.739 ± 0.026 | 72.9% | 73.3% | 72.9% | 72.6% |
| Random forest | 400 trees, min_samples_leaf=2, class_weight=balanced | 0.922 ± 0.018 | 94.2% | 94.2% | 94.2% | 94.2% |
| **HistGradientBoosting** (selected) | max_iter=300, learning_rate=0.06, max_leaf_nodes=15, l2=1.0 | 0.913 ± 0.008 | **94.7%** | 94.7% | 94.7% | **94.7%** |

Selection uses the **validation** macro-F1 only; the test split is touched once, at the end.
The selected pipeline is then wrapped in `CalibratedClassifierCV(method="sigmoid", cv=5)` so its
probabilities are usable as confidence scores (the consistency statuses depend on them).

## Test results (225 unseen claims)

| Metric | Value |
|---|---|
| Accuracy | **89.3%** (SRS NFR-4 target 85%) |
| Macro precision / recall / F1 | 89.5% / 89.3% / 89.2% |
| ROC-AUC (one-vs-rest, macro) | 0.948 |
| Log-loss | 0.406 |
| Expected calibration error | 0.082 |
| Mean top-class confidence | 82.6% |

Confusion matrix (rows actual, columns predicted):

| | Invalid | Manual Review | Valid |
|---|---|---|---|
| **Invalid Claim** | 61 | 8 | 6 |
| **Manual Review** | 2 | 69 | 4 |
| **Valid Claim** | 3 | 1 | 71 |

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Invalid Claim | 92.4% | 81.3% | 86.5% | 75 |
| Manual Review | 88.5% | 92.0% | 90.2% | 75 |
| Valid Claim | 87.7% | 94.7% | 91.0% | 75 |

The weakest cell is Invalid → Manual Review (8). Checking the 14 missed Invalid claims by scenario:
5 are *late reporting* (a rare scenario — 23 of 1,500 claims — so the model has seen few examples),
4 carry deliberately flipped labels (noise), 3 are *excluded damage* with a diagnosis near the 0.55
threshold, and 2 are expiry/grace boundary cases. All of these are claims the rule engine decides
deterministically (LATE_REPORTING, EXCLUDED_DAMAGE, WARRANTY_EXPIRED are hard-fail rules), which is why the
application never relies on the model alone.

## Feature importance (permutation, validation split, drop in macro-F1)

days_to_expiry 0.279 · damage_type 0.161 · unauthorized_repair_flag 0.098 · diagnostic_confidence 0.081 ·
has_receipt 0.076 · serial_number_match 0.057 · missing_document_count 0.056 · reporting_delay_days 0.054

These match the warranty policy: expiry, excluded causes, unauthorised repairs and proof of purchase drive
the outcome.

## Model version and sample predictions

* Version string stored with every prediction: `v2.0.0+<first 12 hex of the file's SHA-256>`.
* scikit-learn 1.9.1 (pinned in `requirements.txt` so the pickle loads identically everywhere).
* 30 sample test predictions with all three probabilities: `model_card_v2.json → test.sample_predictions`;
  all 225 in `reports/model_comparison_report.csv`.
