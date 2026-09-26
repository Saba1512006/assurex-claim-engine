# Google Teachable Machine — evidence (SRS deliverable 5)

> **Status: training pending.** Teachable Machine runs in the browser at teachablemachine.withgoogle.com,
> so the model cannot be produced by a script in this repository. Everything around it is ready: the
> training cards, the runtime, the installer, the evaluation and the comparison report. The sections
> marked *to record* are filled in by the team after training. The earlier `gtm_classifier.joblib` /
> `weights.bin` / `metadata.json` files were a scikit-learn stand-in, not a Teachable Machine export,
> and have been removed.

## Claim Summary Cards

| Item | Value |
|---|---|
| Renderer | `src/core/card_v2.py` (same code for training cards and live claims) |
| Size | 600 × 600 px (square, so Teachable Machine's centre crop keeps every element) |
| Fonts | DejaVu Sans shipped in `static/fonts/` (identical rendering on Windows / Linux / servers) |
| Content | Claim facts only: category pips, warranty life bar with expiry marker, reporting delay bar with 30-day marker, diagnostic confidence bar, five evidence tiles (filled = present, hatched = missing), four integrity signals, previous-repair squares, damage-cause pips, fault and dates |
| Never on a card | Python prediction, any confidence score, final decision, class label |
| Training images | 2 variations per training claim (tint, date format, ±1.5° rotation, blur, JPEG quality) → **2,100** images: 700 per class in `data/summary_cards/train/{valid,invalid,manual_review}/` |
| Validation / test | one canonical card per claim (`<claim_id>_v0.jpg`) in `data/summary_cards/{val,test}/` — **never uploaded for training** |
| Mapping | `data/claim_id_to_card_mapping.csv` (claim ID, split, class, variation, filename, path) |

Samples: Admin › Models shows one training card per class; any card can be opened from a claim page.

## Training procedure

1. Admin › Models › *Download training cards* (zip with three class folders), or use the folders above.
2. teachablemachine.withgoogle.com → *Image Project* → *Standard image model*.
3. Rename the classes exactly **Valid Claim**, **Invalid Claim**, **Manual Review**; upload 700 images each.
4. *Advanced*: start with epochs 50, batch size 16, learning rate 0.001. Train.
5. *Export Model* → *Tensorflow Lite* → *Floating point* → download; unzip.
6. Admin › Models › upload `model_unquant.tflite` and `labels.txt` (checked: TFLite header, exactly the three
   labels, the model loads and runs; the previous model is archived under `model/teachable_machine/versions/`).
7. *Run evaluation* (or `python notebooks/evaluate_gtm.py`) and `python reports/generate_comparison_report.py`.

## Runtime

`src/core/gtm_classifier_v2.py` — TensorFlow Lite interpreter (`ai-edge-litert`), preprocessing identical to
the Teachable Machine export sample (ImageOps.fit to the model input, scaled to [-1, 1]; quantized exports
are supported). The model version is `gtm-<SHA-256 prefix of the .tflite file>` and is stored with every
prediction. If the file is missing or broken the prediction is marked *unavailable* and the claim goes to
manual review — there is no fallback model.

## To record after training

| Item | Value |
|---|---|
| Project link / screenshots of the three classes | *to record* |
| Training configuration (epochs, batch, learning rate) | *to record* |
| Images per class | 700 / 700 / 700 |
| Validation accuracy · test accuracy · macro F1 | *from `model/teachable_machine/evaluation.json`* |
| Confusion matrix | *from `evaluation.json`* |
| Incorrectly classified samples | `reports/gtm_misclassified_test.csv` (written by the evaluation) |
| Retraining details | *to record* |
| Model version | shown on Admin › Models |
| Test screenshots | *to record* |
