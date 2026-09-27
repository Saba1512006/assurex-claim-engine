"""One response envelope and one error vocabulary for every JSON endpoint.

    {"success": true,  "data": {...}, "error": null}
    {"success": false, "data": null, "error": {"code", "message", "fields", "reference"}}

Messages live in MESSAGES so tests can assert them. 500s carry only a reference that is logged.
"""
from __future__ import annotations

import secrets
from enum import Enum

from flask import current_app, jsonify


class ErrorCode(str, Enum):
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    NO_PERMISSION = "NO_PERMISSION"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    TOO_LARGE = "TOO_LARGE"
    UNREADABLE_FILE = "UNREADABLE_FILE"
    RATE_LIMITED = "RATE_LIMITED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    SERVER_ERROR = "SERVER_ERROR"


MESSAGES = {
    ErrorCode.VALIDATION_FAILED: "Some values need attention. Check the highlighted fields and try again.",
    ErrorCode.NOT_AUTHENTICATED: "Sign in to continue.",
    ErrorCode.NO_PERMISSION: "Your role doesn't include this action.",
    ErrorCode.NOT_FOUND: "We couldn't find that record.",
    ErrorCode.CONFLICT: "That change conflicts with the record's current state. Reload the page and try again.",
    ErrorCode.INVALID_TRANSITION: "This claim can't move to that status from its current stage.",
    ErrorCode.TOO_LARGE: "That upload is too large. Files can be at most 16 MB.",
    ErrorCode.UNREADABLE_FILE: "We couldn't read that file. Upload a CSV, PDF or image that opens on your computer.",
    ErrorCode.RATE_LIMITED: "Too many requests in a short time. Wait a minute and try again.",
    ErrorCode.MODEL_UNAVAILABLE: "A model could not run, so the claim was routed to a person.",
    ErrorCode.SERVER_ERROR: "Something went wrong on our side. Your data is safe; try again in a moment.",
}
STATUS = {ErrorCode.VALIDATION_FAILED: 400, ErrorCode.NOT_AUTHENTICATED: 401, ErrorCode.NO_PERMISSION: 403,
          ErrorCode.NOT_FOUND: 404, ErrorCode.CONFLICT: 409, ErrorCode.INVALID_TRANSITION: 409, ErrorCode.TOO_LARGE: 413,
          ErrorCode.UNREADABLE_FILE: 422, ErrorCode.RATE_LIMITED: 429, ErrorCode.MODEL_UNAVAILABLE: 409,
          ErrorCode.SERVER_ERROR: 500}


def reference() -> str:
    return "ERR-" + secrets.token_hex(3).upper()


def ok(data=None, status: int = 200):
    return jsonify(success=True, data=data if data is not None else {}, error=None), status


def fail(code: ErrorCode, message: str | None = None, fields: dict | None = None, status: int | None = None):
    ref = reference()
    if code is ErrorCode.SERVER_ERROR:
        current_app.logger.exception("API error %s", ref)
    return jsonify(success=False, data=None, error={"code": code.value, "message": message or MESSAGES[code],
                                                    "fields": fields or {}, "reference": ref}), status or STATUS[code]
