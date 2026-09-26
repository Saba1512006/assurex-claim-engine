"""End-to-end evaluation: both models, consistency statuses, decisions, versioning, failure handling."""
from datetime import date

import pytest

from src.core import pipeline
from src.core.consistency import consistency_status
from src.core.gtm_classifier_v2 import LABEL_ALIASES, parse_labels
from src.core.python_classifier import ModelUnavailable, get_python_classifier
from src.models.entities import ModelEvaluation
from src.services import claim_service
from tests.conftest import attach_docs, make_claim, make_product, make_user


def good_claim(app, **kw):
    u = make_user(kw.pop("email", "g@x.io"))
    c = make_claim(make_product(u), claim_submission_date=date.today(), **kw)
    attach_docs(c)
    return c


def run(app, c):
    return pipeline.evaluate_claim(c, upload_dir=app.config["UPLOAD_DIR"])


def test_python_model_scores_all_three_classes(app):
    out = run(app, good_claim(app)).evaluation
    scores = out.python_scores()
    assert set(scores) == {"Valid Claim", "Invalid Claim", "Manual Review"}
    assert abs(sum(scores.values()) - 1) < 0.01
    assert out.python_model_version.startswith("v2.0.0+")


def test_without_teachable_machine_claim_goes_to_manual_review(app):
    out = run(app, good_claim(app))
    assert not out.evaluation.gtm_available
    assert out.evaluation.model_consistency_status == "Uncertain Result"
    assert out.decision["decision"] == "Manual Review Required" and out.decision["rule_id"] == "D04"
    assert "gtm" in out.evaluation.model_errors


def test_both_models_agree_valid_is_approved(app, gtm):
    gtm.mirror_python()
    c = good_claim(app)
    out = claim_service.submit(c, c.claimant)
    assert out.evaluation.python_predicted_class == "Valid Claim"
    assert out.evaluation.model_consistency_status == "Strong Match"
    assert out.decision["decision"] == "Likely Valid" and c.status == "Approved"
    assert [h.new_status for h in c.status_history] == ["Draft", "Submitted", "Under Evaluation", "Approved"]


def test_model_disagreement_goes_to_manual_review(app, gtm):
    gtm.set("Invalid Claim", 0.9)
    out = run(app, good_claim(app))
    assert out.evaluation.model_consistency_status == "Model Disagreement"
    assert out.evaluation.is_class_match is False
    assert out.decision["decision"] == "Manual Review Required"


def test_hard_fail_wins_over_agreeing_models(app, gtm):
    gtm.set("Valid Claim", 0.95)
    c = good_claim(app, damage="Water Ingress", conf=0.9)
    out = run(app, c)
    assert out.decision["rule_id"] == "D01" and out.decision["decision"] == "Likely Invalid"
    assert c.risk_level == "High"


def test_low_confidence_image_model_is_uncertain(app, gtm):
    gtm.set("Valid Claim", 0.45)
    out = run(app, good_claim(app))
    assert out.evaluation.model_consistency_status == "Uncertain Result"


@pytest.mark.parametrize("py,pc,gm,gc,expected", [
    ("Valid Claim", 0.90, "Valid Claim", 0.80, "Strong Match"),        # diff 0.10 == strong boundary
    ("Valid Claim", 0.90, "Valid Claim", 0.79, "Acceptable Match"),
    ("Valid Claim", 0.90, "Valid Claim", 0.65, "Acceptable Match"),    # diff 0.25 == acceptable boundary
    ("Valid Claim", 0.91, "Valid Claim", 0.65, "Weak Match"),
    ("Invalid Claim", 0.59, "Invalid Claim", 0.99, "Uncertain Result"),
])
def test_consistency_boundaries(py, pc, gm, gc, expected):
    assert consistency_status(py, pc, gm, gc)[0] == expected


def test_card_stored_and_contains_no_prediction(app):
    out = run(app, good_claim(app)).evaluation
    path = app.config["UPLOAD_DIR"] / out.summary_card_image_path
    assert path.exists() and len(out.summary_card_sha256) == 64
    from PIL import Image
    assert Image.open(path).size == (600, 600)
    assert "predicted_class" not in out.features and "claim_class" not in out.features


def test_reevaluation_keeps_earlier_results(app, gtm):
    c = good_claim(app)
    gtm.set("Valid Claim", 0.9)
    first = run(app, c).evaluation
    gtm.set("Manual Review", 0.8)                     # e.g. a retrained image model
    second = claim_service.reevaluate(c, c.claimant).evaluation
    assert first.id != second.id and ModelEvaluation.query.filter_by(claim_id=c.id).count() == 2
    assert first.gtm_predicted_class == "Valid Claim" and second.gtm_predicted_class == "Manual Review"
    assert c.model_evaluation.id == second.id


def test_python_model_failure_is_handled(app, monkeypatch):
    def broken(_):
        return None, "Python model file not found (test)"
    monkeypatch.setattr(pipeline, "_run_python", broken)
    out = run(app, good_claim(app))
    assert not out.evaluation.python_available and out.decision["decision"] == "Manual Review Required"
    assert out.evaluation.model_errors["python"].startswith("Python model file")


def test_unknown_category_is_rejected_by_model():
    clf = get_python_classifier()
    import pandas as pd
    rec = pd.read_csv("data/splits/test.csv").iloc[0].to_dict()
    rec["damage_type"] = "Hardware Defect"
    with pytest.raises(ModelUnavailable):
        clf.predict(rec)


def test_teachable_machine_label_file_parsing():
    assert parse_labels("0 Valid Claim\n1 Invalid Claim\n2 Manual Review\n") == ["Valid Claim", "Invalid Claim", "Manual Review"]
    assert parse_labels("0 valid\n1 invalid\n2 manual_review") == ["Valid Claim", "Invalid Claim", "Manual Review"]
    assert set(LABEL_ALIASES.values()) == {"Valid Claim", "Invalid Claim", "Manual Review"}


def test_evaluation_is_fast_enough(app):
    """SRS NFR-1: both predictions within five seconds."""
    out = run(app, good_claim(app)).evaluation
    assert out.latency_ms < 5000
