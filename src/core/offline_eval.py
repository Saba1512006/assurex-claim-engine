"""Offline evaluation on the held-out splits (SRS deliverables 4-6).

Runs exactly the production components - Python model, canonical Claim Summary
Card, Teachable Machine model, consistency status, rule engine, decision
table - on the val/test CSV records and their card images, and returns one row
per claim with every column the model-comparison report requires.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from src.core import decision_table
from src.core.gtm_classifier_v2 import GTMUnavailable, get_gtm_classifier
from src.core.pipeline import compare
from src.core.python_classifier import get_python_classifier
from src.core.vocab import CLASSES, DOCUMENT_LABELS
from src.rules import policy_engine
from src.rules.policy_store import get_policy

ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS = ROOT / "data" / "splits"
CARDS = ROOT / "data" / "summary_cards"
DECISION_TO_CLASS = {"Likely Valid": "Valid Claim", "Likely Invalid": "Invalid Claim",
                     "Manual Review Required": "Manual Review"}
FLAG_DOC = {"has_receipt": "receipt", "has_warranty_card": "warranty_card", "has_serial_photo": "serial_photo",
            "has_damage_photo": "damage_photo"}


def evaluate_split(split: str, use_gtm: bool = True) -> pd.DataFrame:
    df = pd.read_csv(SPLITS / f"{split}.csv")
    py = get_python_classifier()
    gtm = None
    if use_gtm:
        try:
            gtm = get_gtm_classifier()
        except GTMUnavailable:
            gtm = None
    policy = decision_table.load_policy()
    rows = []
    for rec in df.to_dict("records"):
        facts = dict(rec, previous_replacement_details="")
        p = py.predict(facts)
        card_name = f"{rec['claim_id']}_v0.jpg"
        g = gtm.predict(CARDS / split / card_name) if gtm else None
        cmp = compare(p, g)
        rules = policy_engine.evaluate(facts)
        mandatory = set(get_policy(rec["product_category"])["mandatory_documents"])
        absent = [d for f, d in FLAG_DOC.items() if not int(rec[f])]
        missing = [DOCUMENT_LABELS[d] for d in absent]
        contradictions = (["Fault/claim dates conflict with the purchase date"] if rec["claim_date_conflict_flag"] else []) + \
                         (["Serial number does not match the evidence"] if not rec["serial_number_match"] else [])
        duplicates = ["Invoice number reused"] if rec["duplicate_invoice_flag"] else []
        d = decision_table.decide({
            "hard_fail_count": len(rules.hard_fails), "contradiction_count": len(contradictions),
            "duplicate_count": len(duplicates), "missing_mandatory_count": len(mandatory & set(absent)),
            "manual_trigger_count": len(rules.manual_triggers), "warning_count": len(rules.warnings),
            "consistency": cmp["status"], "python_class": p["predicted_class"],
            "gtm_class": g["predicted_class"] if g else "Unavailable"}, policy)
        note = ""
        if g and not cmp["match"]:
            note = (f"Python says {p['predicted_class']} ({p['top_confidence']:.2f}); Teachable Machine says "
                    f"{g['predicted_class']} ({g['top_confidence']:.2f}). Rules: "
                    + (", ".join(r.rule_id for r in rules.hard_fails + rules.manual_triggers) or "none fired") + ".")
        rows.append({
            "claim_id": rec["claim_id"], "actual_class": rec["claim_class"], "scenario": rec.get("scenario", ""),
            "python_predicted": p["predicted_class"],
            **{f"python_{c.split()[0].lower()}": p["confidence_scores"][c] for c in CLASSES},
            "card_filename": card_name,
            "gtm_predicted": g["predicted_class"] if g else "unavailable",
            **{f"gtm_{c.split()[0].lower()}": (g["confidence_scores"][c] if g else None) for c in CLASSES},
            "class_match": cmp["match"], "confidence_difference": cmp["diff"], "consistency_status": cmp["status"],
            "rule_result": rules.overall,
            "rules_fired": "; ".join(f"{r.rule_id} ({r.severity})" for r in rules.results if r.fired),
            "missing_documents": "; ".join(missing), "contradictions": "; ".join(contradictions),
            "duplicate_indicators": "; ".join(duplicates), "final_decision": d["decision"],
            "decision_rule": d["rule_id"], "disagreement_explanation": note,
        })
    return pd.DataFrame(rows)


def metrics(rows: pd.DataFrame, column: str) -> dict:
    y, p = rows["actual_class"], rows[column]
    labels = list(CLASSES)
    return {"accuracy": round(float(accuracy_score(y, p)), 4),
            "f1_macro": round(float(f1_score(y, p, average="macro", labels=labels)), 4),
            "labels": labels, "confusion_matrix": confusion_matrix(y, p, labels=labels).tolist(),
            "per_class": classification_report(y, p, labels=labels, output_dict=True, zero_division=0)}


def summarise(rows: pd.DataFrame) -> dict:
    out = {"claims": len(rows), "python": metrics(rows, "python_predicted"),
           "status_counts": rows["consistency_status"].value_counts().to_dict(),
           "decision_counts": rows["final_decision"].value_counts().to_dict()}
    mapped = rows.assign(final_class=rows["final_decision"].map(DECISION_TO_CLASS))
    out["application"] = metrics(mapped, "final_class")
    if (rows["gtm_predicted"] != "unavailable").all():
        out["gtm"] = metrics(rows, "gtm_predicted")
        out["agreement_rate"] = round(float(rows["class_match"].mean()), 4)
    return out


def evaluate_gtm_and_save() -> dict:
    """Admin > Models 'Evaluate' and notebooks/evaluate_gtm.py: GTM metrics on val + test, saved to disk."""
    out = {}
    for split in ("val", "test"):
        rows = evaluate_split(split)
        s = summarise(rows)
        if "gtm" not in s:
            raise GTMUnavailable("Teachable Machine model is not installed.")
        out[split] = {"gtm_accuracy": s["gtm"]["accuracy"], "gtm_f1_macro": s["gtm"]["f1_macro"],
                      "confusion_matrix": s["gtm"]["confusion_matrix"], "per_class": s["gtm"]["per_class"],
                      "agreement_rate": s["agreement_rate"], "status_counts": s["status_counts"],
                      "model_version": get_gtm_classifier().version}
        rows.to_csv(ROOT / "reports" / f"model_comparison_{split}.csv", index=False)
        rows[rows.actual_class != rows.gtm_predicted].to_csv(ROOT / "reports" / f"gtm_misclassified_{split}.csv",
                                                             index=False)
    (ROOT / "model" / "teachable_machine" / "evaluation.json").write_text(json.dumps(out, indent=2, default=str))
    return out
