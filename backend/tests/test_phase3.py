"""
Phase 3 Verification Tests — Text Classification Model

Tests:
- T3.1: Text dataset samples count per category >= 100
- T3.2: TF-IDF vectorizer and model files exist and load
- T3.3: docs/evaluation.md contains actual measured accuracy and F1 scores
- T3.4: predict("There is a huge pothole on the main road") -> Potholes / Damaged Roads
- T3.5: predict("Garbage piled up for days, bad smell") -> Garbage Accumulation
- T3.6: predict("") or predict("   ") handled gracefully without crash
- T3.7: Side-by-side comparison table (LR vs RF) in docs/evaluation.md
- T3.8: Inference latency per prediction is < 100ms
"""

import time
import pandas as pd
from pathlib import Path
import pytest

from backend.ml.text_classifier import TextClassifier, predict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_t3_1_dataset_samples():
    """T3.1: Text dataset has samples for all 4 categories with >= 100 per category."""
    csv_path = BASE_DIR / "data" / "text" / "complaints_dataset.csv"
    assert csv_path.exists(), f"Dataset file missing at {csv_path}"

    df = pd.read_csv(csv_path)
    assert len(df) >= 400, f"Expected at least 400 total samples, found {len(df)}"

    expected_categories = {
        "Potholes / Damaged Roads",
        "Garbage Accumulation",
        "Waterlogging / Drainage Problems",
        "Streetlight Faults",
    }
    found_categories = set(df["category"].unique())
    assert expected_categories == found_categories, f"Categories mismatch: {found_categories}"

    counts = df["category"].value_counts()
    for cat in expected_categories:
        assert counts[cat] >= 100, f"Category '{cat}' has {counts[cat]} samples, expected >= 100"


def test_t3_2_models_and_vectorizer_saved():
    """T3.2: TF-IDF vectorizer and trained model files exist and can be loaded."""
    models_dir = BASE_DIR / "backend" / "ml" / "models"

    vec_path = models_dir / "tfidf_vectorizer.joblib"
    lr_path = models_dir / "text_model_lr.joblib"
    rf_path = models_dir / "text_model_rf.joblib"
    best_path = models_dir / "text_model.joblib"

    assert vec_path.exists(), "tfidf_vectorizer.joblib missing"
    assert lr_path.exists(), "text_model_lr.joblib missing"
    assert rf_path.exists(), "text_model_rf.joblib missing"
    assert best_path.exists(), "text_model.joblib missing"

    # Verify loading via TextClassifier
    classifier = TextClassifier.get_instance()
    assert classifier.vectorizer is not None
    assert classifier.model is not None
    assert len(classifier.classes_) == 4


def test_t3_3_evaluation_docs_present():
    """T3.3: docs/evaluation.md contains actual measured accuracy and F1 metrics."""
    eval_doc = BASE_DIR / "docs" / "evaluation.md"
    assert eval_doc.exists(), "docs/evaluation.md does not exist"

    content = eval_doc.read_text(encoding="utf-8")
    assert "Text Classification Model Evaluation" in content
    assert "Accuracy" in content
    assert "F1-Score" in content
    assert "Per-Class Performance" in content

    # Verify confusion matrix image exists
    cm_img = BASE_DIR / "docs" / "text_confusion_matrix.png"
    assert cm_img.exists(), "docs/text_confusion_matrix.png does not exist"
    assert cm_img.stat().st_size > 0, "Confusion matrix image is 0 bytes"


def test_t3_4_predict_pothole():
    """T3.4: predict('There is a huge pothole on the main road') returns Potholes category."""
    category, confidence = predict("There is a huge pothole on the main road")
    assert category == "Potholes / Damaged Roads", f"Expected Potholes, got: {category}"
    assert confidence > 0.50, f"Expected confidence > 0.50, got {confidence}"


def test_t3_5_predict_garbage():
    """T3.5: predict('Garbage piled up for days, bad smell') returns Garbage category."""
    category, confidence = predict("Garbage piled up for days, bad smell")
    assert category == "Garbage Accumulation", f"Expected Garbage, got: {category}"
    assert confidence > 0.50, f"Expected confidence > 0.50, got {confidence}"


def test_t3_6_predict_edge_cases():
    """T3.6: predict('') or predict('   ') returns a handled result without crashing."""
    cat1, conf1 = predict("")
    assert cat1 in ["Unknown", "Potholes / Damaged Roads", "Garbage Accumulation", "Waterlogging / Drainage Problems", "Streetlight Faults"]
    assert conf1 >= 0.0

    cat2, conf2 = predict("   ")
    assert cat2 in ["Unknown", "Potholes / Damaged Roads", "Garbage Accumulation", "Waterlogging / Drainage Problems", "Streetlight Faults"]
    assert conf2 >= 0.0

    # Non-alphanumeric special characters only
    cat3, conf3 = predict("!@#$%^&*()")
    assert cat3 in ["Unknown", "Potholes / Damaged Roads", "Garbage Accumulation", "Waterlogging / Drainage Problems", "Streetlight Faults"]


def test_t3_7_model_comparison_documented():
    """T3.7: Side-by-side comparison table between Logistic Regression and Random Forest exists in docs/evaluation.md."""
    eval_doc = BASE_DIR / "docs" / "evaluation.md"
    content = eval_doc.read_text(encoding="utf-8")

    assert "Logistic Regression" in content
    assert "Random Forest" in content
    assert "Model Comparison" in content


def test_t3_8_inference_latency():
    """T3.8: Inference latency per prediction is < 100ms on local machine."""
    classifier = TextClassifier.get_instance()

    test_samples = [
        "Huge crater in the road causing accidents near hospital",
        "Rotting organic waste dumped on street corner with bad odor",
        "Waterlogging knee deep after rainfall, cars are stranded",
        "Streetlight not working on pole 14, dark alleyway",
    ]

    # Warm-up run
    for s in test_samples:
        classifier.predict(s)

    latencies = []
    for s in test_samples:
        t0 = time.perf_counter()
        classifier.predict(s)
        latencies.append(time.perf_counter() - t0)

    avg_latency_ms = (sum(latencies) / len(latencies)) * 1000
    print(f"\nAverage Text Inference Latency: {avg_latency_ms:.3f} ms")

    assert avg_latency_ms < 100.0, f"Average latency {avg_latency_ms}ms exceeded 100ms threshold"
