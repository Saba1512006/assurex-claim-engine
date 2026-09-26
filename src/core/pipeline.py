"""End-to-end claim evaluation (SRS Steps 6-12, xviii-xxxv).

    evidence -> contradictions + duplicates -> features -> warranty rules
             -> Python model  (structured record)
             -> Claim Summary Card -> Teachable Machine model (image)
             -> consistency status -> config-driven decision table -> routing

Each run writes a NEW ModelEvaluation + RuleValidationLog row; earlier rows are
never modified, so updating a model cannot alter recorded results (SRS xlviii).
Model failures never crash the request: the failing model is marked
unavailable, the consistency status becomes "Uncertain Result" and the decision
table sends the claim to manual review.
"""
from __future__ import annotations

import hashlib
import io
import json
import time
from dataclasses import dataclass
from pathlib import Path

from src.core import decision_table, features as feature_builder
from src.core.card_v2 import render_card
from src.core.consistency import consistency_status, thresholds
from src.core.gtm_classifier_v2 import GTMUnavailable, get_gtm_classifier
from src.core.python_classifier import ModelUnavailable, get_python_classifier
from src.rules import contradiction_detector, duplicate_detector, policy_engine

UNAVAILABLE = "Unavailable"


@dataclass
class Outcome:
    evaluation: object          # ModelEvaluation
    rule_log: object            # RuleValidationLog
    decision: dict
    next_status: str


def risk_level(decision: str, contradictions: int, duplicates: int, hard_fails: int) -> str:
    if decision == "Likely Invalid" or contradictions or duplicates or hard_fails:
        return "High"
    return "Low" if decision == "Likely Valid" else "Medium"


def _run_python(features: dict) -> tuple[dict | None, str | None]:
    try:
        return get_python_classifier().predict(features), None
    except ModelUnavailable as exc:
        return None, str(exc)


def _run_gtm(card) -> tuple[dict | None, str | None]:
    try:
        return get_gtm_classifier().predict(card), None
    except GTMUnavailable as exc:
        return None, str(exc)


def compare(py: dict | None, gtm: dict | None) -> dict:
    """SRS xxii-xxiv: class match, |top-confidence difference|, consistency status."""
    t = thresholds()
    if py is None or gtm is None:
        missing = "Python model" if py is None else "Teachable Machine model"
        return {"status": "Uncertain Result", "diff": None, "match": None, "thresholds": t,
                "explanation": f"{missing} unavailable, so the two predictions cannot be compared."}
    status, diff = consistency_status(py["predicted_class"], py["top_confidence"],
                                      gtm["predicted_class"], gtm["top_confidence"], t)
    match = py["predicted_class"] == gtm["predicted_class"]
    if status == "Uncertain Result":
        text = (f"Lowest top-class confidence {min(py['top_confidence'], gtm['top_confidence']):.2f} "
                f"is below the {t['min_confidence']:.2f} minimum.")
    elif status == "Model Disagreement":
        text = f"Python predicts {py['predicted_class']}, Teachable Machine predicts {gtm['predicted_class']}."
    else:
        text = f"Both predict {py['predicted_class']}; confidence difference {diff:.2f}."
    return {"status": status, "diff": diff, "match": match, "thresholds": t, "explanation": text}


def evaluate_claim(claim, *, upload_dir: Path, actor=None) -> Outcome:
    """Run the full pipeline for a stored claim and persist the result (caller commits)."""
    from database.db import db
    from src.models.entities import ModelEvaluation, RuleValidationLog
    from src.services.audit import audit

    started = time.perf_counter()
    product = claim.product
    documents = list(claim.documents) + [d for d in product.documents if d.claim_id is None]

    contradictions = contradiction_detector.detect(
        purchase_date=product.purchase_date, fault_date=claim.fault_occurrence_date,
        submission_date=claim.claim_submission_date, registered_serial=product.serial_number,
        registered_model=product.model_number, registered_invoice=product.invoice_number,
        documents=documents, repairs=list(product.repair_records))
    duplicates = duplicate_detector.check(claim)
    facts = feature_builder.build(claim, contradictions=contradictions, duplicates=duplicates)
    rules = policy_engine.evaluate(facts)
    missing = feature_builder.missing_mandatory(claim)

    py, py_err = _run_python(facts)
    card = render_card(facts, variation=0)             # canonical card: no prediction or decision on it
    buf = io.BytesIO()
    card.save(buf, "PNG")
    card_bytes = buf.getvalue()
    gtm, gtm_err = _run_gtm(card)
    comparison = compare(py, gtm)

    decision_facts = {
        "hard_fail_count": len(rules.hard_fails),
        "contradiction_count": len(contradictions["findings"]),
        "duplicate_count": len(duplicates["indicators"]),
        "missing_mandatory_count": len(missing),
        "manual_trigger_count": len(rules.manual_triggers),
        "warning_count": len(rules.warnings),
        "consistency": comparison["status"],
        "python_class": py["predicted_class"] if py else UNAVAILABLE,
        "gtm_class": gtm["predicted_class"] if gtm else UNAVAILABLE,
    }
    policy = decision_table.load_policy()
    decision = decision_table.decide(decision_facts, policy)
    decision["facts"] = decision_facts

    evaluation = ModelEvaluation(
        claim=claim, features_json=json.dumps(facts, default=str),
        python_available=py is not None, python_model_version=py and py["model_version"],
        python_predicted_class=py and py["predicted_class"],
        python_conf_valid=py and py["confidence_scores"]["Valid Claim"],
        python_conf_invalid=py and py["confidence_scores"]["Invalid Claim"],
        python_conf_manual=py and py["confidence_scores"]["Manual Review"],
        gtm_available=gtm is not None, gtm_model_version=gtm and gtm["model_version"],
        gtm_predicted_class=gtm and gtm["predicted_class"],
        gtm_conf_valid=gtm and gtm["confidence_scores"]["Valid Claim"],
        gtm_conf_invalid=gtm and gtm["confidence_scores"]["Invalid Claim"],
        gtm_conf_manual=gtm and gtm["confidence_scores"]["Manual Review"],
        model_errors_json=json.dumps({k: v for k, v in (("python", py_err), ("gtm", gtm_err)) if v}) or None,
        is_class_match=comparison["match"], top_confidence_difference=comparison["diff"],
        model_consistency_status=comparison["status"],
        consistency_thresholds_json=json.dumps({**comparison["thresholds"], "explanation": comparison["explanation"]}),
        decision=decision["decision"], decision_rule_id=decision["rule_id"],
        decision_trace_json=json.dumps(decision["trace"]), decision_policy_version=decision["policy_version"],
        summary_card_sha256=hashlib.sha256(card_bytes).hexdigest(),
    )
    db.session.add(evaluation)
    db.session.flush()                                   # evaluation_id is now final
    cards_dir = upload_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    rel = f"cards/{evaluation.evaluation_id}.png"
    (upload_dir / rel).write_bytes(card_bytes)
    evaluation.summary_card_image_path = rel

    rule_log = RuleValidationLog(
        claim=claim, evaluation_id=evaluation.id, policy_name=rules.policy_name,
        rules_json=json.dumps(rules.to_dict()["results"]),
        contradictions_json=json.dumps(contradictions["findings"]),
        duplicate_flags_json=json.dumps(duplicates["indicators"]),
        missing_documents_json=json.dumps(missing), overall_rule_status=rules.overall)
    db.session.add(rule_log)

    claim.final_decision = decision["decision"]
    claim.decision_reason = decision["reason"]
    claim.decision_rule_id = decision["rule_id"]
    claim.decision_policy_version = decision["policy_version"]
    claim.contradiction_flag = bool(contradictions["findings"])
    claim.is_duplicate_flag = bool(duplicates["indicators"])
    claim.missing_document_flag = bool(missing)
    claim.risk_level = risk_level(decision["decision"], len(contradictions["findings"]),
                                  len(duplicates["indicators"]), len(rules.hard_fails))
    evaluation.latency_ms = int((time.perf_counter() - started) * 1000)

    audit("MODEL_PREDICTION", "Claim", claim.claim_id, user=actor,
          python=py and {k: py[k] for k in ("predicted_class", "top_confidence", "model_version")},
          gtm=gtm and {k: gtm[k] for k in ("predicted_class", "top_confidence", "model_version")},
          consistency=comparison["status"], diff=comparison["diff"], latency_ms=evaluation.latency_ms)
    for name, err in (("Python", py_err), ("Teachable Machine", gtm_err)):
        if err:
            audit("MODEL_UNAVAILABLE", "Claim", claim.claim_id, user=actor, model=name, error=err)
    audit("FINAL_DECISION", "Claim", claim.claim_id, user=actor, decision=decision["decision"],
          rule=decision["rule_id"], policy_version=decision["policy_version"])
    return Outcome(evaluation, rule_log, decision, policy["routing"][decision["decision"]])
