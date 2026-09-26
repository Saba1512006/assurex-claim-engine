"""Single source of truth for every categorical value.

UI <select> options, dataset generator, preprocessor, policy files and card
renderer MUST import from here. tests/test_ml_integrity.py fails the build if
any layer drifts (the root cause of the v1 train/serve skew).

Per-category exclusions and deadlines live in policies/*.json (loaded by
src/rules/policy_store.py) so a surprise "add a warranty exclusion" is a
one-line JSON edit.
"""
from __future__ import annotations

from datetime import date, datetime

CATEGORIES = ("Consumer Electronics", "Home Appliances", "Industrial Tools")

# Neutral, customer-describable causes. None of these is a class label.
DAMAGE_TYPES = (
    "Manufacturing Defect",
    "Normal Wear and Tear",
    "Electrical Surge",
    "Mechanical Stress",
    "Accidental Drop",
    "Water Ingress",
    "Unknown / Not Sure",
)

FAULTS = {
    "Consumer Electronics": ("Screen flickering", "Motherboard failure", "Battery not charging",
                             "Speaker malfunction", "Touch panel unresponsive", "Wi-Fi/Bluetooth failure"),
    "Home Appliances": ("Compressor failure", "Motor burnout", "Thermostat failure",
                        "Drum spin malfunction", "PCB failure", "Water pump leakage"),
    "Industrial Tools": ("Armature burnout", "Seal failure", "Gearbox seizure",
                         "Chuck bearing failure", "Trigger switch failure"),
}

CLASSES = ("Valid Claim", "Invalid Claim", "Manual Review")
DECISIONS = ("Likely Valid", "Likely Invalid", "Manual Review Required")
CONSISTENCY_STATUSES = ("Strong Match", "Acceptable Match", "Weak Match", "Model Disagreement", "Uncertain Result")

# The four documents counted by `missing_document_count` (model feature) and required by every policy.
MANDATORY_DOCUMENTS = ("receipt", "warranty_card", "serial_photo", "damage_photo")
DOCUMENT_LABELS = {
    "receipt": "Purchase receipt / invoice",
    "warranty_card": "Warranty card",
    "serial_photo": "Serial-number photo",
    "damage_photo": "Damage / fault photo",
    "product_photo": "Product photo",
    "fault_video": "Fault video",
    "diagnostic_report": "Diagnostic / repair report",
    "other_evidence": "Other evidence",
}
# Upload types accepted per document kind (validated by magic bytes, not the extension alone).
DOCUMENT_TYPES = tuple(DOCUMENT_LABELS)

# Neutral prior used when no technician has assessed the fault yet (mean of the
# non-defect training distribution). Staff override it from the diagnostic report.
DEFAULT_DIAGNOSTIC_CONFIDENCE = 0.5

# Accepted input date formats (surprise modification: append one line here).
# Day-first formats are tried before month-first, so 03/04/2026 is 3 April.
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%b %d, %Y", "%d %B %Y")


def normalise_category(raw: str) -> str:
    """Map legacy/free-text category names onto the canonical vocabulary."""
    s = (raw or "").strip().lower()
    if "industrial" in s or "tool" in s:
        return "Industrial Tools"
    if "appliance" in s:
        return "Home Appliances"
    if "electronic" in s:
        return "Consumer Electronics"
    raise ValueError(f"Unknown product category: {raw!r}")


def parse_date(value) -> date:
    """Parse any configured date format; raise ValueError with the list tried."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date {value!r}; accepted formats: {', '.join(DATE_FORMATS)}")


def try_parse_date(value):
    """parse_date that returns None instead of raising (for optional fields)."""
    try:
        return parse_date(value) if value not in (None, "") else None
    except ValueError:
        return None


def coverage_days(months: int) -> int:
    """Warranty length in days for a term in months (same formula as the dataset generator)."""
    return int(round(int(months) * 30.44))
