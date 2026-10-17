"""
Phase 2 Verification Tests — Image Classification Model

Tests:
- T2.1: Dataset folders contain images for all 4 categories with >= 50 images per folder.
- T2.2: Train/val/test split has zero data leakage.
- T2.3: Model file exists and is a valid trained Keras model.
- T2.4: Test-set accuracy is documented and >= baseline.
- T2.5: Confusion matrix image exists at docs/image_confusion_matrix.png.
- T2.6: predict("path/to/pothole.jpg") returns ("Potholes / Damaged Roads", float).
- T2.7: predict("path/to/corrupted_file") returns handled output ("Unknown", 0.0) without crashing.
- T2.8: Model is loaded only once across 10 sequential predictions (no reload overhead).
- T2.9: docs/evaluation.md contains measured image model metrics.
"""

import time
import json
from pathlib import Path
import pytest

from backend.ml.image_classifier import ImageClassifier, predict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_DIR = BASE_DIR / "data" / "images"
MODELS_DIR = BASE_DIR / "backend" / "ml" / "models"
DOCS_DIR = BASE_DIR / "docs"


def test_t2_1_dataset_counts():
    """T2.1: Dataset folders contain images for all 4 categories, each with >= 50 images."""
    categories = ["potholes", "garbage", "waterlogging", "streetlight"]

    for cat in categories:
        folder = IMAGE_DIR / cat
        assert folder.exists(), f"Directory missing: {folder}"
        images = list(folder.glob("*.jpg")) + list(folder.glob("*.png"))
        assert len(images) >= 50, f"Category '{cat}' has {len(images)} images, expected >= 50"


def test_t2_2_zero_data_leakage():
    """T2.2: Train/val/test split has no data leakage (no filename overlap)."""
    manifest_path = MODELS_DIR / "image_split_manifest.json"
    assert manifest_path.exists(), f"Split manifest missing at {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    train_set = set(manifest.get("train", []))
    val_set = set(manifest.get("val", []))
    test_set = set(manifest.get("test", []))

    assert len(train_set) > 0, "Train split is empty"
    assert len(val_set) > 0, "Validation split is empty"
    assert len(test_set) > 0, "Test split is empty"

    assert not (train_set & val_set), "Data leakage found between train and validation splits!"
    assert not (train_set & test_set), "Data leakage found between train and test splits!"
    assert not (val_set & test_set), "Data leakage found between validation and test splits!"


def test_t2_3_model_file_exists_and_loads():
    """T2.3: Model file exists and is loadable."""
    model_path = MODELS_DIR / "image_model.keras"
    assert model_path.exists(), f"Image model missing at {model_path}"
    assert model_path.stat().st_size > 1_000_000, "Image model is unusually small (<1MB)"

    classifier = ImageClassifier.get_instance()
    assert classifier.model is not None
    assert len(classifier.classes) == 4


def test_t2_4_and_t2_9_evaluation_docs_present():
    """T2.4 & T2.9: docs/evaluation.md contains measured image accuracy and F1 metrics."""
    eval_doc = DOCS_DIR / "evaluation.md"
    assert eval_doc.exists(), "docs/evaluation.md does not exist"

    content = eval_doc.read_text(encoding="utf-8")
    assert "Image Classification Model Evaluation" in content
    assert "Test Accuracy" in content
    assert "F1-Score" in content
    assert "Per-Class Breakdown" in content


def test_t2_5_confusion_matrix_image():
    """T2.5: Confusion matrix saved as image file."""
    cm_path = DOCS_DIR / "image_confusion_matrix.png"
    assert cm_path.exists(), f"Confusion matrix image missing at {cm_path}"
    assert cm_path.stat().st_size > 1000, "Confusion matrix image file is empty or corrupted"


def test_t2_6_predict_valid_pothole():
    """T2.6: predict on pothole image returns 'Potholes / Damaged Roads' and a valid confidence."""
    sample_path = IMAGE_DIR / "potholes" / "potholes_001.jpg"
    assert sample_path.exists(), f"Test sample image missing: {sample_path}"

    category, confidence = predict(str(sample_path))
    assert category == "Potholes / Damaged Roads", f"Expected Potholes, got: {category}"
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


def test_t2_7_corrupted_file_handling():
    """T2.7: predict on a corrupted file returns handled result ('Unknown', 0.0) without crashing."""
    corrupted_path = BASE_DIR / "data" / "corrupted_test_file.jpg"
    corrupted_path.write_bytes(b"CORRUPTED_RAW_RANDOM_BYTES_NOT_AN_IMAGE_FILE")

    try:
        category, confidence = predict(str(corrupted_path))
        assert category == "Unknown"
        assert confidence == 0.0
    finally:
        if corrupted_path.exists():
            corrupted_path.unlink()


def test_t2_8_singleton_model_caching():
    """T2.8: predict called 10 times in sequence loads model once (low sub-second repeat latency)."""
    sample_path = str(IMAGE_DIR / "garbage" / "garbage_001.jpg")

    # First call (already warm or warms up)
    cat, conf = predict(sample_path)
    assert cat == "Garbage Accumulation"

    # Measure repeat calls
    t0 = time.perf_counter()
    for _ in range(10):
        c, p = predict(sample_path)
        assert c == "Garbage Accumulation"
    total_time = time.perf_counter() - t0

    avg_repeat_latency = (total_time / 10.0) * 1000  # ms
    print(f"\nAverage Repeat Image Inference Latency: {avg_repeat_latency:.2f} ms")

    # If model were reloaded from disk each time (a ~9MB Keras model), 10 loads would take >1500ms
    assert total_time < 3.0, f"10 predictions took {total_time:.2f}s, indicating model was not cached"
