"""Model card data (public /model-card and the landing page).

Every number is read from artefacts written by the training and evaluation scripts:
  model/python_model/model_card_v2.json, model/teachable_machine/evaluation.json,
  reports/model_comparison_test.csv (both models on the 225 test claims), data/splits/test.csv,
  data/dataset_statistics.json, data/claim_scenarios.json, reports/gtm_misclassified_test.csv.
Missing files produce None / empty sections ("Not evaluated yet" in the UI), never a placeholder number.
Results are cached per file modification time.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.core.vocab import CATEGORIES, CLASSES

ROOT = Path(__file__).resolve().parent.parent.parent
FILES = {
    "python": ROOT / "model" / "python_model" / "model_card_v2.json",
    "gtm": ROOT / "model" / "teachable_machine" / "evaluation.json",
    "comparison": ROOT / "reports" / "model_comparison_test.csv",
    "test": ROOT / "data" / "splits" / "test.csv",
    "stats": ROOT / "data" / "dataset_statistics.json",
    "scenarios": ROOT / "data" / "claim_scenarios.json",
    "gtm_errors": ROOT / "reports" / "gtm_misclassified_test.csv",
}
_cache: dict = {}


def _json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _matrix(cm, labels) -> dict | None:
    """Confusion matrix re-ordered to Valid, Invalid, Manual Review with cell weights for shading."""
    if not cm or not labels:
        return None
    idx = [labels.index(c) for c in CLASSES]
    grid = [[int(cm[i][j]) for j in idx] for i in idx]
    peak = max(max(r) for r in grid) or 1
    return {"labels": list(CLASSES), "rows": [[(v, round(v / peak, 3)) for v in r] for r in grid]}


def _reliability(rows: list[dict], prefix: str, bins: int = 5) -> dict | None:
    """Top-class confidence vs observed accuracy, equal-width bins from 0.2 to 1 (three classes)."""
    pts = []
    for r in rows:
        try:
            scores = {c: float(r[f"{prefix}_{k}"]) for c, k in zip(CLASSES, ("valid", "invalid", "manual"))}
        except (KeyError, ValueError):
            continue
        top = max(scores, key=scores.get)
        pts.append((scores[top], top == r["actual_class"]))
    if not pts:
        return None
    lo, width = 1 / 3, (1 - 1 / 3) / bins
    out, ece = [], 0.0
    for b in range(bins):
        a, z = lo + b * width, lo + (b + 1) * width
        inside = [p for p in pts if a <= p[0] < z or (b == bins - 1 and p[0] == 1.0)]
        if inside:
            conf = sum(p[0] for p in inside) / len(inside)
            acc = sum(p[1] for p in inside) / len(inside)
            ece += len(inside) / len(pts) * abs(acc - conf)
            out.append({"from": round(a, 2), "to": round(z, 2), "n": len(inside), "confidence": round(conf, 3), "accuracy": round(acc, 3)})
    return {"bins": out, "ece": round(ece, 4), "n": len(pts)}


def _by_category(rows: list[dict], test_rows: list[dict]) -> list[dict]:
    cat = {r["claim_id"]: r["product_category"] for r in test_rows}
    out = []
    for c in CATEGORIES:
        sub = [r for r in rows if cat.get(r["claim_id"]) == c]
        if sub:
            out.append({"category": c, "n": len(sub),
                        "python": round(sum(r["python_predicted"] == r["actual_class"] for r in sub) / len(sub), 3),
                        "gtm": round(sum(r["gtm_predicted"] == r["actual_class"] for r in sub) / len(sub), 3)})
    return out


def _noise(rows: list[dict], scenarios: dict) -> dict | None:
    """Accuracy against the noisy labels vs against the policy's own answer (scenario class)."""
    policy_class = {s["scenario"]: s["class"] for s in scenarios.get("scenarios", [])}
    if not rows or not policy_class:
        return None
    noisy = [r for r in rows if r["scenario"].endswith("+noise")]

    def truth(r):
        return policy_class.get(r["scenario"].replace("+noise", ""), r["actual_class"])

    res = {"n": len(rows), "noisy": len(noisy)}
    for m in ("python", "gtm"):
        res[m] = {"vs_labels": round(sum(r[f"{m}_predicted"] == r["actual_class"] for r in rows) / len(rows), 3),
                  "vs_policy": round(sum(r[f"{m}_predicted"] == truth(r) for r in rows) / len(rows), 3),
                  "policy_on_noisy": sum(r[f"{m}_predicted"] == truth(r) for r in noisy)}
    return res


def build() -> dict:
    key = tuple(p.stat().st_mtime if p.exists() else 0 for p in FILES.values())
    if _cache.get("key") == key:
        return _cache["data"]
    py, gtm = _json(FILES["python"]), _json(FILES["gtm"])
    rows, test_rows = _rows(FILES["comparison"]), _rows(FILES["test"])
    stats, scenarios = _json(FILES["stats"]), _json(FILES["scenarios"])
    pt, gt = py.get("test", {}), gtm.get("test", {})
    per_class = lambda pc: [{"class": c, **{k: pc[c][k] for k in ("precision", "recall", "f1-score")}} for c in CLASSES if c in pc]  # noqa: E731
    data = {
        "dataset": {
            "total": stats.get("total"), "splits": {k: v.get("rows") for k, v in stats.get("splits", {}).items()},
            "by_class": stats.get("by_class", {}), "noise_rate": stats.get("label_noise_rate"),
            "scenarios": scenarios.get("scenarios", []), "seed": stats.get("seed"),
        },
        "python": None if not pt else {
            "algorithm": pt.get("selected_model"), "version": py.get("version"), "sklearn": py.get("sklearn_version"),
            "accuracy": pt.get("accuracy"), "f1": pt.get("f1_macro"), "precision": pt.get("precision_macro"),
            "recall": pt.get("recall_macro"), "auc": pt.get("roc_auc_ovr_macro"), "ece": pt.get("ece"),
            "log_loss": pt.get("log_loss"), "matrix": _matrix(pt.get("confusion_matrix"), pt.get("labels")),
            "per_class": per_class(pt.get("per_class", {})), "reliability": _reliability(rows, "python"),
            "benchmark": py.get("benchmark_validation", {}), "leakage": sorted(py.get("leakage_audit", {}).items(), key=lambda kv: -kv[1]),
            "importance": py.get("permutation_importance_val", {}),
        },
        "gtm": None if not gt else {
            "version": gt.get("model_version"), "accuracy": gt.get("gtm_accuracy"), "f1": gt.get("gtm_f1_macro"),
            "val_accuracy": gtm.get("val", {}).get("gtm_accuracy"),
            "precision": gt.get("per_class", {}).get("macro avg", {}).get("precision"),
            "recall": gt.get("per_class", {}).get("macro avg", {}).get("recall"),
            "agreement": gt.get("agreement_rate"), "matrix": _matrix(gt.get("confusion_matrix"), list(CLASSES)),
            "per_class": per_class(gt.get("per_class", {})), "reliability": _reliability(rows, "gtm"),
        },
        "by_category": _by_category(rows, test_rows),
        "noise": _noise(rows, scenarios),
        "gtm_errors": _rows(FILES["gtm_errors"])[:6],
    }
    _cache.update(key=key, data=data)
    return data


def headline() -> dict:
    """The four numbers on the landing page (None when not evaluated yet)."""
    d = build()
    return {"python": d["python"], "gtm": d["gtm"]}
