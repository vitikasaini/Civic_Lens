"""
Text Classifier Inference Module for CivicLens V1.0.

Provides singleton-style loaded inference using TF-IDF features and
the trained Logistic Regression model.
"""

import re
import joblib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "backend" / "ml" / "models"
VECTORIZER_PATH = MODELS_DIR / "tfidf_vectorizer.joblib"
MODEL_PATH = MODELS_DIR / "text_model.joblib"


def clean_text(text: str) -> str:
    """Normalize text input: lowercase, strip punctuation and whitespace."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class TextClassifier:
    """
    Inference engine for civic complaint text classification.
    Loads model weights once on instantiation.
    """
    _instance: Optional["TextClassifier"] = None

    def __init__(self, vectorizer_path: Path = VECTORIZER_PATH, model_path: Path = MODEL_PATH):
        if not vectorizer_path.exists():
            raise FileNotFoundError(f"TF-IDF vectorizer not found at: {vectorizer_path}")
        if not model_path.exists():
            raise FileNotFoundError(f"Text model not found at: {model_path}")

        self.vectorizer = joblib.load(vectorizer_path)
        self.model = joblib.load(model_path)
        self.classes_ = list(self.model.classes_)

    @classmethod
    def get_instance(cls) -> "TextClassifier":
        """Singleton accessor to ensure model is only loaded once in memory."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Classifies input text into one of the 4 civic issue categories:
        1. Potholes / Damaged Roads
        2. Garbage Accumulation
        3. Waterlogging / Drainage Problems
        4. Streetlight Faults

        Returns:
            (category: str, confidence: float)

        Edge cases handled:
            - Empty or whitespace-only string: returns ("Unknown", 0.0)
            - Very short text: classified with actual confidence
            - Gibberish / non-matching vocabulary: returns top prediction with low confidence
        """
        cleaned = clean_text(text)

        # Handle empty or whitespace-only input gracefully
        if not cleaned:
            return "Unknown", 0.0

        vec = self.vectorizer.transform([cleaned])

        # If text has zero overlap with trained vocabulary
        if vec.nnz == 0:
            # Fallback: uncertain prediction with lowest baseline confidence
            return "Unknown", 0.0

        probs = self.model.predict_proba(vec)[0]
        max_idx = int(np.argmax(probs))
        category = str(self.classes_[max_idx])
        confidence = float(probs[max_idx])

        return category, round(confidence, 4)

    def predict_detailed(self, text: str) -> Dict[str, Any]:
        """Returns predictions with confidences across all categories."""
        cleaned = clean_text(text)
        if not cleaned:
            return {
                "category": "Unknown",
                "confidence": 0.0,
                "probabilities": {c: 0.0 for c in self.classes_},
            }

        vec = self.vectorizer.transform([cleaned])
        if vec.nnz == 0:
            return {
                "category": "Unknown",
                "confidence": 0.0,
                "probabilities": {c: 0.25 for c in self.classes_},
            }

        probs = self.model.predict_proba(vec)[0]
        max_idx = int(np.argmax(probs))

        return {
            "category": str(self.classes_[max_idx]),
            "confidence": round(float(probs[max_idx]), 4),
            "probabilities": {
                c: round(float(p), 4) for c, p in zip(self.classes_, probs)
            },
        }


# Module-level convenience function
def predict(text: str) -> Tuple[str, float]:
    """Convenience helper to predict civic issue category from description."""
    return TextClassifier.get_instance().predict(text)
