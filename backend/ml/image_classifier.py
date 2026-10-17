"""
Image Classifier Inference Module for CivicLens V1.0.

Provides singleton-style MobileNetV2 transfer learning inference:
- Model is loaded once on startup into memory.
- Preprocesses input images (resize to 224x224, BGR->RGB, MobileNetV2 scaling).
- Handles edge cases: missing files, corrupted files, unsupported extensions, tiny images.
- Returns (category, confidence) tuple and optional detailed probability breakdown.
"""

import json
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
import numpy as np
import cv2

import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "backend" / "ml" / "models"
MODEL_PATH = MODELS_DIR / "image_model.keras"
CLASSES_PATH = MODELS_DIR / "image_classes.json"

DEFAULT_CLASSES = [
    "Garbage Accumulation",
    "Potholes / Damaged Roads",
    "Streetlight Faults",
    "Waterlogging / Drainage Problems",
]


class ImageClassifier:
    """
    Singleton MobileNetV2 classifier for civic issue images.
    Caches model in memory to eliminate re-load overhead on repeat inference.
    """
    _instance: Optional["ImageClassifier"] = None

    def __init__(self, model_path: Path = MODEL_PATH, classes_path: Path = CLASSES_PATH):
        if not model_path.exists():
            raise FileNotFoundError(f"Trained image model not found at: {model_path}")

        # Load classes
        if classes_path.exists():
            with open(classes_path, "r", encoding="utf-8") as f:
                self.classes: List[str] = json.load(f)
        else:
            self.classes = DEFAULT_CLASSES

        # Load Keras model once
        self.model = tf.keras.models.load_model(str(model_path))

    @classmethod
    def get_instance(cls) -> "ImageClassifier":
        """Singleton accessor ensuring the model is loaded only once."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def predict(self, image_path: str) -> Tuple[str, float]:
        """
        Classifies an input image into one of the 4 civic issue categories:
        1. Potholes / Damaged Roads
        2. Garbage Accumulation
        3. Waterlogging / Drainage Problems
        4. Streetlight Faults

        Args:
            image_path: Absolute or relative path to the image file.

        Returns:
            (category: str, confidence: float)

        Edge case handling:
            - File not found: raises FileNotFoundError or returns handled fallback
            - Corrupted file: returns ("Unknown", 0.0) without crashing
            - Very small image (e.g. 1x1): safely resized and classified
        """
        p = Path(image_path)
        if not p.is_absolute():
            p = BASE_DIR / p

        if not p.exists():
            raise FileNotFoundError(f"Image file does not exist: {image_path}")

        # Read image using OpenCV
        img = cv2.imread(str(p))
        if img is None or img.size == 0:
            # Corrupted image or unsupported raw bytes
            return "Unknown", 0.0

        try:
            # Resize safely to standard input dimensions (224, 224)
            img_resized = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA if img.shape[0] > 224 else cv2.INTER_LINEAR)
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB).astype(np.float32)
            img_preprocessed = preprocess_input(img_rgb)
            batch = np.expand_dims(img_preprocessed, axis=0)

            probs = self.model.predict(batch, verbose=0)[0]
            max_idx = int(np.argmax(probs))
            category = self.classes[max_idx]
            confidence = float(probs[max_idx])

            return category, round(confidence, 4)
        except Exception:
            return "Unknown", 0.0

    def predict_detailed(self, image_path: str) -> Dict[str, Any]:
        """Returns predictions with confidences across all categories."""
        cat, conf = self.predict(image_path)
        if cat == "Unknown":
            return {
                "category": "Unknown",
                "confidence": 0.0,
                "probabilities": {c: 0.0 for c in self.classes},
            }

        p = Path(image_path)
        if not p.is_absolute():
            p = BASE_DIR / p

        img = cv2.imread(str(p))
        img_resized = cv2.resize(img, (224, 224))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB).astype(np.float32)
        batch = np.expand_dims(preprocess_input(img_rgb), axis=0)
        probs = self.model.predict(batch, verbose=0)[0]

        return {
            "category": cat,
            "confidence": conf,
            "probabilities": {c: round(float(p), 4) for c, p in zip(self.classes, probs)},
        }


def predict(image_path: str) -> Tuple[str, float]:
    """Module-level convenience wrapper."""
    return ImageClassifier.get_instance().predict(image_path)
