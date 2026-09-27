# Google Teachable Machine — evidence (SRS deliverable 5)

> **Status: trained and installed.** Model `gtm-514702678b8c`, trained in the browser on the 2,100 v3
> training cards: **93.8% test accuracy** (macro F1 93.8%), 97.3% validation accuracy, agreeing with the
> Python model on 92.9% of test claims. A first model trained on the v2 cards scored 54.2% and was
> replaced (see *Card design iterations*). The earlier `gtm_classifier.joblib` / `weights.bin` /
> `metadata.json` files were a scikit-learn stand-in, not a Teachable Machine export, and were removed.

## Claim Summary Cards

| Item | Value |
|---|---|
| Renderer | `src/core/card_v2.py` (same code for training cards and live claims) |
| Size | 600 × 600 px (square, so Teachable Machine's centre crop keeps every element) |
| Fonts | DejaVu Sans shipped in `static/fonts/` (identical rendering on Windows / Linux / servers) |
| Content (v3) | Claim facts compared with the category's policy limits, as a fixed 3×3 grid of large tiles: coverage (within / grace / ended), reporting time (in time / late), damage cause (covered / excluded, with diagnostic confidence), receipt, supporting evidence (3 of 3 … 0 of 3), serial (matches / differs / unverified), dates (consistent / conflict), invoice (unique / reused), repairs (count / repeat / unauthorised). Each state has its own colour **and** glyph (✓ ! ✕ ↔); a colour band shows the category. Limits come from `policies/*.json`, the same source as the rule engine |
| Never on a card | Python prediction, any confidence score, final decision, class label |
| Training images | 2 variations per training claim (colour jitter, date format, ±1.5° rotation, blur, JPEG quality) → **2,100** images: 700 per class in `data/summary_cards/train/{valid,invalid,manual_review}/` |
| Validation / test | one canonical card per claim (`<claim_id>_v0.jpg`) in `data/summary_cards/{val,test}/` — **never uploaded for training** |
| Mapping | `data/claim_id_to_card_mapping.csv` (claim ID, split, class, variation, filename, path) |

Samples: Admin › Models shows one training card per class; any card can be opened from a claim page.

## Card design iterations (measured)

| Card | How measured | Validation | Test | Notes |
|---|---|---|---|---|
| v2 (grey bars, small tiles and pips) | Real Teachable Machine export `gtm-ec95b4aa49b5`, evaluated in the app | 52.9% | **54.2%** (macro F1 45.1%) | agreed with the Python model on 55.1% of test claims; below the SRS 85% target |
| v2 | `notebooks/tm_replica_check.py`, 2 seeds | 63.1–74.7% | 58.2–65.8% | the replica reproduces the failure, so the card, not the training run, was the problem |
| v3 (policy-relative colour tiles) | `notebooks/tm_replica_check.py`, 3 seeds | 95.1–97.3% | 92.9–94.2% (mean 93.6%) | pre-check before the browser run |
| **v3** | **Real Teachable Machine export `gtm-514702678b8c`**, evaluated in the app | **97.3%** | **93.8%** (macro F1 93.8%) | agrees with the Python model on 92.9% of test claims; ceiling ≈ 96% (4% deliberate label noise) |

Why v2 failed: Teachable Machine does not fine-tune the image network; it trains a small head on frozen
ImageNet (MobileNet) features. Thin grey bars and 20-pixel pips at 224×224 produce almost identical
features for all three classes. v3 makes every fact a large region whose colour and glyph change with the
fact's value relative to the policy limit, which those frozen features separate easily. The card still
shows facts only — no class, decision, rule outcome or model confidence.

The replica estimate (92.9–94.2%) matched the real v3 export (93.8%), so the offline check is a useful
way to test a card design before spending a browser training run.

## Training procedure

1. Admin › Models › *Download training cards* (zip with three class folders), or use the folders above.
2. teachablemachine.withgoogle.com → *Image Project* → *Standard image model*.
3. Rename the classes exactly **Valid Claim**, **Invalid Claim**, **Manual Review**; upload 700 images each.
4. *Advanced*: start with epochs 50, batch size 16, learning rate 0.001. Train.
5. *Export Model* → *Tensorflow Lite* → *Floating point* → download; unzip.
6. Admin › Models › upload `model_unquant.tflite` and `labels.txt` (checked: TFLite header, exactly the three
   labels, the model loads and runs; the previous model is archived under `model/teachable_machine/versions/`).
7. *Run evaluation* (or `python notebooks/evaluate_gtm.py`) and `python reports/generate_comparison_report.py`.

## Confusion matrix (test, 225 cards; rows = actual, columns = predicted)

| | Valid Claim | Invalid Claim | Manual Review |
|---|---|---|---|
| **Valid Claim** | 73 | 1 | 1 |
| **Invalid Claim** | 5 | 68 | 2 |
| **Manual Review** | 4 | 1 | 70 |

Most errors predict *Valid Claim* for claims labelled Invalid or Manual Review (9 of 14). 12 of the 14
errors are claims whose label was deliberately flipped, where the model's answer is the policy's answer (see
*Training observations*); in the application no claim is marked *Likely Valid* unless the rule engine and
the Python model agree as well.

## Training observations

* **Run 1 (v2 cards).** Training finished normally (epochs 50, batch 16, learning rate 0.001), but on our
  225 test cards the model reached only 54.2% and agreed with the Python model on 55.1% of claims: a card
  that looks clear to a person is not necessarily clear to frozen ImageNet features at 224 × 224 pixels.
* **Diagnosis.** An offline replica of the trainer (`notebooks/tm_replica_check.py`) reproduced the failure
  (58–66%), so the problem was the input representation, not the training run or its settings.
* **Run 2 (v3 cards).** Same settings. Validation 97.3%, test 93.8%; the preview in Teachable Machine gave
  *Invalid Claim 99%* for an unseen card with a date conflict, late reporting and an excluded cause
  (`screenshots/24_gtm_v3_preview_test.png`).
* **Where it still errs.** 12 of its 14 test errors are claims whose label was deliberately flipped to
  simulate reviewer disagreement (the test split has 12 such claims): on every one of them the image model
  gave the answer the warranty policy gives. Its only 2 real errors are a grace-period claim called
  *Invalid* (should be reviewed) and a late-reporting claim called *Manual Review* (should be invalid).
  Measured against the policy instead of the noisy labels it agrees on 223 of 225 test claims (99.1%).
  The misclassified cards are listed with their scenario in `reports/gtm_misclassified_test.csv`.
* **Browser behaviour.** With 2,100 images Chrome showed "Page unresponsive" during "Preparing training
  data"; choosing *Wait* and keeping the tab in front let training finish (about 20–25 minutes).
* **Deployment.** TensorFlow 2.20 no longer ships `tf.lite.Interpreter`; the app uses `ai-edge-litert`
  (Windows and Linux). Models are loaded from bytes so a new export can replace a running one on Windows.

## Runtime

`src/core/gtm_classifier_v2.py` — TensorFlow Lite interpreter (`ai-edge-litert`), preprocessing identical to
the Teachable Machine export sample (ImageOps.fit to the model input, scaled to [-1, 1]; quantized exports
are supported). The model version is `gtm-<SHA-256 prefix of the .tflite file>` and is stored with every
prediction. If the file is missing or broken the prediction is marked *unavailable* and the claim goes to
manual review — there is no fallback model.

## Training record

| Item | Value |
|---|---|
| Model version | `gtm-514702678b8c` (`model/teachable_machine/model_unquant.tflite`, float, input 224×224) |
| Classes | Valid Claim · Invalid Claim · Manual Review (`labels.txt`) |
| Images per class | 700 / 700 / 700 v3 training cards (two variations of each of the 1,050 training claims) |
| Training configuration | Standard image model; epochs 50, batch size 16, learning rate 0.001 |
| Validation accuracy (225 cards) | 97.3% |
| Test accuracy (225 cards) · macro F1 | **93.8% · 93.8%** |
| Agreement with the Python model (test) | 92.9% of claims |
| Macro precision / recall (test) | 94.0% / 93.8% |
| Per class (test): precision / recall | Valid 89.0% / 97.3% · Invalid 97.1% / 90.7% · Manual Review 95.9% / 93.3% |
| Full evaluation | `model/teachable_machine/evaluation.json`; comparison with the Python model in `reports/model_comparison_report.md` (application decision accuracy 92.0%) |
| Incorrectly classified samples | `reports/gtm_misclassified_test.csv` (written by the evaluation) |
| Retraining details | Run 1 on v2 cards → 54.2% test (archived as `gtm-ec95b4aa49b5`). Cause found with `notebooks/tm_replica_check.py`; card redesigned (v3); run 2 on v3 cards → 93.8% |
| Screenshots | Run 1: `screenshots/20_gtm_training.png`, `22_gtm_evaluation.png`. Run 2: `23_gtm_v3_training.png`, `24_gtm_v3_preview_test.png`, `25_gtm_v3_evaluation.png` |
