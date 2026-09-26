"""AssureX dataset generator v2 — leakage-free, policy-labelled, reproducible.

Design (why v1 scored 100% and v2 does not):
  * Attributes are sampled from realistic, OVERLAPPING distributions first,
    independent of the class.  The label is then DERIVED by an adjudication
    function that mirrors the warranty policy (hidden from the model), plus a
    small amount of label noise that models reviewer disagreement.
  * No field is a renamed label (v1 `damage_type` mapped 1:1 onto the class).
  * Claim IDs are assigned AFTER shuffling (v1 IDs 1-500 were all Valid).
  * Categorical values come from src/core/vocab.py and deadlines/exclusions from
    policies/*.json — the same sources the web application uses.

Run:  python dataset_generator/generator_v2.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.core.vocab import CATEGORIES, CLASSES, DAMAGE_TYPES, FAULTS, coverage_days  # noqa: E402
from src.rules.policy_store import get_policy  # noqa: E402

SEED = 42
PER_CLASS = 500
LABEL_NOISE = 0.04          # share of labels flipped: simulated reviewer disagreement
POLICIES = {c: get_policy(c) for c in CATEGORIES}
DAMAGE_P = {  # category-conditional prior over DAMAGE_TYPES (same order)
    "Consumer Electronics": (0.34, 0.16, 0.10, 0.06, 0.14, 0.12, 0.08),
    "Home Appliances":      (0.36, 0.22, 0.12, 0.10, 0.06, 0.08, 0.06),
    "Industrial Tools":     (0.30, 0.26, 0.06, 0.20, 0.08, 0.04, 0.06),
}
# Descriptive columns (never features): make each record a believable claim.
CATALOG = {
    "Consumer Electronics": {"brands": ("ApexTech", "NovaSound", "VividDisplay", "PixelCraft"),
                             "models": ("ApexBook Pro 16", "NovaPhone 12", "VividTab 11", "PixelWatch 3", "NovaPods Max")},
    "Home Appliances": {"brands": ("FrostGuard", "AeroBreeze", "CleanCycle", "KitchenPro"),
                        "models": ("FrostGuard 450L", "CleanCycle 8kg", "AeroBreeze 1.5T", "KitchenPro 30L")},
    "Industrial Tools": {"brands": ("TorqueMax", "IronForge", "HydraPower", "VoltEdge"),
                         "models": ("TorqueMax HD Drill", "IronForge Grinder 9", "HydraPower Jack 5T", "VoltEdge Saw 18V")},
}
RETAILERS = ("City Electronics Mall", "National Appliance Depot", "Industrial Supply Direct",
             "MegaMart Online", "Metro Hardware Centre", "Brand Flagship Store")
DAMAGE_PHRASE = {
    "Manufacturing Defect": "started without any external cause during normal use",
    "Normal Wear and Tear": "developed gradually with regular use",
    "Electrical Surge": "appeared after a power fluctuation",
    "Mechanical Stress": "appeared under heavy load",
    "Accidental Drop": "appeared after the unit was dropped",
    "Water Ingress": "appeared after contact with water",
    "Unknown / Not Sure": "has no obvious cause",
}


def _sample_attributes(rng: np.random.Generator) -> dict:
    cat = CATEGORIES[rng.integers(len(CATEGORIES))]
    pol = POLICIES[cat]
    terms = pol["standard_terms_months"]
    extended = rng.random() < 0.25
    months = int(rng.choice(terms)) + (pol["extended_extra_months"] if extended else 0)
    cover = coverage_days(months)
    claim_date = date(2026, 1, 1) + timedelta(days=int(rng.integers(0, 265)))

    regime = rng.random()          # where in the warranty life the claim falls
    if regime < 0.68:
        age = int(rng.integers(15, cover - 20))
    elif regime < 0.88:
        age = cover + int(rng.integers(-20, 21))           # boundary zone
    else:
        age = cover + int(rng.integers(21, 400))
    purchase = claim_date - timedelta(days=age)
    expiry = purchase + timedelta(days=cover)

    delay = int(min(rng.exponential(9), 90))
    fault_date = claim_date - timedelta(days=delay)
    conflict = rng.random() < 0.05
    if conflict:                    # fault reported before purchase
        fault_date = purchase - timedelta(days=int(rng.integers(1, 40)))

    damage = DAMAGE_TYPES[rng.choice(len(DAMAGE_TYPES), p=DAMAGE_P[cat])]
    diag = float(np.clip(rng.beta(5, 2) if damage == "Manufacturing Defect" else rng.beta(3, 3), 0, 1))
    repairs = int(min(rng.poisson(0.45), 4))
    unauthorized = bool(repairs and rng.random() < 0.22)
    docs = {
        "has_receipt": rng.random() < 0.90,
        "has_warranty_card": rng.random() < 0.86,
        "has_damage_photo": rng.random() < 0.90,
        "has_serial_photo": rng.random() < 0.86,
    }
    docs["has_repair_report"] = bool(repairs and rng.random() < 0.7)
    fault = str(rng.choice(FAULTS[cat]))
    brand = str(rng.choice(CATALOG[cat]["brands"]))
    return {
        "product_category": cat,
        "product_brand": brand,
        "product_model": str(rng.choice(CATALOG[cat]["models"])),
        "product_serial": f"SN-{brand[:3].upper()}-{int(rng.integers(1_000_000, 9_999_999))}",
        "retailer": str(rng.choice(RETAILERS)),
        "invoice_number": f"INV-{purchase.year}-{int(rng.integers(10_000, 99_999))}",
        "fault_category": fault,
        "fault_description": f"{fault}: the problem {DAMAGE_PHRASE[damage]}.",
        "damage_type": damage,
        "purchase_date": purchase, "warranty_expiry_date": expiry,
        "fault_occurrence_date": fault_date, "claim_submission_date": claim_date,
        "warranty_duration_months": months,
        "is_extended_warranty": int(extended),
        "purchase_price": round(float(rng.lognormal(6.4, 0.55)), 2),
        "product_age_days": age,
        "days_to_expiry": cover - age,                   # negative = expired
        "reporting_delay_days": max(0, (claim_date - fault_date).days),
        "diagnostic_confidence": round(diag, 3),
        "previous_repairs_count": repairs,
        "unauthorized_repair_flag": int(unauthorized),
        "serial_number_match": int(rng.random() < 0.93),
        "duplicate_invoice_flag": int(rng.random() < 0.03),
        "claim_date_conflict_flag": int(conflict),
        **{k: int(v) for k, v in docs.items()},
    }


def adjudicate(r: dict) -> tuple[str, str]:
    """Ground-truth policy (hidden from the model). Returns (class, scenario).

    The scenario names map to the SRS dataset requirement: normal (covered_defect),
    incomplete (missing_documents), contradictory (contradiction, serial_*),
    complex (repeat_repairs, ambiguous_cause, possible_duplicate) and borderline
    (grace_boundary)."""
    pol = POLICIES[r["product_category"]]
    overdue = -r["days_to_expiry"]
    excluded = r["damage_type"] in set(pol["excluded_damage_types"])
    if overdue > pol["grace_period_days"]:
        return "Invalid Claim", "expired"
    if r["unauthorized_repair_flag"]:
        return "Invalid Claim", "unauthorized_repair"
    if excluded and r["diagnostic_confidence"] >= pol["exclusion_min_diagnostic_confidence"]:
        return "Invalid Claim", "excluded_damage"
    if not r["serial_number_match"] and r["has_receipt"] and r["has_serial_photo"]:
        return "Invalid Claim", "serial_mismatch"
    if r["claim_date_conflict_flag"]:
        return "Manual Review", "contradiction"
    if r["reporting_delay_days"] > pol["claim_reporting_period_days"]:
        return "Invalid Claim", "late_reporting"
    missing = 4 - (r["has_receipt"] + r["has_warranty_card"] + r["has_damage_photo"] + r["has_serial_photo"])
    if 0 < overdue <= pol["grace_period_days"]:
        return "Manual Review", "grace_boundary"
    if r["duplicate_invoice_flag"]:
        return "Manual Review", "possible_duplicate"
    if not r["has_receipt"] or missing >= 2:
        return "Manual Review", "missing_documents"
    if not r["serial_number_match"]:
        return "Manual Review", "serial_unverifiable"
    if excluded or (r["damage_type"] == "Unknown / Not Sure" and r["diagnostic_confidence"] < 0.5):
        return "Manual Review", "ambiguous_cause"
    if r["previous_repairs_count"] >= pol["repeat_repair_review_threshold"]:
        return "Manual Review", "repeat_repairs"
    return "Valid Claim", "covered_defect"


def generate(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    buckets: dict[str, list] = {c: [] for c in CLASSES}
    while min(len(v) for v in buckets.values()) < PER_CLASS:
        r = _sample_attributes(rng)
        label, scenario = adjudicate(r)
        if rng.random() < LABEL_NOISE:                     # reviewer disagreement
            label = str(rng.choice([c for c in CLASSES if c != label]))
            scenario += "+noise"
        if len(buckets[label]) < PER_CLASS:
            buckets[label].append({**r, "scenario": scenario, "claim_class": label})
    df = pd.DataFrame([x for v in buckets.values() for x in v]).sample(frac=1, random_state=seed)
    df.insert(0, "claim_id", [f"CLM-{i:05d}" for i in range(1, len(df) + 1)])   # IDs after shuffle
    df.insert(1, "product_id", [f"PRD-{i:05d}" for i in range(1, len(df) + 1)])
    df["warranty_start_date"] = df["purchase_date"]
    for c in ("purchase_date", "warranty_start_date", "warranty_expiry_date",
              "fault_occurrence_date", "claim_submission_date"):
        df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m-%d")
    df["remaining_warranty_days"] = df["days_to_expiry"].clip(lower=0)
    df["missing_document_count"] = 4 - df[["has_receipt", "has_warranty_card", "has_damage_photo", "has_serial_photo"]].sum(axis=1)
    if df["claim_id"].duplicated().any():
        raise AssertionError("duplicate claim_id")
    return df.reset_index(drop=True)


def split(df: pd.DataFrame, seed: int = SEED):
    """Stratified 70/15/15 split performed BEFORE any card is rendered."""
    train, rest = train_test_split(df, test_size=0.30, stratify=df["claim_class"], random_state=seed)
    val, test = train_test_split(rest, test_size=0.50, stratify=rest["claim_class"], random_state=seed)
    ids = [set(x["claim_id"]) for x in (train, val, test)]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2]), "split leakage"
    return train, val, test


if __name__ == "__main__":
    out = ROOT / "data"
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "splits").mkdir(parents=True, exist_ok=True)
    data = generate()
    data.to_csv(out / "raw" / "common_warranty_claims_1500.csv", index=False)
    tr, va, te = split(data)
    for name, part in (("train", tr), ("val", va), ("test", te)):
        part.to_csv(out / "splits" / f"{name}.csv", index=False)
    stats = {
        "total": len(data),
        "by_class": data["claim_class"].value_counts().to_dict(),
        "by_scenario": data["scenario"].value_counts().to_dict(),
        "by_category": data["product_category"].value_counts().to_dict(),
        "splits": {n: {"rows": len(p), "by_class": p["claim_class"].value_counts().to_dict()}
                   for n, p in (("train", tr), ("val", va), ("test", te))},
        "label_noise_rate": LABEL_NOISE, "seed": SEED,
    }
    (out / "dataset_statistics.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
