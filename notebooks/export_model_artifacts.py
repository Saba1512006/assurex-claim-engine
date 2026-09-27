"""Export the Python model's preprocessing, label encoder, processed datasets and sample predictions.

The trained model is ONE artefact (model/python_model/claim_classifier_v2.joblib) so the encoder and the
classifier can never drift apart; that file is what the application loads. The SRS also asks for the label
encoder and preprocessing files and the preprocessed data on their own, so this script pulls them out of
the saved model — it never refits anything — and writes:

  model/python_model/preprocessing_pipeline.joblib   ColumnTransformer: numeric + binary passthrough,
                                                      one-hot for category and damage type (fixed vocabulary)
  model/python_model/label_encoder.joblib             sklearn LabelEncoder for the three classes
  model/python_model/feature_schema.json              input columns, types, vocabularies, output columns
  model/python_model/sample_test_predictions.csv      all 225 test claims: actual, predicted, 3 probabilities
  data/processed/{train,val,test}_features.csv        model-ready matrices (claim_id + encoded features + label)
  data/claim_scenarios.json                           scenario definitions, class and frequency
  data/labels.csv                                     claim_id -> split, class, scenario, card files

Run:  python notebooks/export_model_artifacts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.core.features import BINARY, CATEGORICAL, MODEL_FEATURES, NUMERIC  # noqa: E402
from src.core.vocab import CATEGORIES, CLASSES, DAMAGE_TYPES  # noqa: E402

MODEL_DIR = ROOT / "model" / "python_model"
DATA = ROOT / "data"

# Order of precedence in dataset_generator/generator_v2.py::adjudicate (first match wins).
SCENARIOS = {
    "expired": ("Invalid Claim", "Claim filed after the warranty and its grace period ended."),
    "unauthorized_repair": ("Invalid Claim", "The product was previously repaired by an unauthorised center."),
    "excluded_damage": ("Invalid Claim", "Damage cause is excluded by the category policy and the technician's "
                                         "diagnosis confirms it (confidence at or above the policy threshold)."),
    "serial_mismatch": ("Invalid Claim", "Serial number differs from the receipt and the serial photo."),
    "contradiction": ("Manual Review", "Dates contradict each other (fault reported before purchase)."),
    "late_reporting": ("Invalid Claim", "Fault reported later than the category's reporting period."),
    "grace_boundary": ("Manual Review", "Warranty ended but the claim is inside the grace period."),
    "possible_duplicate": ("Manual Review", "The invoice was already used on another claim."),
    "missing_documents": ("Manual Review", "Receipt missing, or two or more supporting documents missing."),
    "serial_unverifiable": ("Manual Review", "Serial mismatch that cannot be verified (evidence incomplete)."),
    "ambiguous_cause": ("Manual Review", "Excluded cause without a confirming diagnosis, or unknown cause "
                                         "with low diagnostic confidence."),
    "repeat_repairs": ("Manual Review", "Previous repairs at or above the policy's repeat-repair threshold."),
    "covered_defect": ("Valid Claim", "Covered fault, inside the warranty, complete evidence, consistent data."),
}


def main() -> None:
    bundle = joblib.load(MODEL_DIR / "claim_classifier_v2.joblib")
    model, features = bundle["pipeline"], bundle["features"]
    assert list(features) == MODEL_FEATURES, "model features differ from src/core/features.py"

    # The calibrated model holds one fitted copy of the pipeline per CV fold. Their preprocessing is identical
    # (passthrough + one-hot with a fixed vocabulary); verify that instead of assuming it.
    preps = [c.estimator.named_steps["prep"] for c in model.calibrated_classifiers_]
    splits = {n: pd.read_csv(DATA / "splits" / f"{n}.csv") for n in ("train", "val", "test")}
    ref = preps[0].transform(splits["test"][features])
    assert all(np.allclose(p.transform(splits["test"][features]), ref) for p in preps[1:]), "fold preprocessors differ"
    prep = preps[0]
    joblib.dump(prep, MODEL_DIR / "preprocessing_pipeline.joblib")

    encoder = LabelEncoder().fit(list(model.classes_))
    assert list(encoder.classes_) == list(model.classes_)
    joblib.dump(encoder, MODEL_DIR / "label_encoder.joblib")

    out_cols = [str(c).split("__", 1)[-1] for c in prep.get_feature_names_out()]
    schema = {
        "model_file": "claim_classifier_v2.joblib", "model_version": bundle["version"],
        "sklearn_version": bundle["sklearn_version"],
        "inputs": {"numeric": NUMERIC, "binary": BINARY, "categorical": CATEGORICAL},
        "vocabularies": {"product_category": list(CATEGORIES), "damage_type": list(DAMAGE_TYPES)},
        "missing_values": "documents absent -> 0, no repairs -> 0, no diagnosis -> 0.5 (src/core/features.py); "
                          "unknown category or damage type is rejected, never encoded as zeros",
        "encoding": "one-hot with the fixed vocabularies above (handle_unknown='error')",
        "scaling": "none for tree models (the selected HistGradientBoosting); StandardScaler only for the "
                   "logistic-regression candidate",
        "output_columns": out_cols, "classes": list(encoder.classes_),
    }
    (MODEL_DIR / "feature_schema.json").write_text(json.dumps(schema, indent=2))

    (DATA / "processed").mkdir(exist_ok=True)
    for name, df in splits.items():
        X = pd.DataFrame(prep.transform(df[features]), columns=out_cols)
        X.insert(0, "claim_id", df["claim_id"].values)
        X["claim_class"] = df["claim_class"].values
        X["label_id"] = encoder.transform(df["claim_class"])
        X.to_csv(DATA / "processed" / f"{name}_features.csv", index=False)

    test = splits["test"]
    proba = model.predict_proba(test[features])
    pred = model.classes_[proba.argmax(1)]
    col = {c: i for i, c in enumerate(model.classes_)}
    pd.DataFrame({
        "claim_id": test["claim_id"], "actual_class": test["claim_class"], "predicted_class": pred,
        "p_valid": proba[:, col["Valid Claim"]].round(4), "p_invalid": proba[:, col["Invalid Claim"]].round(4),
        "p_manual_review": proba[:, col["Manual Review"]].round(4), "correct": pred == test["claim_class"].values,
    }).to_csv(MODEL_DIR / "sample_test_predictions.csv", index=False)

    raw = pd.read_csv(DATA / "raw" / "common_warranty_claims_1500.csv")
    base = raw["scenario"].str.replace("+noise", "", regex=False)
    counts, noisy = base.value_counts().to_dict(), raw[raw["scenario"].str.endswith("+noise")]["scenario"]
    (DATA / "claim_scenarios.json").write_text(json.dumps({
        "precedence": "rules are applied in this order; the first that matches decides the label",
        "label_noise": f"{len(noisy)} claims ({len(noisy) / len(raw):.1%}) carry a deliberately flipped label "
                       "(scenario suffix '+noise') to simulate reviewer disagreement",
        "scenarios": [{"scenario": k, "class": c, "definition": d, "claims": int(counts.get(k, 0))}
                      for k, (c, d) in SCENARIOS.items()],
    }, indent=2))

    m = pd.read_csv(DATA / "claim_id_to_card_mapping.csv")
    cards = m.groupby("claim_id")["relative_path"].apply(lambda s: ";".join(sorted(s))).rename("card_files")
    labels = raw[["claim_id", "claim_class", "scenario"]].merge(
        m.drop_duplicates("claim_id")[["claim_id", "split"]], on="claim_id").merge(cards, on="claim_id")
    labels[["claim_id", "split", "claim_class", "scenario", "card_files"]].sort_values("claim_id").to_csv(
        DATA / "labels.csv", index=False)
    acc = (pred == test["claim_class"].values).mean()
    print(f"exported preprocessing, label encoder, schema, processed splits, labels; test accuracy {acc:.3f}")


if __name__ == "__main__":
    main()
