"""Evaluate the exported Teachable Machine model on the held-out validation and test cards.

    python notebooks/evaluate_gtm.py

Writes model/teachable_machine/evaluation.json (accuracy, macro F1, confusion matrix,
per-class report, agreement with the Python model, consistency-status counts) and
reports/model_comparison_{val,test}.csv + gtm_misclassified_{val,test}.csv.
Same code path as Admin > Models > "Run evaluation".
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.core.offline_eval import evaluate_gtm_and_save  # noqa: E402

if __name__ == "__main__":
    result = evaluate_gtm_and_save()
    print(json.dumps({s: {k: result[s][k] for k in ("gtm_accuracy", "gtm_f1_macro", "agreement_rate", "status_counts")}
                      for s in result}, indent=2))
