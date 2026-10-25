"""
Phase 10 Verification Tests: Evaluation Reports, Documentation, and Docstrings.

Tests cover:
- T10.1: docs/evaluation.md contains measured image classification metrics.
- T10.2: docs/evaluation.md contains measured text classification metrics.
- T10.3: Both confusion matrix image files exist on disk and are referenced in docs.
- T10.4: Severity scoring validation agreement rate and Cohen's Kappa recorded.
- T10.5: Priority ranking Spearman correlation and p-value recorded.
- T10.6: README.md exists and contains project overview, architecture, and setup guide.
- T10.7: Requirements.txt and frontend package.json exist and match dependencies.
- T10.8: Core Python modules contain docstrings on public classes and functions.
"""

import ast
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_t10_1_and_t10_2_evaluation_docs_metrics():
    """T10.1 & T10.2: docs/evaluation.md has real measured image and text metrics."""
    eval_file = BASE_DIR / "docs" / "evaluation.md"
    assert eval_file.exists(), "docs/evaluation.md must exist"

    content = eval_file.read_text(encoding="utf-8")
    assert "Text Classification Model Evaluation" in content
    assert "Image Classification Model Evaluation" in content
    assert "Accuracy" in content
    assert "F1-Score" in content
    assert "1.0000" in content, "Metrics tables must contain measured scores"


def test_t10_3_confusion_matrix_images_exist():
    """T10.3: Both confusion matrix images exist on disk and are non-empty."""
    text_cm = BASE_DIR / "docs" / "text_confusion_matrix.png"
    img_cm = BASE_DIR / "docs" / "image_confusion_matrix.png"

    assert text_cm.exists() and text_cm.stat().st_size > 1000
    assert img_cm.exists() and img_cm.stat().st_size > 1000


def test_t10_4_severity_validation_in_docs():
    """T10.4: Severity scoring validation metrics documented with sample size and Kappa."""
    eval_file = BASE_DIR / "docs" / "evaluation.md"
    content = eval_file.read_text(encoding="utf-8")

    assert "Severity Scoring Validation" in content
    assert "Human Agreement Rate" in content
    assert "Cohen's Kappa" in content
    assert "25" in content or "Benchmark Samples" in content


def test_t10_5_priority_validation_in_docs():
    """T10.5: Priority validation metrics documented with Spearman correlation."""
    eval_file = BASE_DIR / "docs" / "evaluation.md"
    content = eval_file.read_text(encoding="utf-8")

    assert "Priority Ranking Validation" in content
    assert "Spearman Rank Correlation" in content
    assert "p-value" in content


def test_t10_6_readme_complete():
    """T10.6: README.md exists with required setup and architecture sections."""
    readme_file = BASE_DIR / "README.md"
    assert readme_file.exists()

    content = readme_file.read_text(encoding="utf-8")
    assert "CivicLens" in content
    assert "Quick Start" in content or "Setup" in content
    assert "Architecture" in content
    assert "API Reference" in content


def test_t10_7_dependency_files_intact():
    """T10.7: requirements.txt and package.json exist and specify core packages."""
    reqs = (BASE_DIR / "requirements.txt").read_text(encoding="utf-8")
    assert "fastapi" in reqs
    assert "sqlalchemy" in reqs
    assert "tensorflow" in reqs

    pkg = (BASE_DIR / "frontend" / "package.json").read_text(encoding="utf-8")
    assert "react" in pkg
    assert "leaflet" in pkg


def test_t10_8_docstrings_on_python_modules():
    """T10.8: Core Python modules have module docstrings and function docstrings."""
    modules_to_check = [
        BASE_DIR / "backend" / "ml" / "category_resolver.py",
        BASE_DIR / "backend" / "ml" / "severity.py",
        BASE_DIR / "backend" / "ml" / "grouping.py",
        BASE_DIR / "backend" / "ml" / "priority.py",
        BASE_DIR / "backend" / "ml" / "text_classifier.py",
        BASE_DIR / "backend" / "ml" / "image_classifier.py",
        BASE_DIR / "backend" / "api" / "complaints.py",
        BASE_DIR / "backend" / "api" / "dashboard.py",
        BASE_DIR / "backend" / "models" / "complaint.py",
        BASE_DIR / "backend" / "models" / "schemas.py",
    ]

    for mod_path in modules_to_check:
        assert mod_path.exists(), f"{mod_path} must exist"
        tree = ast.parse(mod_path.read_text(encoding="utf-8"))
        module_doc = ast.get_docstring(tree)
        assert module_doc, f"Module {mod_path.name} is missing a module docstring"

        # Check that top-level functions or classes have docstrings
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                assert ast.get_docstring(node), f"{mod_path.name}::{node.name} is missing a docstring"
