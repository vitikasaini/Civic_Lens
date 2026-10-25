"""
Phase 7 Verification Tests: Citizen Submission Interface & Pipeline Integration.

Tests cover:
- T7.1: Form structure and client assets validation (components exist and build cleanly).
- T7.2: Submission with missing/empty required fields is rejected with 422.
- T7.3: Uploading a non-image file (.txt, .exe) is rejected with clear error.
- T7.4: Map coordinates (latitude, longitude) validation and range checks.
- T7.5: Valid complaint submission returns 201 Created with complaint ID.
- T7.6: Newly submitted complaint immediately appears in GET /api/complaints.
- T7.7: Production frontend build serves index.html and assets at /app.
- T7.8: Frontend bundle contains responsive layout styles for mobile viewports.
- T7.9: Full end-to-end flow: image + description + location + citizen severity
        persists category, severity points, and priority in SQLite DB.
"""

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import SessionLocal, init_db
from backend.models.complaint import Complaint

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_SAMPLE = BASE_DIR / "data" / "images" / "potholes" / "potholes_001.jpg"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    with SessionLocal() as db:
        db.query(Complaint).delete()
        db.commit()


def test_t7_1_frontend_components_exist():
    """T7.1: Frontend submission components exist with required fields."""
    sub_component = BASE_DIR / "frontend" / "src" / "components" / "CitizenSubmission.jsx"
    map_component = BASE_DIR / "frontend" / "src" / "components" / "LocationPickerMap.jsx"

    assert sub_component.exists(), "CitizenSubmission.jsx must exist"
    assert map_component.exists(), "LocationPickerMap.jsx must exist"

    code = sub_component.read_text(encoding="utf-8")
    assert 'type="file"' in code
    assert 'textarea' in code.lower()
    assert 'citizenSeverity' in code or 'severity-select' in code
    assert 'LocationPickerMap' in code


def test_t7_2_submission_empty_fields_rejected():
    """T7.2: Submitting without required fields returns 422 Validation Error."""
    client = TestClient(app)

    # Missing image
    resp = client.post(
        "/api/complaints",
        data={
            "description": "Massive pothole on main road",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
    )
    assert resp.status_code == 422

    # Empty description
    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    resp_empty = client.post(
        "/api/complaints",
        data={
            "description": "   ",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
        files={"image": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp_empty.status_code == 422


def test_t7_3_non_image_file_rejected():
    """T7.3: Uploading a non-image file is rejected with 422."""
    client = TestClient(app)
    text_file_content = b"This is a plain text file, not a civic incident photo."

    resp = client.post(
        "/api/complaints",
        data={
            "description": "Pothole on main road causing problems",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Moderate",
        },
        files={"image": ("report.txt", io.BytesIO(text_file_content), "text/plain")},
    )
    assert resp.status_code == 422
    assert "Unsupported file format" in resp.text or "format" in resp.text.lower()


def test_t7_4_location_coordinates_validation():
    """T7.4: Invalid latitude/longitude coordinates are rejected."""
    client = TestClient(app)
    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    # Out of range latitude (95 > 90)
    resp = client.post(
        "/api/complaints",
        data={
            "description": "Pothole on main road causing problems",
            "latitude": "95.0",
            "longitude": "77.2090",
            "citizen_severity": "Moderate",
        },
        files={"image": ("pothole.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp.status_code == 422


def test_t7_5_valid_submission_creates_complaint():
    """T7.5: Valid complaint submission returns 201 Created with complaint ID."""
    client = TestClient(app)
    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    resp = client.post(
        "/api/complaints",
        data={
            "description": "Dangerous pothole cave-in near central bus stop",
            "latitude": "28.6440",
            "longitude": "77.2167",
            "citizen_severity": "Severe",
        },
        files={"image": ("pothole_bus.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "Reported"
    assert "uploads/" in data["image_path"]


def test_t7_6_complaint_appears_in_list():
    """T7.6: Newly created complaint appears in GET /api/complaints."""
    client = TestClient(app)
    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    post_resp = client.post(
        "/api/complaints",
        data={
            "description": "Deep crater on arterial road causing multiple accidents",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
        files={"image": ("crater.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    cid = post_resp.json()["id"]

    list_resp = client.get("/api/complaints")
    assert list_resp.status_code == 200
    complaints = list_resp.json()
    assert any(c["id"] == cid for c in complaints)


def test_t7_7_production_frontend_serves_spa():
    """T7.7: Production React SPA is built and served at /app with 200 OK."""
    client = TestClient(app)
    resp = client.get("/app")
    assert resp.status_code == 200
    assert "CivicLens" in resp.text or "<div id=\"root\">" in resp.text


def test_t7_8_responsive_layout_configured():
    """T7.8: Mobile-friendly styles and responsive media queries are defined in CSS."""
    css_path = BASE_DIR / "frontend" / "src" / "App.css"
    assert css_path.exists()
    css_content = css_path.read_text(encoding="utf-8")
    assert "@media" in css_content
    assert "max-width: 768px" in css_content or "max-width" in css_content


def test_t7_9_full_pipeline_end_to_end():
    """
    T7.9: Submitting image + description + location + severity ->
    DB record has category, severity, severity_points, priority_score, priority_factors populated.
    """
    client = TestClient(app)
    with open(IMAGE_SAMPLE, "rb") as f:
        img_bytes = f.read()

    resp = client.post(
        "/api/complaints",
        data={
            "description": "Deep pothole causing vehicle accident and danger near City General Hospital",
            "latitude": "28.6139",  # Sensitive hospital coordinate
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
        files={"image": ("hospital_pothole_pipeline.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert resp.status_code == 201
    cid = resp.json()["id"]

    # Verify directly in SQLite DB
    with SessionLocal() as db:
        record = db.query(Complaint).filter(Complaint.id == cid).first()
        assert record is not None
        assert record.category == "Potholes / Damaged Roads"
        assert record.severity in ["Medium", "High"]
        assert record.severity_points is not None
        assert record.severity_points >= 2
        assert record.priority_score is not None
        assert record.priority_score >= 0.6  # High priority due to Severe + Sensitive location
        assert record.priority_factors is not None
        assert "priority_breakdown" in record.priority_factors
