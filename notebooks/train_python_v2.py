"""Python classifier training v2.

Fixes vs v1: model selected on VALIDATION (v1 selected on test = test-set
leakage), single sklearn Pipeline artefact (no preprocessor/model drift),
probability calibration (v1 emitted 1.000 everywhere, making the 5 consistency
statuses meaningless), leakage audit, ECE and ROC-AUC reporting.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import hashlib

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, log_loss, precision_score, recall_score, roc_auc_score)
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.core.features import BINARY, CATEGORICAL, NUMERIC  # noqa: E402
from src.core.vocab import CATEGORIES, DAMAGE_TYPES  # noqa: E402

SEED = 42
VERSION = "v2.0.0"
NUM, BIN, CAT = NUMERIC, BINARY, CATEGORICAL          # same lists the web app builds (src/core/features.py)
FEATURES = NUM + BIN + CAT
FORBIDDEN = {"claim_id", "scenario", "claim_class", "fault_description"}   # never features
TARGET = "claim_class"
assert not FORBIDDEN & set(FEATURES)


def preprocessor(scale: bool) -> ColumnTransformer:
    return ColumnTransformer([
        ("num", StandardScaler() if scale else "passthrough", NUM),
        ("bin", "passthrough", BIN),
        # fixed categories = vocab; unknown value raises instead of silently zeroing
        ("cat", OneHotEncoder(categories=[list(CATEGORIES), list(DAMAGE_TYPES)], handle_unknown="error"), CAT),
    ])


def candidates() -> dict:
    return {
        "logistic_regression": Pipeline([("prep", preprocessor(True)),
                                         ("clf", LogisticRegression(max_iter=2000, C=1.0))]),
        "random_forest": Pipeline([("prep", preprocessor(False)),
                                   ("clf", RandomForestClassifier(n_estimators=400, min_samples_leaf=2,
                                                                  class_weight="balanced", random_state=SEED, n_jobs=-1))]),
        "hist_gradient_boosting": Pipeline([("prep", preprocessor(False)),
                                            ("clf", HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
                                                                                   max_leaf_nodes=15, l2_regularization=1.0,
                                                                                   random_state=SEED))]),
    }


def expected_calibration_error(y_true, proba, classes, bins: int = 10) -> float:
    conf = proba.max(axis=1)
    correct = (np.asarray(classes)[proba.argmax(axis=1)] == np.asarray(y_true)).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def leakage_audit(train: pd.DataFrame, val: pd.DataFrame) -> dict:
    """Accuracy of a depth-3 tree on each single feature. >0.90 => suspicious proxy."""
    out = {}
    for f in FEATURES:
        Xtr = pd.get_dummies(train[[f]].astype(str)) if f in CAT else train[[f]]
        Xva = (pd.get_dummies(val[[f]].astype(str)).reindex(columns=Xtr.columns, fill_value=0)
               if f in CAT else val[[f]])
        tree = DecisionTreeClassifier(max_depth=3, random_state=SEED).fit(Xtr, train[TARGET])
        out[f] = round(float(accuracy_score(val[TARGET], tree.predict(Xva))), 3)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def main() -> None:
    d = ROOT / "data" / "splits"
    train, val, test = (pd.read_csv(d / f"{n}.csv") for n in ("train", "val", "test"))
    audit = leakage_audit(train, val)
    worst = next(iter(audit.items()))
    print("leakage audit (top 5):", list(audit.items())[:5])
    assert worst[1] < 0.90, f"feature {worst[0]} alone predicts the label ({worst[1]}) -> leakage"

    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    report, fitted = {}, {}
    for name, pipe in candidates().items():
        cv_f1 = cross_val_score(pipe, train[FEATURES], train[TARGET], cv=cv, scoring="f1_macro")
        pipe.fit(train[FEATURES], train[TARGET])
        fitted[name] = pipe
        vp = pipe.predict(val[FEATURES])
        report[name] = {"cv_f1_macro_mean": round(cv_f1.mean(), 4), "cv_f1_macro_std": round(cv_f1.std(), 4),
                        "val_accuracy": round(accuracy_score(val[TARGET], vp), 4),
                        "val_precision_macro": round(precision_score(val[TARGET], vp, average="macro"), 4),
                        "val_recall_macro": round(recall_score(val[TARGET], vp, average="macro"), 4),
                        "val_f1_macro": round(f1_score(val[TARGET], vp, average="macro"), 4),
                        "val_confusion_matrix": confusion_matrix(val[TARGET], vp, labels=sorted(val[TARGET].unique())).tolist()}
        print(name, report[name])

    best = max(report, key=lambda k: report[k]["val_f1_macro"])          # selection on VALIDATION only
    imp = permutation_importance(fitted[best], val[FEATURES], val[TARGET], scoring="f1_macro",
                                 n_repeats=10, random_state=SEED)
    importance = dict(sorted(((f, round(float(m), 4)) for f, m in zip(FEATURES, imp.importances_mean)),
                             key=lambda kv: -kv[1]))
    print("permutation importance (top 5):", list(importance.items())[:5])
    model = CalibratedClassifierCV(candidates()[best], method="sigmoid", cv=5)
    model.fit(train[FEATURES], train[TARGET])

    proba = model.predict_proba(test[FEATURES])
    pred = model.classes_[proba.argmax(axis=1)]
    classes = list(model.classes_)
    test_metrics = {
        "selected_model": best,
        "accuracy": round(accuracy_score(test[TARGET], pred), 4),
        "precision_macro": round(precision_score(test[TARGET], pred, average="macro"), 4),
        "recall_macro": round(recall_score(test[TARGET], pred, average="macro"), 4),
        "f1_macro": round(f1_score(test[TARGET], pred, average="macro"), 4),
        "roc_auc_ovr_macro": round(roc_auc_score(test[TARGET], proba, multi_class="ovr", labels=classes), 4),
        "log_loss": round(log_loss(test[TARGET], proba, labels=classes), 4),
        "ece": round(expected_calibration_error(test[TARGET], proba, classes), 4),
        "labels": classes,
        "confusion_matrix": confusion_matrix(test[TARGET], pred, labels=classes).tolist(),
        "per_class": classification_report(test[TARGET], pred, output_dict=True, zero_division=0),
        "mean_top_confidence": round(float(proba.max(axis=1).mean()), 4),
    }
    sample = test.head(30)
    sp = model.predict_proba(sample[FEATURES])
    test_metrics["sample_predictions"] = [
        {"claim_id": cid, "actual": act, "predicted": classes[int(row.argmax())],
         **{f"p_{c}": round(float(v), 4) for c, v in zip(classes, row)}}
        for cid, act, row in zip(sample["claim_id"], sample[TARGET], sp)]
    print(json.dumps({k: v for k, v in test_metrics.items() if k not in ("per_class", "sample_predictions")}, indent=2))
    assert test_metrics["accuracy"] >= 0.85, "SRS NFR-4 not met"

    out = ROOT / "model" / "python_model"
    out.mkdir(parents=True, exist_ok=True)
    import sklearn
    artefact = out / "claim_classifier_v2.joblib"
    joblib.dump({"pipeline": model, "features": FEATURES, "version": VERSION,
                 "sklearn_version": sklearn.__version__}, artefact)
    sha = hashlib.sha256(artefact.read_bytes()).hexdigest()
    (out / "model_card_v2.json").write_text(json.dumps(
        {"version": VERSION, "artefact_sha256": sha, "sklearn_version": sklearn.__version__, "seed": SEED,
         "features": FEATURES, "leakage_audit": audit, "permutation_importance_val": importance, "selection": "highest validation macro-F1",
         "benchmark_validation": report, "test": test_metrics}, indent=2, default=str))
    print("saved", artefact.name, sha[:12])


if __name__ == "__main__":
    main()
