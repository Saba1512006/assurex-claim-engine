# Development log (SRS §1.8 item 3)

Entries record work completed, problems encountered, model failures, changes made and tests performed.
Earlier days are in the Git history; team members should add their own entries below.

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

**Open items**
- Republish the blog; redeploy and re-seed the live site; complete the team rows in `AI_USAGE.md`.
