"""Render Claim Summary Cards for every split + the claim-id mapping file.

train: N_VARIATIONS augmented cards per claim, grouped in class folders ready
       to drag into Teachable Machine (one folder per class).
val/test: one canonical card per claim (variation 0), never uploaded to TM.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.core.card_v2 import render_card  # noqa: E402

N_VARIATIONS = 2          # SRS minimum; 3 gives TM more robustness at ~50 MB extra
FOLDER = {"Valid Claim": "valid", "Invalid Claim": "invalid", "Manual Review": "manual_review"}


def main() -> None:
    splits = ROOT / "data" / "splits"
    cards = ROOT / "data" / "summary_cards"
    rows = []
    for split in ("train", "val", "test"):
        df = pd.read_csv(splits / f"{split}.csv")
        for rec in df.to_dict("records"):
            variations = range(1, N_VARIATIONS + 1) if split == "train" else [0]
            for v in variations:
                sub = cards / split / FOLDER[rec["claim_class"]] if split == "train" else cards / split
                sub.mkdir(parents=True, exist_ok=True)
                name = f"{rec['claim_id']}_v{v}.jpg"
                render_card(rec, v).save(sub / name, quality=85)
                rows.append({"claim_id": rec["claim_id"], "split": split, "claim_class": rec["claim_class"],
                             "variation": v, "filename": name,
                             "relative_path": str((sub / name).relative_to(cards))})
    m = pd.DataFrame(rows)
    # isolation guarantee: a claim id belongs to exactly one split
    assert m.groupby("claim_id")["split"].nunique().max() == 1, "claim appears in more than one split"
    m.to_csv(ROOT / "data" / "claim_id_to_card_mapping.csv", index=False)
    print(m.groupby(["split", "claim_class"]).size())


if __name__ == "__main__":
    main()
