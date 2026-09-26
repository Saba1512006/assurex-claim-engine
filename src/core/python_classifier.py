"""Python classification model runtime (SRS xviii, xix, xlviii).

Loads the single sklearn Pipeline artefact produced by notebooks/train_python_v2.py.
It never retrains itself: a missing or incompatible artefact raises ModelUnavailable,
and the claim is routed to manual review with a clear message (SRS xlix).
The version string embeds the artefact hash, so every stored prediction points
to the exact file that produced it.
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import joblib
import pandas as pd

from src.core.features import MODEL_FEATURES
from src.core.vocab import CLASSES

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "model" / "python_model"
ARTEFACT = MODEL_DIR / "claim_classifier_v2.joblib"
CARD = MODEL_DIR / "model_card_v2.json"


class ModelUnavailable(RuntimeError):
    """The model file is missing, corrupt or incompatible with the running library versions."""


class PythonClaimClassifier:
    def __init__(self, path: Path = ARTEFACT):
        if not path.exists():
            raise ModelUnavailable(f"Python model file not found ({path.name}). Run notebooks/train_python_v2.py.")
        raw = path.read_bytes()
        try:
            bundle = joblib.load(path)
        except Exception as exc:  # pickle from another sklearn version, truncated file, ...
            raise ModelUnavailable(f"Python model could not be loaded: {type(exc).__name__}") from None
        if bundle.get("features") != MODEL_FEATURES:
            raise ModelUnavailable("Python model was trained on a different feature list; retrain it.")
        self.pipeline = bundle["pipeline"]
        self.classes = [str(c) for c in self.pipeline.classes_]
        if set(self.classes) != set(CLASSES):
            raise ModelUnavailable(f"Python model classes {self.classes} do not match {list(CLASSES)}.")
        self.version = f"{bundle.get('version', 'v?')}+{hashlib.sha256(raw).hexdigest()[:12]}"
        self.sklearn_version = bundle.get("sklearn_version")

    def predict(self, features: dict) -> dict:
        row = pd.DataFrame([{f: features[f] for f in MODEL_FEATURES}])
        try:
            probs = self.pipeline.predict_proba(row)[0]
        except ValueError as exc:            # unknown category -> OneHotEncoder(handle_unknown="error")
            raise ModelUnavailable(f"Python model rejected the input: {exc}") from None
        scores = {c: round(float(p), 4) for c, p in zip(self.classes, probs)}
        top = max(scores, key=scores.get)
        return {"model_type": "python_tabular", "model_version": self.version, "predicted_class": top,
                "top_confidence": scores[top], "confidence_scores": {c: scores[c] for c in CLASSES}}


_lock = threading.Lock()
_instance: PythonClaimClassifier | None = None
_error: str | None = None


def get_python_classifier() -> PythonClaimClassifier:
    """Process-wide singleton. Raises ModelUnavailable (cached) if the artefact cannot be used."""
    global _instance, _error
    with _lock:
        if _instance is None and _error is None:
            try:
                _instance = PythonClaimClassifier()
            except ModelUnavailable as exc:
                _error = str(exc)
        if _instance is None:
            raise ModelUnavailable(_error)
        return _instance


def reset() -> None:
    global _instance, _error
    with _lock:
        _instance, _error = None, None


def model_card() -> dict:
    return json.loads(CARD.read_text()) if CARD.exists() else {}
