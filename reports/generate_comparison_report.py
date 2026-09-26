"""Model prediction & confidence comparison report (SRS deliverable 6).

    python reports/generate_comparison_report.py [--split test] [--limit 225]

For every unseen claim: the structured record goes to the Python model and its
canonical Claim Summary Card (data/summary_cards/<split>/<id>_v0.jpg) goes to
the Teachable Machine model; the rule engine and decision table then produce the
application decision. Writes reports/model_comparison_report.csv and .md.
If the Teachable Machine export is not installed, its columns say "unavailable"
and the summary states it - nothing is estimated or filled in.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.core.gtm_classifier_v2 import find_model_file  # noqa: E402
from src.core.offline_eval import evaluate_split, summarise  # noqa: E402

COLUMNS = {  # csv column -> report heading (SRS page 28-29 order)
    "claim_id": "Claim ID", "actual_class": "Actual class", "python_predicted": "Python predicted class",
    "python_valid": "Python conf. Valid", "python_invalid": "Python conf. Invalid", "python_manual": "Python conf. Manual",
    "card_filename": "Card filename", "gtm_predicted": "GTM predicted class", "gtm_valid": "GTM conf. Valid",
    "gtm_invalid": "GTM conf. Invalid", "gtm_manual": "GTM conf. Manual", "class_match": "Classes match",
    "confidence_difference": "Top-confidence difference", "consistency_status": "Consistency status",
    "rule_result": "Warranty-rule result", "missing_documents": "Missing documents",
    "contradictions": "Contradictions", "duplicate_indicators": "Duplicate indicators",
    "final_decision": "Final application decision", "disagreement_explanation": "Explanation of disagreement",
}


def fmt(v):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v) if v != "" else "—"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["val", "test"])
    ap.add_argument("--limit", type=int, default=225, help="claims to include (SRS minimum 30)")
    args = ap.parse_args()
    rows = evaluate_split(args.split).head(max(30, args.limit))
    summary = summarise(rows)
    out = ROOT / "reports"
    rows[list(COLUMNS)].rename(columns=COLUMNS).to_csv(out / "model_comparison_report.csv", index=False)

    gtm_on = find_model_file() is not None
    lines = [f"# Model prediction & confidence comparison — {args.split} split", "",
             f"{len(rows)} unseen claims. Python model on the structured record; Google Teachable Machine on the "
             "claim's canonical Claim Summary Card; rules and decision table as in production.", ""]
    if not gtm_on:
        lines += ["> **Teachable Machine model not installed.** Its columns read “unavailable”, every comparison is "
                  "*Uncertain Result*, and the application sends those claims to manual review. Install the export "
                  "(Admin › Models) and re-run this script to fill the columns.", ""]
    py = summary["python"]
    lines += ["## Overall comparison summary", "",
              "| Metric | Value |", "|---|---|",
              f"| Python model accuracy | {py['accuracy']:.1%} |", f"| Python model macro F1 | {py['f1_macro']:.1%} |"]
    if "gtm" in summary:
        lines += [f"| Teachable Machine accuracy | {summary['gtm']['accuracy']:.1%} |",
                  f"| Teachable Machine macro F1 | {summary['gtm']['f1_macro']:.1%} |",
                  f"| Predicted-class agreement | {summary['agreement_rate']:.1%} |"]
    lines += [f"| Application decision accuracy (decision → class) | {summary['application']['accuracy']:.1%} |"]
    lines += ["", "**Consistency statuses:** " + ", ".join(f"{k} {v}" for k, v in summary["status_counts"].items()),
              "", "**Final decisions:** " + ", ".join(f"{k} {v}" for k, v in summary["decision_counts"].items()), ""]
    dis = rows[rows["disagreement_explanation"] != ""]
    lines += ["## Major disagreements", ""]
    lines += [f"- **{r.claim_id}** (actual {r.actual_class}): {r.disagreement_explanation}" for r in dis.itertuples()] \
        or ["- None" if gtm_on else "- Not measurable until the Teachable Machine model is installed."]
    lines += ["", "## Per-claim results", "", "| " + " | ".join(COLUMNS.values()) + " |",
              "|" + "---|" * len(COLUMNS)]
    for r in rows.to_dict("records"):
        lines.append("| " + " | ".join(fmt(r[c]).replace("|", "/") for c in COLUMNS) + " |")
    (out / "model_comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k in ("claims", "status_counts", "decision_counts")}, indent=2))
    print("python accuracy", py["accuracy"], "| written reports/model_comparison_report.{csv,md}")


if __name__ == "__main__":
    main()
