"""Read a receipt for a form without storing it (SRS vi, vii); one JSON envelope for the product form and the wizard."""
from __future__ import annotations

import tempfile
from pathlib import Path

from src.api.errors import ErrorCode, fail, ok
from src.ocr import document_processor as ocr
from src.services import documents as doc_service

UNAVAILABLE = "Automatic reading isn't available for this file type on this server. Type the details from your receipt."
UNREADABLE = "We couldn't find invoice details in this file. Check that it is the receipt and that it is legible."


def scan(file):
    try:
        data, mime, ext = doc_service.validate(file, "receipt")
    except doc_service.UploadError as exc:
        return fail(ErrorCode.VALIDATION_FAILED, str(exc), fields={"receipt": str(exc)})
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"receipt.{ext}"
        path.write_bytes(data)
        result = ocr.process(path, mime, "receipt")
    if result["status"] == "unavailable":
        return fail(ErrorCode.UNREADABLE_FILE, UNAVAILABLE)
    if result["status"] != "ok" or not ocr.looks_like_receipt(result["entities"]):
        return fail(ErrorCode.UNREADABLE_FILE, UNREADABLE)
    return ok({"entities": result["entities"], "text": result.get("text", "")})
