# Sample claims — the 11 SRS demonstration cases

Each file holds one claim **feature record** (the exact columns the Python model and rule engine
use, same as `data/splits/*.csv`) plus the expected recommendation and the decision-table row that
should produce it. `tests/test_demonstration_cases.py` runs every file through the production
components: warranty rules → Python model → consistency status → decision table.

The Teachable Machine prediction cannot be computed without the exported model, so each file
states what the image model is assumed to say: the same class as the Python model, except case 11,
where it is forced to disagree. Once the real export is installed, `notebooks/evaluate_gtm.py`
produces the measured comparison for the whole test split.

| # | Case | Expected | Row |
|---|------|----------|-----|
| 1 | Valid claim | Likely Valid | D07 |
| 2 | Invalid claim (water ingress, confirmed) | Likely Invalid | D01 |
| 3 | Manual review (unknown cause) | Manual Review Required | D05 |
| 4 | Expired warranty | Likely Invalid | D01 |
| 5 | Missing receipt | Manual Review Required | D03 |
| 6 | Duplicate invoice | Manual Review Required | D02 |
| 7 | Contradictory dates | Manual Review Required | D02 |
| 8 | Serial mismatch | Likely Invalid | D01 |
| 9 | Unauthorised repair | Likely Invalid | D01 |
| 10 | Boundary date (inside grace period; model confidence < 0.60) | Manual Review Required | D04 |
| 11 | Model disagreement | Manual Review Required | D04 |

The seeded demo database (`python database/seed.py`) contains the same eleven situations as real
claims with generated receipts and photos, submitted through the web pipeline.
