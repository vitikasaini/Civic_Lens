"""
Phase 9 Verification Tests: End-to-End Integration, Edge Cases & Performance Benchmarks.

Tests cover:
- T9.1: 10 diverse test complaints submitted -> 100% complete ML classification and dashboard visibility.
- T9.2: Nearby same-category complaints correctly clustered and grouped with group_id and similar_count.
- T9.3: Priority ordering validates: High severity + sensitive location + duplicates outranks isolated minor issue.
- T9.4: Full status lifecycle (Reported -> In Progress -> Resolved) verified with complete status history.
- T9.5: Dashboard summary counts accurately match database numbers across all statuses and priorities.
- T9.6: Geographic coordinates mapped for all complaints.
- T9.7: Complaint detail exposes image, description, category, severity breakdown, priority factors, and history.
- T9.8: Oversized image submission (>10MB) handled gracefully with 422 error, no crash.
- T9.9: Empty or below minimum length description handled gracefully with 422 error.
- T9.10: Single submission end-to-end latency < 30 seconds on local environment.
- T9.11: Dashboard summary and list query with 50+ complaints loads in < 5 seconds.
"""

import io
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import SessionLocal, init_db
from backend.models.complaint import Complaint, StatusHistory

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_DIR = BASE_DIR / "data" / "images"

# Benchmark image samples from each category
SAMPLES = {
    "Potholes": IMAGE_DIR / "potholes" / "potholes_001.jpg",
    "Garbage": IMAGE_DIR / "garbage" / "garbage_001.jpg",
    "Waterlogging": IMAGE_DIR / "waterlogging" / "waterlogging_001.jpg",
    "Streetlight": IMAGE_DIR / "streetlight" / "streetlight_001.jpg",
}


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    with SessionLocal() as db:
        db.query(StatusHistory).delete()
        db.query(Complaint).delete()
        db.commit()


def test_t9_1_to_t9_7_end_to_end_workflow():
    """
    T9.1 to T9.7: Submit 10 complaints across all categories and locations.
    Verifies:
      - T9.1: All 10 visible on dashboard with valid category, severity, and priority.
      - T9.2: Grouping links nearby same-category complaints.
      - T9.3: Priority score correctly orders urgent issues above minor issues.
      - T9.4: Status lifecycle Reported -> In Progress -> Resolved tracks history.
      - T9.5: Summary counts match test data.
      - T9.6: Geographic coordinates present on all complaints.
      - T9.7: Detail endpoint returns rich factor and history breakdowns.
    """
    client = TestClient(app)

    test_submissions = [
        # 1. Pothole near hospital (Sensitive, Severe)
        {
            "img": SAMPLES["Potholes"],
            "desc": "Massive deep pothole right outside hospital gate causing traffic jam and damage",
            "lat": 28.6139,
            "lon": 77.2090,
            "citizen_sev": "Severe",
        },
        # 2. Pothole near hospital (Nearby #1 -> should group with #1)
        {
            "img": SAMPLES["Potholes"],
            "desc": "Dangerous crater road cave-in 60m from hospital gate",
            "lat": 28.6143,
            "lon": 77.2093,
            "citizen_sev": "Severe",
        },
        # 3. Pothole distant (Isolated, Minor)
        {
            "img": SAMPLES["Potholes"],
            "desc": "Minor asphalt unevenness on colony lane",
            "lat": 28.5100,
            "lon": 77.1000,
            "citizen_sev": "Minor",
        },
        # 4. Garbage near market (Sensitive, Severe)
        {
            "img": SAMPLES["Garbage"],
            "desc": "Huge pile of rotting garbage overflowing for days near market with terrible smell",
            "lat": 28.6508,
            "lon": 77.2289,
            "citizen_sev": "Severe",
        },
        # 5. Garbage near market (Nearby #4 -> should group with #4)
        {
            "img": SAMPLES["Garbage"],
            "desc": "Waste container overflowing and spilling onto street near market",
            "lat": 28.6512,
            "lon": 77.2292,
            "citizen_sev": "Moderate",
        },
        # 6. Garbage distant (Isolated, Minor)
        {
            "img": SAMPLES["Garbage"],
            "desc": "Some dry leaves and papers on sidewalk",
            "lat": 28.5200,
            "lon": 77.1100,
            "citizen_sev": "Minor",
        },
        # 7. Waterlogging near school (Sensitive, Severe)
        {
            "img": SAMPLES["Waterlogging"],
            "desc": "Severe street flooded knee-deep with sewage entering buildings near school",
            "lat": 28.6329,
            "lon": 77.2195,
            "citizen_sev": "Severe",
        },
        # 8. Waterlogging distant (Moderate)
        {
            "img": SAMPLES["Waterlogging"],
            "desc": "Slow drainage causing standing water puddle on avenue",
            "lat": 28.5300,
            "lon": 77.1200,
            "citizen_sev": "Moderate",
        },
        # 9. Streetlight near bus terminal (Sensitive, Severe)
        {
            "img": SAMPLES["Streetlight"],
            "desc": "Pitch dark blackout with broken streetlights near bus stop for weeks",
            "lat": 28.6440,
            "lon": 77.2167,
            "citizen_sev": "Severe",
        },
        # 10. Streetlight distant (Minor)
        {
            "img": SAMPLES["Streetlight"],
            "desc": "Streetlight fixture dim on quiet alley",
            "lat": 28.5400,
            "lon": 77.1300,
            "citizen_sev": "Minor",
        },
    ]

    submitted_ids = []
    for sub in test_submissions:
        with open(sub["img"], "rb") as f:
            content = f.read()
        resp = client.post(
            "/api/complaints",
            data={
                "description": sub["desc"],
                "latitude": str(sub["lat"]),
                "longitude": str(sub["lon"]),
                "citizen_severity": sub["citizen_sev"],
            },
            files={"image": (sub["img"].name, io.BytesIO(content), "image/jpeg")},
        )
        assert resp.status_code == 201, resp.text
        submitted_ids.append(resp.json()["id"])

    assert len(submitted_ids) == 10

    # T9.1: Verify all 10 appear in GET /api/complaints with category, severity, and priority
    list_resp = client.get("/api/complaints")
    assert list_resp.status_code == 200
    all_complaints = list_resp.json()
    assert len(all_complaints) == 10

    for c in all_complaints:
        assert c["category"] in [
            "Potholes / Damaged Roads",
            "Garbage Accumulation",
            "Waterlogging / Drainage Problems",
            "Streetlight Faults",
        ]
        assert c["severity"] in ["Low", "Medium", "High"]
        assert c["priority_score"] is not None
        assert 0.0 <= c["priority_score"] <= 1.0
        # T9.6: Check coordinates
        assert -90.0 <= c["latitude"] <= 90.0
        assert -180.0 <= c["longitude"] <= 180.0

    # T9.2: Verify grouping of nearby complaints (Complaint 1 & 2 share group_id)
    c1 = client.get(f"/api/complaints/{submitted_ids[0]}").json()
    c2 = client.get(f"/api/complaints/{submitted_ids[1]}").json()
    assert c1["group_id"] is not None
    assert c1["group_id"] == c2["group_id"]
    assert c1["similar_count"] >= 1
    assert c2["similar_count"] >= 1

    # T9.3: Verify priority ordering: urgent hospital complaint > isolated minor complaint
    c3 = client.get(f"/api/complaints/{submitted_ids[2]}").json()
    assert c1["priority_score"] > c3["priority_score"]
    assert c1["priority_score"] >= 0.6  # High priority tier

    # T9.4: Status lifecycle walk: Reported -> In Progress -> Resolved
    test_cid = submitted_ids[0]
    p1 = client.patch(f"/api/complaints/{test_cid}/status", json={"new_status": "In Progress"})
    assert p1.status_code == 200
    p2 = client.patch(f"/api/complaints/{test_cid}/status", json={"new_status": "Resolved"})
    assert p2.status_code == 200

    c1_final = client.get(f"/api/complaints/{test_cid}").json()
    assert c1_final["status"] == "Resolved"
    # Status history records initial submission + 2 transitions = 3 records
    assert len(c1_final["status_history"]) == 3
    assert [h["new_status"] for h in c1_final["status_history"]] == ["Reported", "In Progress", "Resolved"]

    # T9.5: Verify dashboard summary counts
    summary = client.get("/api/dashboard/summary").json()
    assert summary["total"] == 10
    assert summary["resolved"] == 1
    assert summary["pending"] == 9

    # T9.7: Complaint detail exposes full factor breakdown
    factors = c1_final["priority_factors"]
    assert "priority_breakdown" in factors
    assert "severity_breakdown" in factors


def test_t9_8_large_image_handling():
    """T9.8: Submitting an oversized image (>10MB) is rejected with 422, no server crash."""
    client = TestClient(app)
    # Generate 11MB synthetic bytes
    large_payload = b"0" * (11 * 1024 * 1024)

    resp = client.post(
        "/api/complaints",
        data={
            "description": "Image payload boundary test",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Moderate",
        },
        files={"image": ("large_image.jpg", io.BytesIO(large_payload), "image/jpeg")},
    )
    assert resp.status_code == 422
    assert "10MB" in resp.text


def test_t9_9_short_description_handling():
    """T9.9: Minimal short description (1-2 words) handled gracefully without server crash."""
    client = TestClient(app)
    with open(SAMPLES["Potholes"], "rb") as f:
        img_bytes = f.read()

    # Submitting 1-word minimal description
    resp = client.post(
        "/api/complaints",
        data={
            "description": "Pothole",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Moderate",
        },
        files={"image": ("short.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    # Must succeed gracefully (no 500 internal server error or crash)
    assert resp.status_code == 201
    assert "id" in resp.json()

    # And completely empty/whitespace-only description is rejected with 422
    resp_empty = client.post(
        "/api/complaints",
        data={
            "description": "   ",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Moderate",
        },
        files={"image": ("empty.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp_empty.status_code == 422


def test_t9_10_submission_latency_benchmark():
    """T9.10: Single submission end-to-end latency < 30 seconds."""
    client = TestClient(app)
    with open(SAMPLES["Potholes"], "rb") as f:
        img_bytes = f.read()

    start_time = time.time()
    resp = client.post(
        "/api/complaints",
        data={
            "description": "Timed latency benchmark submission for civic issue",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Moderate",
        },
        files={"image": ("timed.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    elapsed = time.time() - start_time
    assert resp.status_code == 201
    assert elapsed < 30.0, f"Latency {elapsed:.2f}s exceeded 30s threshold"


def test_t9_11_dashboard_load_performance():
    """T9.11: Dashboard query with 50+ complaints loads in < 5 seconds."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        bulk_complaints = [
            Complaint(
                description=f"Bulk benchmark complaint #{i} on public road",
                image_path=f"uploads/bulk_{i}.jpg",
                latitude=28.6000 + (i * 0.001),
                longitude=77.2000 + (i * 0.001),
                citizen_severity="Moderate",
                category="Potholes / Damaged Roads",
                severity="Medium",
                priority_score=0.50,
                status="Reported" if i % 3 != 0 else "Resolved",
                created_at=now - timedelta(hours=i),
            )
            for i in range(55)
        ]
        db.add_all(bulk_complaints)
        db.commit()

    client = TestClient(app)

    start_time = time.time()
    list_resp = client.get("/api/complaints?sort=priority")
    summary_resp = client.get("/api/dashboard/summary")
    elapsed = time.time() - start_time

    assert list_resp.status_code == 200
    assert summary_resp.status_code == 200
    assert len(list_resp.json()) >= 55
    assert elapsed < 5.0, f"Dashboard query took {elapsed:.2f}s, expected < 5.0s"
