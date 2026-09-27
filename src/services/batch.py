"""Admin batch evaluation (a CSV in the training-split schema, e.g. data/splits/test.csv).

Upload validates every row up front; processing then runs CHUNK rows per poll through exactly the production
pipeline (Python model, Claim Summary Card, Teachable Machine, rules, decision table) without touching the
claims tables. PythonAnywhere has no background workers, so the browser drives the work one chunk at a time.
"""
from __future__ import annotations

import csv
import io
import json
import time
from collections import Counter
from datetime import date

from database.db import db
from src.core.features import BINARY, CATEGORICAL, MODEL_FEATURES, NUMERIC, FeatureError, validate
from src.core.pipeline import run
from src.core.vocab import CLASSES
from src.models.entities import BatchRun, utcnow
from src.rules.policy_store import get_policy

CHUNK = 20
MAX_ROWS = 500
MAX_BYTES = 2 * 1024 * 1024
CARD_COLUMNS = ["claim_id", "fault_category", "product_brand", "product_model", "product_serial", "purchase_date",
                "warranty_expiry_date", "fault_occurrence_date", "claim_submission_date"]
REQUIRED = MODEL_FEATURES + CARD_COLUMNS
DATES = ["purchase_date", "warranty_expiry_date", "fault_occurrence_date", "claim_submission_date"]
FLAG_DOC = {"has_receipt": "receipt", "has_warranty_card": "warranty_card", "has_serial_photo": "serial_photo",
            "has_damage_photo": "damage_photo"}
DECISION_TO_CLASS = {"Likely Valid": "Valid Claim", "Likely Invalid": "Invalid Claim", "Manual Review Required": "Manual Review"}
RESULT_COLUMNS = ["claim_id", "actual_class", "python_predicted", "python_top", "gtm_predicted", "gtm_top",
                  "consistency_status", "confidence_difference", "final_decision", "decision_rule", "decision_reason"]


class BatchError(ValueError):
    def __init__(self, message: str, rows: list[str] | None = None):
        super().__init__(message)
        self.rows = rows or []


def _row(raw: dict, n: int) -> dict:
    rec = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
    try:
        for k in NUMERIC:
            rec[k] = float(rec[k])
        for k in BINARY:
            rec[k] = int(float(rec[k]))
        for k in DATES:
            date.fromisoformat(rec[k])
        for k in CATEGORICAL + ["claim_id", "fault_category"]:
            if not rec[k]:
                raise ValueError(f"{k} is empty")
        validate(rec)
    except (ValueError, FeatureError) as exc:
        raise BatchError(f"Row {n}: {exc}") from None
    label = rec.get("claim_class") or rec.get("actual_class") or ""
    if label and label not in CLASSES:
        raise BatchError(f"Row {n}: claim_class must be one of {', '.join(CLASSES)}.")
    rec["claim_class"] = label
    rec.setdefault("fault_description", "")
    rec["previous_replacement_details"] = rec.get("previous_replacement_details") or ""
    return rec


def parse(file) -> tuple[str, list[dict]]:
    """Validate the whole upload before anything runs. Raises BatchError listing up to ten bad rows."""
    if file is None or not file.filename:
        raise BatchError("Choose a CSV file.")
    if not file.filename.lower().endswith(".csv"):
        raise BatchError("Upload a .csv file in the training-split format.")
    data = file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise BatchError("The file is larger than 2 MB. Split it into smaller batches.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BatchError("The file is not UTF-8 text. Save it as CSV (UTF-8) and try again.") from None
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        raise BatchError(f"Missing columns: {', '.join(missing)}.")
    rows, errors = [], []
    for n, raw in enumerate(reader, start=2):
        if len(rows) + len(errors) >= MAX_ROWS:
            raise BatchError(f"At most {MAX_ROWS} rows per batch.")
        try:
            rows.append(_row(raw, n))
        except BatchError as exc:
            errors.append(str(exc))
    if errors:
        raise BatchError(f"{len(errors)} row{'s' if len(errors) != 1 else ''} could not be read.", errors[:10])
    if not rows:
        raise BatchError("The file has a header but no rows.")
    return file.filename[:150], rows


def create(user, filename: str, rows: list[dict]) -> BatchRun:
    b = BatchRun(created_by_id=user.id, filename=filename, total=len(rows), rows_json=json.dumps(rows))
    db.session.add(b)
    db.session.flush()
    return b


def _evaluate(rec: dict) -> dict:
    started = time.perf_counter()
    contradictions = ([{"code": "DATE_CONFLICT", "message": "Fault/claim dates conflict with the purchase date"}]
                      if rec.get("claim_date_conflict_flag") else []) + \
                     ([{"code": "SERIAL_MISMATCH", "message": "Serial number does not match the evidence"}]
                      if not rec.get("serial_number_match", 1) else [])
    duplicates = [{"code": "INVOICE_REUSED", "message": "Invoice number reused"}] if rec.get("duplicate_invoice_flag") else []
    mandatory = set(get_policy(rec["product_category"])["mandatory_documents"])
    missing = [d for f, d in FLAG_DOC.items() if not int(rec[f]) and d in mandatory]
    out = run(rec, contradictions={"findings": contradictions, "date_conflict": bool(contradictions), "serial_mismatch": False,
                                   "serials_seen": []},
              duplicates={"indicators": duplicates}, missing=missing,
              preprocess_ms=round((time.perf_counter() - started) * 1000), claim_id=rec["claim_id"], explain=False)
    p = out["payload"]
    return {"claim_id": rec["claim_id"], "actual_class": rec["claim_class"],
            "python_predicted": p["python"]["predicted"], "python_top": p["python"]["top"],
            "gtm_predicted": p["gtm"]["predicted"] or "Unavailable", "gtm_top": p["gtm"]["top"],
            "consistency_status": p["consistency"]["status"], "confidence_difference": p["consistency"]["difference"],
            "final_decision": p["decision"]["value"], "decision_rule": p["decision"]["rule_id"],
            "decision_reason": p["decision"]["reason"]}


def step(b: BatchRun) -> BatchRun:
    """Process the next CHUNK rows (idempotent once done)."""
    if b.status in ("done", "failed"):
        return b
    rows, results = b.rows(), b.results()
    b.status = "running"
    try:
        for rec in rows[b.processed:b.processed + CHUNK]:
            results.append(_evaluate(rec))
    except Exception as exc:                      # a model error fails the batch visibly instead of hanging
        b.status, b.error, b.finished_at = "failed", str(exc)[:500], utcnow()
        return b
    b.results_json, b.processed = json.dumps(results), len(results)
    if b.processed >= b.total:
        b.status, b.finished_at = "done", utcnow()
    return b


def summary(b: BatchRun) -> dict:
    res = b.results()
    counts = Counter(r["final_decision"] for r in res)
    labelled = [r for r in res if r["actual_class"]]
    out = {"batch_id": b.batch_id, "status": b.status, "total": b.total, "processed": b.processed, "error": b.error,
           "decisions": {d: counts.get(d, 0) for d in DECISION_TO_CLASS},
           "agreement": round(sum(r["python_predicted"] == r["gtm_predicted"] for r in res) / len(res), 4) if res else None,
           "labelled": len(labelled)}
    if labelled:
        out["python_accuracy"] = round(sum(r["python_predicted"] == r["actual_class"] for r in labelled) / len(labelled), 4)
        gtm_rows = [r for r in labelled if r["gtm_predicted"] != "Unavailable"]
        out["gtm_accuracy"] = round(sum(r["gtm_predicted"] == r["actual_class"] for r in gtm_rows) / len(gtm_rows), 4) if gtm_rows else None
        out["decision_accuracy"] = round(sum(DECISION_TO_CLASS[r["final_decision"]] == r["actual_class"] for r in labelled) / len(labelled), 4)
    return out


def to_csv(b: BatchRun) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=RESULT_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for r in b.results():
        w.writerow({k: ("'" + v if isinstance(v, str) and v[:1] in "=+-@" else v) for k, v in r.items()})
    return buf.getvalue()
