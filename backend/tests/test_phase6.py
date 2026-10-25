"""
Phase 6 Verification Tests: Explainable Priority Engine.

Tests cover:
- T6.1: Severity normalization: Low -> 0.33, Medium -> 0.67, High -> 1.00.
- T6.2: Similar-complaint count normalization: 0 -> 0.0, cap (10) -> 1.0, >10 -> 1.0.
- T6.3: Location importance: within 200m of sensitive location -> 1.00; outside -> 0.50.
- T6.4: Time normalization: 0 days -> 0.0, 30 days -> 1.0, >30 days -> 1.0.
- T6.5: Formula calculation: hand-verified benchmark matches output.
- T6.6: Factor breakdown structure contains {value, normalized, weight, contribution} for all 4 factors.
- T6.7: Comparative ordering: high-severity/urgent complaint outranks low-urgency complaint.
- T6.8: GET /api/complaints?sort=priority returns complaints in strictly descending priority score order.
- T6.9: GET /api/complaints/{id} returns rich explainable contributing factor breakdown.
- T6.10: Adding a new complaint near an existing one triggers automatic re-grouping and priority boost.
"""

import io
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import SessionLocal, init_db
from backend.models.complaint import Complaint
from backend.ml.priority import (
    normalize_severity,
    normalize_similar_count,
    normalize_location,
    normalize_time,
    calculate_priority,
    recalculate_all_priorities,
    WEIGHT_SEVERITY,
    WEIGHT_SIMILAR,
    WEIGHT_LOCATION,
    WEIGHT_TIME,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_SAMPLE = BASE_DIR / "data" / "images" / "potholes" / "potholes_001.jpg"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    with SessionLocal() as db:
        db.query(Complaint).delete()
        db.commit()


def test_t6_1_severity_normalization():
    """T6.1: Severity normalization maps Low -> 0.33, Medium -> 0.67, High -> 1.0."""
    norm_low, _ = normalize_severity("Low")
    norm_med, _ = normalize_severity("Medium")
    norm_high, _ = normalize_severity("High")

    assert norm_low == 0.33
    assert norm_med == 0.67
    assert norm_high == 1.00


def test_t6_2_similar_count_normalization():
    """T6.2: Similar complaints normalization: 0 -> 0.0, 5 -> 0.5, 10 -> 1.0, 15 -> 1.0."""
    assert normalize_similar_count(0)[0] == 0.0
    assert normalize_similar_count(5)[0] == 0.5
    assert normalize_similar_count(10)[0] == 1.0
    assert normalize_similar_count(15)[0] == 1.0  # Capped at 1.0


def test_t6_3_location_importance_lookup():
    """T6.3: Location importance: complaint at/near known sensitive location -> 1.0, elsewhere -> 0.5."""
    # City General Hospital is at (28.6139, 77.2090)
    score_sensitive, label_sens, name = normalize_location(28.6139, 77.2090)
    assert score_sensitive == 1.00
    assert label_sens == "Sensitive"
    assert name == "City General Hospital"

    # Location in open rural coordinates far away from any sensitive location
    score_std, label_std, name_std = normalize_location(28.1000, 76.5000)
    assert score_std == 0.50
    assert label_std == "Standard"
    assert name_std is None


def test_t6_4_time_normalization():
    """T6.4: Time normalization: 0 days -> 0.0, 15 days -> 0.5, 30 days -> 1.0."""
    now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)

    # 0 days elapsed
    norm_0, _, _ = normalize_time(now, now=now)
    assert norm_0 == 0.0

    # 15 days elapsed
    t_15 = now - timedelta(days=15)
    norm_15, _, _ = normalize_time(t_15, now=now)
    assert norm_15 == 0.5

    # 30 days elapsed
    t_30 = now - timedelta(days=30)
    norm_30, _, _ = normalize_time(t_30, now=now)
    assert norm_30 == 1.0

    # 45 days elapsed (capped at 1.0)
    t_45 = now - timedelta(days=45)
    norm_45, _, _ = normalize_time(t_45, now=now)
    assert norm_45 == 1.0


def test_t6_5_formula_hand_calculation():
    """
    T6.5: Verify calculation matches hand-calculated benchmark:
    Severity: High (1.00) * 0.40 = 0.40
    Similar: 8 (0.80) * 0.25 = 0.20
    Location: Sensitive (1.00) * 0.20 = 0.20
    Time: 10 days (10/30 = 0.3333) * 0.15 = 0.05
    Total Expected = 0.40 + 0.20 + 0.20 + 0.05 = 0.8500
    """
    now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    created_at = now - timedelta(days=10)

    res = calculate_priority(
        severity="High",
        similar_count=8,
        latitude=28.6139,  # Hospital location
        longitude=77.2090,
        created_at=created_at,
        now=now,
    )
    assert abs(res["score"] - 0.8500) < 0.001
    assert res["severity"]["contribution"] == 0.40
    assert res["similar"]["contribution"] == 0.20
    assert res["location"]["contribution"] == 0.20
    assert abs(res["time"]["contribution"] - 0.05) < 0.001


def test_t6_6_priority_factors_structure():
    """T6.6: Priority factors JSON contains all 4 factors with value, normalized, weight, contribution."""
    now = datetime.now(timezone.utc)
    res = calculate_priority(
        severity="Medium",
        similar_count=2,
        latitude=28.6315,
        longitude=77.2167,
        created_at=now,
        now=now,
    )
    for factor in ["severity", "similar", "location", "time"]:
        assert factor in res
        item = res[factor]
        assert "value" in item
        assert "normalized" in item
        assert "weight" in item
        assert "contribution" in item


def test_t6_7_comparative_ordering():
    """T6.7: High severity + 8 similar + sensitive + 10 days outranks Low + 0 similar + standard + 1 day."""
    now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)

    urgent = calculate_priority(
        severity="High",
        similar_count=8,
        latitude=28.6139,
        longitude=77.2090,
        created_at=now - timedelta(days=10),
        now=now,
    )

    mild = calculate_priority(
        severity="Low",
        similar_count=0,
        latitude=28.1000,
        longitude=76.5000,
        created_at=now - timedelta(days=1),
        now=now,
    )

    assert urgent["score"] > mild["score"]
    assert urgent["score"] > 0.80
    assert mild["score"] < 0.30


def test_t6_8_api_sorting_by_priority():
    """T6.8: GET /api/complaints?sort=priority returns complaints in descending priority order."""
    client = TestClient(app)

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        c_low = Complaint(
            description="Minor crack on path",
            image_path="uploads/low.jpg",
            latitude=28.1000,
            longitude=76.5000,
            citizen_severity="Minor",
            severity="Low",
            priority_score=0.25,
            created_at=now,
        )
        c_high = Complaint(
            description="Dangerous collapse on main route",
            image_path="uploads/high.jpg",
            latitude=28.6139,
            longitude=77.2090,
            citizen_severity="Severe",
            severity="High",
            priority_score=0.88,
            created_at=now,
        )
        c_mid = Complaint(
            description="Medium pothole in colony",
            image_path="uploads/mid.jpg",
            latitude=28.6300,
            longitude=77.2100,
            citizen_severity="Moderate",
            severity="Medium",
            priority_score=0.55,
            created_at=now,
        )
        db.add_all([c_low, c_high, c_mid])
        db.commit()

    resp = client.get("/api/complaints?sort=priority")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    scores = [item["priority_score"] for item in items]
    assert scores == [0.88, 0.55, 0.25]


def test_t6_9_dashboard_detail_contributing_factors():
    """T6.9: GET /api/complaints/{id} exposes rich explainable factor breakdown."""
    client = TestClient(app)

    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    resp = client.post(
        "/api/complaints",
        data={
            "description": "Severe deep pothole causing fatal accidents right near City General Hospital entrance",
            "latitude": "28.6139",  # City General Hospital location
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
        files={"image": ("hosp_pothole.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    detail = client.get(f"/api/complaints/{cid}").json()
    assert detail["priority_score"] is not None
    assert detail["priority_score"] > 0.0

    factors = detail["priority_factors"]
    assert "priority_breakdown" in factors
    pb = factors["priority_breakdown"]
    assert pb["severity"]["value"] in ["Medium", "High"]
    assert pb["location"]["value"] == "Sensitive"
    assert pb["location"]["matched_location"] == "City General Hospital"
    assert pb["score"] == detail["priority_score"]


def test_t6_10_new_similar_complaint_updates_existing_priority():
    """T6.10: Adding a new complaint near an existing one boosts similar_count and priority of existing complaint."""
    client = TestClient(app)

    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    # 1. Post initial complaint
    resp1 = client.post(
        "/api/complaints",
        data={
            "description": "Isolated pothole on residential road",
            "latitude": "28.5500",
            "longitude": "77.1500",
            "citizen_severity": "Moderate",
        },
        files={"image": ("c1.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    cid1 = resp1.json()["id"]

    detail1_before = client.get(f"/api/complaints/{cid1}").json()
    p_score_before = detail1_before["priority_score"]
    assert detail1_before["similar_count"] == 0

    # 2. Post second complaint 50m away in the same category
    resp2 = client.post(
        "/api/complaints",
        data={
            "description": "Another pothole right next to the previous one on residential road",
            "latitude": "28.5503",
            "longitude": "77.1503",
            "citizen_severity": "Moderate",
        },
        files={"image": ("c2.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp2.status_code == 201

    # 3. Verify complaint 1 priority score increased due to similar_count rising from 0 to 1
    detail1_after = client.get(f"/api/complaints/{cid1}").json()
    assert detail1_after["similar_count"] == 1
    p_score_after = detail1_after["priority_score"]

    # Since similar factor weight is 0.25 and normalized rose from 0.0 to 0.1, score should rise by +0.025
    assert p_score_after > p_score_before
