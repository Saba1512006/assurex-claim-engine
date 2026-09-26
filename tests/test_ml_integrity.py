"""Guards that make hidden-claim evaluation safe. Run: pytest -q"""
import json
import re
from pathlib import Path

import joblib
import pandas as pd
import pytest

from src.core.consistency import consistency_status
from src.core.decision_table import decide, load_policy
from src.core.vocab import CATEGORIES, DAMAGE_TYPES, DATE_FORMATS, parse_date

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ROOT / "data" / "splits"


@pytest.fixture(scope="module")
def splits():
    return {n: pd.read_csv(SPLITS / f"{n}.csv") for n in ("train", "val", "test")}


# ---------- data integrity ----------
def test_split_sizes_and_balance(splits):
    assert [len(splits[n]) for n in ("train", "val", "test")] == [1050, 225, 225]
    for df in splits.values():
        counts = df["claim_class"].value_counts()
        assert counts.max() - counts.min() <= 1


def test_no_claim_in_two_splits(splits):
    ids = [set(df["claim_id"]) for df in splits.values()]
    assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])


def test_card_mapping_respects_splits():
    m = pd.read_csv(ROOT / "data" / "claim_id_to_card_mapping.csv")
    assert m.groupby("claim_id")["split"].nunique().max() == 1
    assert (m[m.split == "train"].groupby("claim_id").size() >= 2).all()   # >=2 variations per train claim
    assert len(m[m.split == "train"]) >= 2100


def test_claim_id_does_not_encode_class(splits):
    df = pd.concat(splits.values())
    num = df["claim_id"].str.extract(r"(\d+)")[0].astype(int)
    means = num.groupby(df["claim_class"]).mean()
    assert means.max() - means.min() < 0.1 * num.max()


# ---------- train/serve parity ----------
def test_ui_options_exist_in_training_vocabulary(app, client):
    """The damage-type options the customer can pick (rendered HTML) must all be training values."""
    from tests.conftest import login, make_product, make_user
    u = make_user("ui@x.io")
    make_product(u)
    login(client, "ui@x.io")
    html = client.get("/claims/new").get_data(as_text=True)
    select = re.search(r'<select[^>]*name="damage_type".*?</select>', html, re.S).group(0)
    ui_values = set(re.findall(r'value="([^"]+)"', select)) - {""}
    assert ui_values == set(DAMAGE_TYPES), f"UI/training vocabulary drift: {ui_values ^ set(DAMAGE_TYPES)}"


def test_training_categories_are_canonical(splits):
    df = pd.concat(splits.values())
    assert set(df["product_category"]) <= set(CATEGORIES)
    assert set(df["damage_type"]) <= set(DAMAGE_TYPES)


def test_unknown_category_is_rejected_not_silently_zeroed():
    bundle = joblib.load(ROOT / "model" / "python_model" / "claim_classifier_v2.joblib")
    row = pd.read_csv(SPLITS / "test.csv").head(1).copy()
    row["damage_type"] = "Hardware Defect"       # v1 vocabulary
    with pytest.raises(ValueError):
        bundle["pipeline"].predict_proba(row[bundle["features"]])


def test_model_meets_srs_accuracy_and_is_not_suspiciously_perfect():
    card = json.loads((ROOT / "model" / "python_model" / "model_card_v2.json").read_text())
    assert 0.85 <= card["test"]["accuracy"] < 0.995
    assert max(card["leakage_audit"].values()) < 0.90


# ---------- consistency + decision ----------
@pytest.mark.parametrize("py,pc,gm,gc,expected", [
    ("Valid Claim", 0.92, "Valid Claim", 0.88, "Strong Match"),
    ("Valid Claim", 0.92, "Valid Claim", 0.72, "Acceptable Match"),
    ("Valid Claim", 0.95, "Valid Claim", 0.62, "Weak Match"),
    ("Valid Claim", 0.90, "Invalid Claim", 0.85, "Model Disagreement"),
    ("Valid Claim", 0.55, "Valid Claim", 0.90, "Uncertain Result"),
    ("Valid Claim", 0.60, "Valid Claim", 0.60, "Strong Match"),          # boundary: == min is allowed
])
def test_consistency_matrix(py, pc, gm, gc, expected):
    assert consistency_status(py, pc, gm, gc)[0] == expected


BASE = dict(hard_fail_count=0, contradiction_count=0, duplicate_count=0, missing_mandatory_count=0,
            manual_trigger_count=0, warning_count=0, consistency="Strong Match",
            python_class="Valid Claim", gtm_class="Valid Claim")


@pytest.mark.parametrize("override,expected", [
    ({}, "Likely Valid"),
    ({"hard_fail_count": 1}, "Likely Invalid"),
    ({"hard_fail_count": 1, "consistency": "Model Disagreement"}, "Likely Invalid"),   # hard fail wins
    ({"duplicate_count": 1}, "Manual Review Required"),
    ({"consistency": "Model Disagreement", "gtm_class": "Invalid Claim"}, "Manual Review Required"),
    ({"python_class": "Invalid Claim", "gtm_class": "Invalid Claim"}, "Likely Invalid"),
    ({"warning_count": 2}, "Likely Valid"),          # warnings are advisory; blocking rules use manual_review
    ({"manual_trigger_count": 1}, "Manual Review Required"),
    ({"missing_mandatory_count": 1}, "Manual Review Required"),
    ({"contradiction_count": 1}, "Manual Review Required"),
    ({"consistency": "Weak Match"}, "Manual Review Required"),
    ({"consistency": "Uncertain Result", "gtm_class": "Unavailable"}, "Manual Review Required"),
    ({"python_class": "Manual Review", "gtm_class": "Manual Review"}, "Manual Review Required"),
])
def test_decision_table(override, expected):
    assert decide({**BASE, **override})["decision"] == expected


def test_policy_file_is_valid():
    load_policy()


@pytest.mark.parametrize("raw", ["2026-09-26", "26/09/2026", "26-09-2026", "26 Sep 2026", "Sep 26, 2026"])
def test_all_configured_date_formats_parse(raw):
    assert str(parse_date(raw)) == "2026-09-26"
    assert len(DATE_FORMATS) >= 5
