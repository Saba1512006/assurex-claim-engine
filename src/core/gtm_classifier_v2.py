"""Google Teachable Machine inference (SRS xxi).

Train the image model on teachablemachine.withgoogle.com with the class folders in
data/summary_cards/train/, then Export Model -> Tensorflow Lite -> Floating point
(or Quantized). Put `model_unquant.tflite` (or `model.tflite`) and `labels.txt` in
model/teachable_machine/ - or upload both from Admin > Models.

Runtime: `pip install ai-edge-litert` (preferred), `tflite-runtime` or full `tensorflow`.
Preprocessing is identical to the Teachable Machine export sample:
ImageOps.fit to the model's input size (LANCZOS), then scale to [-1, 1] (float
models) or raw uint8 (quantized models).

There is deliberately NO fallback model: without the real export the
comparison reports "Teachable Machine model unavailable" and the claim goes to
manual review.
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from src.core.vocab import CLASSES

ROOT = Path(__file__).resolve().parent.parent.parent
GTM_DIR = ROOT / "model" / "teachable_machine"
MODEL_FILES = ("model_unquant.tflite", "model.tflite")


class GTMUnavailable(RuntimeError):
    pass


def _interpreter_cls():
    for mod, attr in (("ai_edge_litert.interpreter", "Interpreter"),
                      ("tflite_runtime.interpreter", "Interpreter"),
                      ("tensorflow.lite", "Interpreter")):
        try:
            return getattr(__import__(mod, fromlist=[attr]), attr)
        except (ImportError, AttributeError):          # TensorFlow >= 2.20 no longer ships tf.lite.Interpreter
            continue
    raise GTMUnavailable("No TensorFlow Lite runtime installed (pip install ai-edge-litert).")


# Class names as typed in Teachable Machine (or the training folder names) -> canonical class.
LABEL_ALIASES = {"valid claim": "Valid Claim", "valid": "Valid Claim",
                 "invalid claim": "Invalid Claim", "invalid": "Invalid Claim",
                 "manual review": "Manual Review", "manual_review": "Manual Review"}


def parse_labels(text: str) -> list[str]:
    """labels.txt lines look like '0 Valid Claim'. Returns canonical labels in index order."""
    labels = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        idx, _, name = ln.partition(" ")
        name = name.strip() if idx.isdigit() and name else ln
        labels.append(LABEL_ALIASES.get(name.lower(), name))
    return labels


def version_of(model_bytes: bytes) -> str:
    return "gtm-" + hashlib.sha256(model_bytes).hexdigest()[:12]


def find_model_file(model_dir: Path = GTM_DIR) -> Path | None:
    return next((model_dir / f for f in MODEL_FILES if (model_dir / f).exists()), None)


class TeachableMachineClassifier:
    def __init__(self, model_dir: Path = GTM_DIR):
        model_path = find_model_file(model_dir)
        if model_path is None:
            raise GTMUnavailable("Teachable Machine export not installed (model/teachable_machine/model_unquant.tflite).")
        labels_path = model_dir / "labels.txt"
        if not labels_path.exists():
            raise GTMUnavailable("labels.txt is missing next to the Teachable Machine model.")
        self.labels = parse_labels(labels_path.read_text(encoding="utf-8"))
        if sorted(self.labels) != sorted(CLASSES):
            raise GTMUnavailable(f"Teachable Machine labels {self.labels} must be exactly {list(CLASSES)}.")
        raw = model_path.read_bytes()
        self.version = version_of(raw)                   # immutable version id
        self.model_file = model_path.name
        try:
            # Load from bytes, not from the path: an interpreter built from a path memory-maps the file,
            # and Windows then refuses to replace or archive it while the app is running.
            self._interp = _interpreter_cls()(model_content=raw)
            self._interp.allocate_tensors()
        except GTMUnavailable:
            raise
        except Exception as exc:
            raise GTMUnavailable(f"Teachable Machine model could not be loaded: {type(exc).__name__}") from None
        self._in = self._interp.get_input_details()[0]
        self._out = self._interp.get_output_details()[0]
        _, self.h, self.w, _ = (int(x) for x in self._in["shape"])
        self.quantized = self._in["dtype"] == np.uint8
        self._lock = threading.Lock()                    # tflite interpreters are not thread-safe

    def _prepare(self, image) -> np.ndarray:
        img = image if isinstance(image, Image.Image) else Image.open(image)
        img = ImageOps.fit(img.convert("RGB"), (self.w, self.h), Image.Resampling.LANCZOS)
        arr = np.asarray(img)
        if self.quantized:
            return arr.astype(np.uint8)[np.newaxis, ...]
        return ((arr.astype(np.float32) / 127.5) - 1.0)[np.newaxis, ...]

    def predict(self, image) -> dict:
        x = self._prepare(image)
        with self._lock:
            self._interp.set_tensor(self._in["index"], x)
            self._interp.invoke()
            out = self._interp.get_tensor(self._out["index"])[0]
        probs = out.astype(np.float64)
        if self._out["dtype"] == np.uint8:
            scale, zero = self._out.get("quantization", (1 / 255.0, 0))
            probs = (probs - zero) * (scale or 1 / 255.0)
        probs = np.clip(probs, 0, None)
        probs = probs / probs.sum() if probs.sum() > 0 else np.full(len(probs), 1 / len(probs))
        scores = {lbl: round(float(p), 4) for lbl, p in zip(self.labels, probs)}
        top = max(scores, key=scores.get)
        return {"model_type": "google_teachable_machine_image", "model_version": self.version,
                "predicted_class": top, "top_confidence": scores[top],
                "confidence_scores": {c: scores.get(c, 0.0) for c in CLASSES}}


_lock = threading.Lock()
_instance: TeachableMachineClassifier | None = None
_error: str | None = None


def get_gtm_classifier() -> TeachableMachineClassifier:
    global _instance, _error
    with _lock:
        if _instance is None and _error is None:
            try:
                _instance = TeachableMachineClassifier()
            except GTMUnavailable as exc:
                _error = str(exc)
        if _instance is None:
            raise GTMUnavailable(_error)
        return _instance


def reset() -> None:
    global _instance, _error
    with _lock:
        _instance, _error = None, None


def evaluation() -> dict:
    path = GTM_DIR / "evaluation.json"
    return json.loads(path.read_text()) if path.exists() else {}
