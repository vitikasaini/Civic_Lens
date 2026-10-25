"""
Phase 5 Verification Tests: Duplicate and Nearby Complaint Grouping.

Tests cover:
- T5.1: Haversine distance formula accuracy (within 1m of geodetic reference).
- T5.2: DBSCAN clusters 3 complaints within 200m into 1 cluster.
- T5.3: DBSCAN separates complaints 5km apart.
- T5.4: Text cosine similarity exceeds threshold for near-duplicate descriptions.
- T5.5: Text cosine similarity stays below threshold for unrelated descriptions.
- T5.6: Combined grouping: same category + nearby/similar -> grouped together.
- T5.7: Combined grouping: same location but different category -> NOT grouped.
- T5.8: similar_count reflects accurate count (group_size - 1).
- T5.9: GET /api/complaints/{id}/similar returns related group members.
- T5.10: API submission triggers automatic re-grouping of nearby complaints.
"""

import io
import math
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import SessionLocal, init_db, engine, Base
from backend.models.complaint import Complaint
from backend.ml.grouping import (
    haversine_distance,
    compute_text_similarity,
    cluster_coordinates_dbscan,
    group_complaints_data,
    recompute_all_groups,
    DEFAULT_EPS_METERS,
    DEFAULT_TEXT_SIMILARITY_THRESHOLD,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_SAMPLE = BASE_DIR / "data" / "images" / "potholes" / "potholes_001.jpg"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    # Cleanup complaints and history created during tests
    with SessionLocal() as db:
        db.query(Complaint).delete()
        db.commit()


def test_t5_1_haversine_accuracy():
    """T5.1: Haversine distance between two known coordinates matches expected value within 1m."""
    # Connaught Place (28.6315, 77.2167) to India Gate (28.6129, 77.2295)
    # Geodesic haversine analytical distance = 2416.29 meters
    cp_lat, cp_lon = 28.6315, 77.2167
    ig_lat, ig_lon = 28.6129, 77.2295
    dist = haversine_distance(cp_lat, cp_lon, ig_lat, ig_lon)
    assert abs(dist - 2416.29) < 1.0, f"Expected ~2416.29m, got {dist}m"

    # Equator 1-degree longitude difference: 6371000 * radians(1.0) = 111194.92m
    eq_dist = haversine_distance(0.0, 0.0, 0.0, 1.0)
    expected_eq = 6371000.0 * math.radians(1.0)
    assert abs(eq_dist - expected_eq) < 1.0, f"Expected {expected_eq}m, got {eq_dist}m"


def test_t5_2_dbscan_nearby_clustering():
    """T5.2: DBSCAN clusters 3 complaints within 200m of each other into 1 group."""
    # 3 points in Connaught Place outer circle, pairwise ~60m to 150m apart
    coords = [
        (28.6315, 77.2167),
        (28.6320, 77.2172),
        (28.6318, 77.2160),
    ]
    labels = cluster_coordinates_dbscan(coords, eps_meters=500.0, min_samples=2)
    assert len(labels) == 3
    # All three should be in the same non-noise cluster
    assert labels[0] >= 0
    assert labels[0] == labels[1] == labels[2]


def test_t5_3_dbscan_distant_separation():
    """T5.3: DBSCAN keeps 2 complaints 5km apart in separate groups."""
    coords = [
        (28.6315, 77.2167),  # Connaught Place
        (28.6800, 77.2500),  # > 5.5km away
    ]
    labels = cluster_coordinates_dbscan(coords, eps_meters=500.0, min_samples=2)
    assert len(labels) == 2
    # Because min_samples=2 and distance > 500m, neither forms a cluster (both noise -1)
    # or they have different cluster IDs
    assert labels[0] == -1
    assert labels[1] == -1


def test_t5_4_text_similarity_high_for_near_duplicates():
    """T5.4: Text similarity: two nearly identical descriptions -> similarity > threshold."""
    desc1 = "Huge deep pothole on main road causing accidents"
    desc2 = "Huge deep pothole on the main road causing fatal accidents"
    sim = compute_text_similarity(desc1, desc2)
    assert sim > DEFAULT_TEXT_SIMILARITY_THRESHOLD, f"Expected > {DEFAULT_TEXT_SIMILARITY_THRESHOLD}, got {sim}"


def test_t5_5_text_similarity_low_for_unrelated():
    """T5.5: Text similarity: unrelated descriptions -> similarity < threshold."""
    desc1 = "Pothole on the road"
    desc2 = "Garbage overflowing and smelling terrible"
    sim = compute_text_similarity(desc1, desc2)
    assert sim < DEFAULT_TEXT_SIMILARITY_THRESHOLD, f"Expected < {DEFAULT_TEXT_SIMILARITY_THRESHOLD}, got {sim}"


def test_t5_6_combined_grouping_same_category_nearby():
    """T5.6: Combined grouping: same category + nearby + similar text -> grouped."""
    complaints = [
        {
            "id": 101,
            "category": "Potholes / Damaged Roads",
            "latitude": 28.6315,
            "longitude": 77.2167,
            "description": "Deep pothole on main carriageway",
        },
        {
            "id": 102,
            "category": "Potholes / Damaged Roads",
            "latitude": 28.6320,  # ~70m away
            "longitude": 77.2170,
            "description": "Dangerous pothole near the crossing",
        },
    ]
    res = group_complaints_data(complaints, eps_meters=500.0)
    assert res[101]["group_id"] is not None
    assert res[101]["group_id"] == res[102]["group_id"]
    assert res[101]["similar_count"] == 1
    assert res[102]["similar_count"] == 1


def test_t5_7_combined_grouping_different_category_not_grouped():
    """T5.7: Combined grouping: same location but different category -> NOT grouped."""
    complaints = [
        {
            "id": 201,
            "category": "Potholes / Damaged Roads",
            "latitude": 28.6315,
            "longitude": 77.2167,
            "description": "Deep pothole near pole",
        },
        {
            "id": 202,
            "category": "Streetlight Faults",
            "latitude": 28.6315,  # Exactly the same location
            "longitude": 77.2167,
            "description": "Streetlight not working on this pole",
        },
    ]
    res = group_complaints_data(complaints, eps_meters=500.0)
    # Neither should be grouped because categories differ
    assert res[201]["group_id"] is None
    assert res[202]["group_id"] is None
    assert res[201]["similar_count"] == 0
    assert res[202]["similar_count"] == 0


def test_t5_8_similar_count_reflects_group_size():
    """T5.8: similar_count for a grouped complaint reflects correct count (group_size - 1)."""
    complaints = [
        {"id": 1, "category": "Garbage Accumulation", "latitude": 28.5000, "longitude": 77.1000, "description": "Garbage pile"},
        {"id": 2, "category": "Garbage Accumulation", "latitude": 28.5005, "longitude": 77.1005, "description": "Trash overflowing"},
        {"id": 3, "category": "Garbage Accumulation", "latitude": 28.5002, "longitude": 77.1002, "description": "Waste on street"},
    ]
    res = group_complaints_data(complaints, eps_meters=500.0)
    assert res[1]["group_id"] == res[2]["group_id"] == res[3]["group_id"]
    # 3 in cluster -> each has 2 similar complaints
    assert res[1]["similar_count"] == 2
    assert res[2]["similar_count"] == 2
    assert res[3]["similar_count"] == 2


def test_t5_9_get_similar_api_endpoint():
    """T5.9: GET /api/complaints/{id}/similar returns correct related complaints."""
    client = TestClient(app)

    # Insert two complaints directly into DB with same group
    with SessionLocal() as db:
        c1 = Complaint(
            description="First pothole report",
            image_path="uploads/test1.jpg",
            latitude=28.6139,
            longitude=77.2090,
            citizen_severity="Moderate",
            category="Potholes / Damaged Roads",
            severity="Medium",
            severity_points=2,
            status="Reported",
        )
        c2 = Complaint(
            description="Second pothole nearby",
            image_path="uploads/test2.jpg",
            latitude=28.6142,
            longitude=77.2092,
            citizen_severity="Moderate",
            category="Potholes / Damaged Roads",
            severity="Medium",
            severity_points=2,
            status="Reported",
        )
        db.add_all([c1, c2])
        db.commit()
        db.refresh(c1)
        db.refresh(c2)
        c1_id = c1.id
        c2_id = c2.id

    # Recompute groups
    with SessionLocal() as db:
        recompute_all_groups(db)

    # Query similar for c1
    resp1 = client.get(f"/api/complaints/{c1_id}/similar")
    assert resp1.status_code == 200
    similar_list = resp1.json()
    assert len(similar_list) == 1
    assert similar_list[0]["id"] == c2_id

    # Query similar for c2
    resp2 = client.get(f"/api/complaints/{c2_id}/similar")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["id"] == c1_id


def test_t5_10_api_submission_triggers_regrouping():
    """T5.10: Submitting a new complaint near existing ones triggers automatic re-grouping."""
    client = TestClient(app)

    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    # Submit first complaint
    resp1 = client.post(
        "/api/complaints",
        data={
            "description": "Massive deep pothole on outer ring road near junction",
            "latitude": "28.6315",
            "longitude": "77.2167",
            "citizen_severity": "Moderate",
        },
        files={"image": ("c1.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    # Verify first complaint initially has similar_count == 0
    detail1_before = client.get(f"/api/complaints/{id1}").json()
    assert detail1_before["similar_count"] == 0

    # Submit second complaint 80m away with same category
    resp2 = client.post(
        "/api/complaints",
        data={
            "description": "Another deep pothole right next to the previous one on outer ring road",
            "latitude": "28.6320",
            "longitude": "77.2170",
            "citizen_severity": "Severe",
        },
        files={"image": ("c2.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    # Both complaints should now be grouped with similar_count == 1
    detail1_after = client.get(f"/api/complaints/{id1}").json()
    detail2 = client.get(f"/api/complaints/{id2}").json()

    assert detail1_after["group_id"] is not None
    assert detail1_after["group_id"] == detail2["group_id"]
    assert detail1_after["similar_count"] == 1
    assert detail2["similar_count"] == 1
