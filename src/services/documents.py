"""Evidence upload, storage and duplicate-file checks (SRS v, xii, xiv, xv, xxxi).

Files are validated by their magic bytes (not the extension), stored under a
random name outside the web root, hashed with SHA-256 and OCR-processed when
they can carry text. The original filename is kept only as metadata.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from flask import current_app

from database.db import db
from src.core.vocab import DOCUMENT_LABELS
from src.models.entities import ClaimDocument
from src.ocr import document_processor as ocr

SIGNATURES = (
    (b"%PDF-", "application/pdf", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
)
EXT_OK = {"pdf": {"pdf"}, "png": {"png"}, "jpg": {"jpg", "jpeg"}, "mp4": {"mp4"}}
MAX_BYTES = {"fault_video": 16 * 1024 * 1024}
DEFAULT_MAX = 10 * 1024 * 1024
MIN_BYTES = 100


class UploadError(ValueError):
    """User-facing reason a file was refused."""


def sniff(head: bytes) -> tuple[str, str] | None:
    for magic, mime, ext in SIGNATURES:
        if head.startswith(magic):
            return mime, ext
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "video/mp4", "mp4"
    return None


def validate(file_storage, document_type: str) -> tuple[bytes, str, str]:
    """Return (content, mime, ext) or raise UploadError with a message the user can act on."""
    if document_type not in DOCUMENT_LABELS:
        raise UploadError("Unknown document type.")
    if file_storage is None or not file_storage.filename:
        raise UploadError("Choose a file to upload.")
    data = file_storage.read()
    label = DOCUMENT_LABELS[document_type]
    limit = MAX_BYTES.get(document_type, DEFAULT_MAX)
    if len(data) < MIN_BYTES:
        raise UploadError(f"{label}: the file is empty or damaged.")
    if len(data) > limit:
        raise UploadError(f"{label}: files can be at most {limit // (1024 * 1024)} MB.")
    kind = sniff(data[:16])
    declared = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if kind is None:
        raise UploadError(f"{label}: only PDF, JPG, JPEG or PNG files are accepted"
                          f"{' (MP4 for videos)' if document_type == 'fault_video' else ''}.")
    mime, ext = kind
    if declared not in EXT_OK[ext]:
        raise UploadError(f"{label}: the file content ({ext.upper()}) does not match its .{declared or '?'} extension.")
    if ext == "mp4" and document_type != "fault_video":
        raise UploadError(f"{label}: videos can only be uploaded as fault evidence.")
    if document_type == "fault_video" and ext != "mp4":
        raise UploadError("Fault video: upload an MP4 file.")
    return data, mime, ext


def upload_dir() -> Path:
    path = Path(current_app.config["UPLOAD_DIR"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def store(file_storage, document_type: str, *, claim=None, product=None, uploader=None,
          reject_unreadable_receipt: bool = True) -> tuple[ClaimDocument, dict]:
    """Validate, save, hash and OCR one file. Returns (document, info) where info carries
    OCR status/entities and duplicate-file hits. Caller commits."""
    from src.rules.duplicate_detector import document_reuse

    data, mime, ext = validate(file_storage, document_type)
    rel = f"docs/{uuid.uuid4().hex}.{ext}"
    dest = upload_dir() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    result = ocr.process(dest, mime, document_type)
    # Refuse a "receipt" whose text we could read but that has no invoice details, or an image where
    # OCR ran and found no text at all (a logo or unrelated photo). A scanned PDF without a text
    # layer, or any file when OCR isn't installed, is accepted and the user types the details.
    no_invoice_text = bool(result["text"].strip()) and not ocr.looks_like_receipt(result["entities"])
    blank_image = mime.startswith("image/") and result["status"] == "unreadable"
    if reject_unreadable_receipt and document_type == "receipt" and (no_invoice_text or blank_image):
        dest.unlink(missing_ok=True)
        raise UploadError("Purchase receipt: we could read text in this file but no invoice details "
                          "(invoice number, date, amount or serial). Upload the actual receipt.")
    file_hash = ocr.sha256_file(dest)
    doc = ClaimDocument(claim=claim, product=product or (claim.product if claim else None), uploaded_by=uploader,
                        document_type=document_type, file_path=rel,
                        original_filename=Path(file_storage.filename).name[:150], mime_type=mime,
                        file_size_bytes=len(data), file_hash_sha256=file_hash, ocr_status=result["status"],
                        ocr_extracted_text=result["text"] or None,
                        ocr_data_json=json.dumps(result["entities"]) if result["entities"] else None)
    db.session.add(doc)
    reuse = document_reuse(file_hash, exclude_claim_id=getattr(claim, "id", None),
                           exclude_product_id=getattr(product or getattr(claim, "product", None), "id", None))
    return doc, {"ocr_status": result["status"], "entities": result["entities"], "reused_in": reuse}


def absolute_path(doc: ClaimDocument) -> Path:
    base = upload_dir().resolve()
    path = (base / doc.file_path).resolve()
    if base not in path.parents:                      # never serve anything outside the upload root
        raise UploadError("Invalid document path.")
    return path


def remove(doc: ClaimDocument) -> None:
    try:
        absolute_path(doc).unlink(missing_ok=True)
    except UploadError:
        pass
    db.session.delete(doc)
