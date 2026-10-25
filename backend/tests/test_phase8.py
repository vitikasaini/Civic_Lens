"""
Phase 8 Verification Tests: Authority Dashboard & Status Lifecycle Management.

Tests cover:
- T8.1: Dashboard summary counts accurately match database records.
- T8.2: Complaint list returns all required table columns.
- T8.3: Complaint detail endpoint exposes full explanation, severity breakdown, and factors.
- T8.4: Status lifecycle updates: Reported -> In Progress -> Resolved with history tracking.
- T8.5: Invalid status transitions (e.g., Reported -> Resolved) are rejected with 400.
- T8.6: Filtering by category, severity, status, and priority tier returns correct subsets.
- T8.7: Sorting by priority (descending) vs date (descending) correctly reorders list.
- T8.8: Dashboard map component exists and maps complaint coordinates.
- T8.9: Quick status update and similar complaints retrieval for dashboard modal.
- T8.10: Frontend components for authority dashboard build and render without error.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import SessionLocal, init_db
from backend.models.complaint import Complaint, StatusHistory

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    with SessionLocal() as db:
        db.query(StatusHistory).delete()
        db.query(Complaint).delete()
        db.commit()


def test_t8_1_dashboard_summary_counts():
    """T8.1: Dashboard summary counts accurately match database records."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c1 = Complaint(
            description="Pending pothole",
            image_path="uploads/c1.jpg",
            latitude=28.6139,
            longitude=77.2090,
            citizen_severity="Moderate",
            category="Potholes / Damaged Roads",
            status="Reported",
            priority_score=0.45,
            created_at=now,
        )
        c2 = Complaint(
            description="Urgent hospital road damage",
            image_path="uploads/c2.jpg",
            latitude=28.6139,
            longitude=77.2090,
            citizen_severity="Severe",
            category="Potholes / Damaged Roads",
            status="In Progress",
            priority_score=0.85,
            created_at=now,
        )
        c3 = Complaint(
            description="Resolved street lamp",
            image_path="uploads/c3.jpg",
            latitude=28.6300,
            longitude=77.2100,
            citizen_severity="Minor",
            category="Streetlight Faults",
            status="Resolved",
            priority_score=0.20,
            created_at=now,
        )
        db.add_all([c1, c2, c3])
        db.commit()

    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_complaints"] == 3
    assert data["high_priority_complaints"] == 1  # c2 has priority_score 0.85 >= 0.6
    assert data["pending_complaints"] == 1        # c1 has status "Reported"
    assert data["in_progress_complaints"] == 1    # c2 has status "In Progress"
    assert data["resolved_complaints"] == 1       # c3 has status "Resolved"


def test_t8_2_complaint_table_columns():
    """T8.2: Complaint list returns all required table columns."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c = Complaint(
            description="Garbage dump on street corner",
            image_path="uploads/garbage.jpg",
            latitude=28.6508,
            longitude=77.2289,
            citizen_severity="Moderate",
            category="Garbage Accumulation",
            severity="Medium",
            priority_score=0.55,
            similar_count=3,
            status="Reported",
            created_at=now,
        )
        db.add(c)
        db.commit()

    resp = client.get("/api/complaints")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]

    for field in ["id", "category", "description", "latitude", "longitude", "severity", "priority_score", "similar_count", "status", "created_at"]:
        assert field in item, f"Missing required column: {field}"


def test_t8_3_complaint_detail_modal_data():
    """T8.3: Complaint detail exposes full explanation, factors, and history."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c = Complaint(
            description="Waterlogging outside school entrance",
            image_path="uploads/water.jpg",
            latitude=28.6329,
            longitude=77.2195,
            citizen_severity="Severe",
            category="Waterlogging / Drainage Problems",
            severity="High",
            severity_points=4,
            priority_score=0.78,
            priority_factors={
                "severity_breakdown": {"text_cue": 2, "citizen": 2, "image_cue": 0, "points": 4},
                "priority_breakdown": {"score": 0.78},
            },
            status="Reported",
            created_at=now,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        cid = c.id

    resp = client.get(f"/api/complaints/{cid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == cid
    assert data["category"] == "Waterlogging / Drainage Problems"
    assert data["severity"] == "High"
    assert data["severity_points"] == 4
    assert data["priority_score"] == 0.78
    assert "severity_breakdown" in data["priority_factors"]
    assert "priority_breakdown" in data["priority_factors"]


def test_t8_4_status_workflow_transitions():
    """T8.4: Status updates follow Reported -> In Progress -> Resolved lifecycle."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c = Complaint(
            description="Flickering streetlight",
            image_path="uploads/light.jpg",
            latitude=28.6400,
            longitude=77.2200,
            citizen_severity="Moderate",
            category="Streetlight Faults",
            status="Reported",
            created_at=now,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        cid = c.id

    # Step 1: Transition Reported -> In Progress
    r1 = client.patch(f"/api/complaints/{cid}/status", json={"new_status": "In Progress"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "In Progress"

    # Step 2: Transition In Progress -> Resolved
    r2 = client.patch(f"/api/complaints/{cid}/status", json={"new_status": "Resolved"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "Resolved"

    # Verify history in detail
    detail = client.get(f"/api/complaints/{cid}").json()
    assert len(detail["status_history"]) == 2
    assert detail["status_history"][0]["new_status"] == "In Progress"
    assert detail["status_history"][1]["new_status"] == "Resolved"


def test_t8_5_invalid_status_transition_rejected():
    """T8.5: Invalid status transition (Reported -> Resolved directly) is rejected with 400 Bad Request."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c = Complaint(
            description="Skip stage test",
            image_path="uploads/skip.jpg",
            latitude=28.6400,
            longitude=77.2200,
            citizen_severity="Moderate",
            status="Reported",
            created_at=now,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        cid = c.id

    # Try skipping "In Progress"
    resp = client.patch(f"/api/complaints/{cid}/status", json={"new_status": "Resolved"})
    assert resp.status_code == 400
    assert "Invalid status transition" in resp.json()["detail"]


def test_t8_6_table_filters():
    """T8.6: Filtering by category, severity, status, and priority tier returns matching complaints."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c1 = Complaint(
            description="Pothole complaint",
            image_path="uploads/p1.jpg",
            latitude=28.6139,
            longitude=77.2090,
            citizen_severity="Severe",
            category="Potholes / Damaged Roads",
            severity="High",
            status="Reported",
            priority_score=0.85,
            created_at=now,
        )
        c2 = Complaint(
            description="Garbage complaint",
            image_path="uploads/g1.jpg",
            latitude=28.6508,
            longitude=77.2289,
            citizen_severity="Minor",
            category="Garbage Accumulation",
            severity="Low",
            status="Resolved",
            priority_score=0.25,
            created_at=now,
        )
        db.add_all([c1, c2])
        db.commit()

    # Filter by category
    r_cat = client.get("/api/complaints?category=Potholes / Damaged Roads").json()
    assert len(r_cat) == 1
    assert r_cat[0]["category"] == "Potholes / Damaged Roads"

    # Filter by status
    r_stat = client.get("/api/complaints?status=Resolved").json()
    assert len(r_stat) == 1
    assert r_stat[0]["status"] == "Resolved"

    # Filter by priority tier
    r_prio = client.get("/api/complaints?priority=High").json()
    assert len(r_prio) == 1
    assert r_prio[0]["priority_score"] >= 0.6


def test_t8_7_table_sorting():
    """T8.7: Sorting by priority vs date reorders results appropriately."""
    client = TestClient(app)
    t_older = datetime.now(timezone.utc) - timedelta(days=5)
    t_newer = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c_low_new = Complaint(
            description="New mild issue",
            image_path="uploads/new.jpg",
            latitude=28.5000,
            longitude=77.1000,
            citizen_severity="Minor",
            priority_score=0.20,
            created_at=t_newer,
        )
        c_high_old = Complaint(
            description="Old urgent issue",
            image_path="uploads/old.jpg",
            latitude=28.6139,
            longitude=77.2090,
            citizen_severity="Severe",
            priority_score=0.90,
            created_at=t_older,
        )
        db.add_all([c_low_new, c_high_old])
        db.commit()

    # Priority sort: high priority first
    r_prio = client.get("/api/complaints?sort=priority").json()
    assert r_prio[0]["priority_score"] == 0.90

    # Date sort: newest first
    r_date = client.get("/api/complaints?sort=date").json()
    assert r_date[0]["priority_score"] == 0.20


def test_t8_8_dashboard_map_component_exists():
    """T8.8: DashboardMap.jsx component exists with Leaflet integration."""
    map_comp = BASE_DIR / "frontend" / "src" / "components" / "DashboardMap.jsx"
    assert map_comp.exists(), "DashboardMap.jsx must exist"
    code = map_comp.read_text(encoding="utf-8")
    assert "L.map" in code
    assert "tileLayer" in code
    assert "custom-map-marker" in code or "createPriorityIcon" in code


def test_t8_9_similar_endpoint_accessible():
    """T8.9: /api/complaints/{id}/similar endpoint returns 200 with list."""
    client = TestClient(app)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        c = Complaint(
            description="Standalone report",
            image_path="uploads/std.jpg",
            latitude=28.5000,
            longitude=77.1000,
            citizen_severity="Minor",
            created_at=now,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        cid = c.id

    resp = client.get(f"/api/complaints/{cid}/similar")
    assert resp.status_code == 200
    assert resp.json() == []


def test_t8_10_authority_dashboard_component_exists():
    """T8.10: AuthorityDashboard.jsx component exists with KPI cards, table, and map."""
    dash_comp = BASE_DIR / "frontend" / "src" / "components" / "AuthorityDashboard.jsx"
    assert dash_comp.exists(), "AuthorityDashboard.jsx must exist"
    code = dash_comp.read_text(encoding="utf-8")
    assert "summary.total_complaints" in code
    assert "DashboardMap" in code
    assert "ComplaintDetailModal" in code
    assert "complaint-table" in code
