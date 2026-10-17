"""
Phase 4 Verification Tests — Category Resolution & Severity Assessment

Tests:
- T4.1: resolve agreement case
- T4.2: resolve conflict case per Decision 3 rule
- T4.3: resolution logs source confidences and decision reason
- T4.4: text cue scoring with high-severity keywords -> +2
- T4.5: text cue scoring with routine/default description -> 0
- T4.6: citizen severity points (Minor=0, Moderate=1, Severe=2)
- T4.7: image cue on pothole image with large affected area -> +1
- T4.8: image cue on waterlogging image -> 0 (category restricted)
- T4.9: combined scoring: 2 + 2 + 1 = 5 -> "High"
- T4.10: combined scoring: 0 + 0 + 0 = 0 -> "Low"
- T4.11: combined scoring: 1 + 1 + 0 = 2 -> "Medium"
- T4.12: end-to-end API submission fills category, severity, severity_points in DB
- T4.13: severity breakdown JSON accessible in GET /api/complaints/{id}
"""

import io
import cv2
import numpy as np
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import get_db, init_db, Base
from backend.models.complaint import Complaint
from backend.ml.category_resolver import resolve, resolve_detailed
from backend.ml.severity import (
    score_text_cues,
    score_image_cue,
    assess_severity,
    CITIZEN_SEVERITY_POINTS,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_DIR = BASE_DIR / "data" / "images"


def test_t4_1_resolve_agreement():
    """T4.1: resolve(('Pothole', 0.9), ('Pothole', 0.8)) -> 'Potholes / Damaged Roads'."""
    result = resolve(("Potholes / Damaged Roads", 0.90), ("Potholes / Damaged Roads", 0.80))
    assert result == "Potholes / Damaged Roads"

    # Also test with shorthand names
    res_short = resolve(("pothole", 0.88), ("pothole road", 0.82))
    assert res_short == "Potholes / Damaged Roads"


def test_t4_2_resolve_conflict_rule():
    """T4.2: resolve(('Garbage', 0.70), ('Pothole', 0.85)) follows Decision 3 rule (high confidence text wins)."""
    # Case A: Text >= 0.80 while Image < 0.80 -> Text wins
    detail_a = resolve_detailed(("Garbage Accumulation", 0.70), ("Potholes / Damaged Roads", 0.85))
    assert detail_a["final_category"] == "Potholes / Damaged Roads"
    assert "Text classifier is highly confident" in detail_a["reason"]
    assert detail_a["agreed"] is False

    # Case B: Image >= 0.80 while Text < 0.80 -> Image wins
    detail_b = resolve_detailed(("Potholes / Damaged Roads", 0.92), ("Garbage Accumulation", 0.65))
    assert detail_b["final_category"] == "Potholes / Damaged Roads"
    assert "Image classifier is highly confident" in detail_b["reason"]

    # Case C: Image margin > 0.15 -> Image wins
    detail_c = resolve_detailed(("Garbage Accumulation", 0.75), ("Streetlight Faults", 0.55))
    assert detail_c["final_category"] == "Garbage Accumulation"

    # Case D: Both uncertain / close -> Default to text as tiebreaker
    detail_d = resolve_detailed(("Garbage Accumulation", 0.60), ("Waterlogging / Drainage Problems", 0.58))
    assert detail_d["final_category"] == "Waterlogging / Drainage Problems"
    assert "tiebreaker" in detail_d["reason"]


def test_t4_3_resolution_logging(caplog):
    """T4.3: Resolution logs source confidences and decision reason."""
    import logging
    with caplog.at_level(logging.INFO):
        resolve_detailed(("Potholes / Damaged Roads", 0.88), ("Garbage Accumulation", 0.60))
    assert any("Resolved Category" in record.message for record in caplog.records)


def test_t4_4_text_cue_high_severity():
    """T4.4: Description with 'deep pothole, accident' + category Pothole -> text_cue = 2."""
    score, cues = score_text_cues(
        "There was a terrible vehicle accident caused by a deep pothole on the road",
        "Potholes / Damaged Roads",
    )
    assert score == 2
    assert "accident" in cues or "deep" in cues


def test_t4_5_text_cue_zero_default():
    """T4.5: Description with no severity keywords -> text_cue = 0."""
    score, cues = score_text_cues(
        "Reporting issue near the corner of park street",
        "Potholes / Damaged Roads",
    )
    assert score == 0
    assert len(cues) == 0


def test_t4_6_citizen_severity_mapping():
    """T4.6: Citizen severity: Minor -> 0, Moderate -> 1, Severe -> 2."""
    assert CITIZEN_SEVERITY_POINTS["Minor"] == 0
    assert CITIZEN_SEVERITY_POINTS["Moderate"] == 1
    assert CITIZEN_SEVERITY_POINTS["Severe"] == 2


def test_t4_7_image_cue_pothole_affected_area():
    """T4.7: Image cue on Pothole image with large affected area -> image_cue = 1."""
    # Create a synthetic pothole test image with > 15% dark cavity
    test_img = np.full((224, 224, 3), 100, dtype=np.uint8)
    cv2.circle(test_img, (112, 112), 65, (10, 10, 10), -1)  # Area = pi * 65^2 ~ 13,273 / 50,176 ~ 26%

    test_path = BASE_DIR / "data" / "large_pothole_test.jpg"
    cv2.imwrite(str(test_path), test_img)

    try:
        score = score_image_cue(str(test_path), "Potholes / Damaged Roads")
        assert score == 1, f"Expected image cue score 1, got {score}"
    finally:
        if test_path.exists():
            test_path.unlink()


def test_t4_8_image_cue_category_restricted():
    """T4.8: Image cue on Waterlogging or Streetlight image -> image_cue = 0 (not applicable)."""
    # Even if an image has dark or contrasting pixels, waterlogging and streetlights must return 0
    sample_img = str(IMAGE_DIR / "waterlogging" / "waterlogging_001.jpg")
    score_water = score_image_cue(sample_img, "Waterlogging / Drainage Problems")
    assert score_water == 0

    sample_light = str(IMAGE_DIR / "streetlight" / "streetlight_001.jpg")
    score_light = score_image_cue(sample_light, "Streetlight Faults")
    assert score_light == 0


def test_t4_9_combined_high_severity():
    """T4.9: text_cue=2 + citizen=2 + image_cue=1 = 5 -> 'High'."""
    # "accident" (+2), Severe (+2), image heuristic (+1)
    test_img = np.full((224, 224, 3), 100, dtype=np.uint8)
    cv2.circle(test_img, (112, 112), 65, (10, 10, 10), -1)
    test_path = BASE_DIR / "data" / "test_sev_high.jpg"
    cv2.imwrite(str(test_path), test_img)

    try:
        res = assess_severity(
            description="Deep crater caused an accident and vehicle damage",
            category="Potholes / Damaged Roads",
            citizen_severity="Severe",
            image_path=str(test_path),
        )
        assert res["points"] >= 4
        assert res["severity"] == "High"
        assert res["text_cue"] == 2
        assert res["citizen"] == 2
        assert res["image_cue"] == 1
    finally:
        if test_path.exists():
            test_path.unlink()


def test_t4_10_combined_low_severity():
    """T4.10: text_cue=0 + citizen=0 + image_cue=0 = 0 -> 'Low'."""
    res = assess_severity(
        description="Just a normal spot on the lane",
        category="Potholes / Damaged Roads",
        citizen_severity="Minor",
        image_path=None,
    )
    assert res["points"] == 0
    assert res["severity"] == "Low"
    assert res["text_cue"] == 0
    assert res["citizen"] == 0
    assert res["image_cue"] == 0


def test_t4_11_combined_medium_severity():
    """T4.11: text_cue=1 + citizen=1 + image_cue=0 = 2 -> 'Medium'."""
    res = assess_severity(
        description="Potholes are growing and worsening along this path",  # medium cue = 1
        category="Potholes / Damaged Roads",
        citizen_severity="Moderate",  # citizen = 1
        image_path=None,  # image = 0
    )
    assert res["points"] == 2
    assert res["severity"] == "Medium"
    assert res["text_cue"] == 1
    assert res["citizen"] == 1
    assert res["image_cue"] == 0


def test_t4_12_and_t4_13_api_end_to_end_severity_pipeline():
    """
    T4.12: Submitting a complaint via API triggers ML pipeline and fills category, severity, severity_points in DB.
    T4.13: Severity breakdown JSON is stored in DB and returned by GET /api/complaints/{id}.
    """
    client = TestClient(app)

    # Use a real pothole image sample from our benchmark dataset
    pothole_sample = IMAGE_DIR / "potholes" / "potholes_001.jpg"
    assert pothole_sample.exists()

    with open(pothole_sample, "rb") as f:
        img_bytes = f.read()

    response = client.post(
        "/api/complaints",
        data={
            "description": "Massive deep pothole on main road causing fatal vehicle accident",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
        files={"image": ("test_pothole_sub.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )

    assert response.status_code == 201, response.text
    complaint_id = response.json()["id"]

    # Verify via GET /api/complaints/{id}
    detail_resp = client.get(f"/api/complaints/{complaint_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()

    # Category must be resolved (T4.12)
    assert data["category"] == "Potholes / Damaged Roads"
    assert data["severity"] in ["Medium", "High"]
    assert data["severity_points"] is not None
    assert data["severity_points"] >= 2

    # Severity factors breakdown must be present in response (T4.13)
    assert "priority_factors" in data
    factors = data["priority_factors"]
    assert "severity_breakdown" in factors
    sb = factors["severity_breakdown"]
    assert "text_cue" in sb
    assert "citizen" in sb
    assert "image_cue" in sb
    assert "points" in sb
    assert "resolution_data" in factors
