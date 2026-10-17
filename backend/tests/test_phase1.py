"""
Phase 1 Verification Tests

Tests all 10 requirements from checklist.md:
- T1.1: DB init script idempotency
- T1.2: POST /api/complaints valid payload -> 201, stored in DB
- T1.3: POST /api/complaints missing required fields -> 422
- T1.4: Uploaded image saved to disk at returned path, valid image
- T1.5: GET /api/complaints list & filtering by status=Reported
- T1.6: GET /api/complaints/{id} full complaint detail with all fields
- T1.7: PATCH /api/complaints/{id}/status lifecycle Reported -> In Progress -> Resolved
- T1.8: PATCH /api/complaints/{id}/status invalid transition -> 400 with explanation
- T1.9: GET /api/dashboard/summary correct counts across statuses
- T1.10: SQLite DB portability (copying db file and querying matches)
"""

import os
import shutil
import sqlite3
import io
from pathlib import Path
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.models.database import Base, get_db, init_db, DEFAULT_DB_PATH
from backend.models.complaint import Complaint, StatusHistory
from backend.api.complaints import UPLOAD_DIR

# Use isolated test database for repeatable, clean tests
TEST_DB_PATH = Path(__file__).resolve().parent / "test_phase1.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    """Set up and tear down test database and override FastAPI get_db."""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    init_db(target_engine=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


@pytest.fixture
def client():
    return TestClient(app)


def create_dummy_image_bytes():
    """Creates a tiny 10x10 valid PNG in memory."""
    # 1x1 transparent PNG hex
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return io.BytesIO(png_bytes)


def test_t1_1_db_init_idempotent():
    """T1.1: Run DB init script twice — second run doesn't error or duplicate tables."""
    # First init already happened in fixture, run it again on the same engine
    init_db(target_engine=test_engine)
    init_db(target_engine=test_engine)

    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "complaints" in tables
    assert "status_history" in tables
    assert tables.count("complaints") == 1
    assert tables.count("status_history") == 1


def test_t1_2_post_complaint_valid(client):
    """T1.2: POST /api/complaints with valid payload -> 201, record exists in DB."""
    image_stream = create_dummy_image_bytes()
    response = client.post(
        "/api/complaints",
        data={
            "description": "Deep pothole causing vehicle damage near school gate",
            "latitude": "28.6329",
            "longitude": "77.2195",
            "citizen_severity": "Severe",
        },
        files={"image": ("test_pothole.png", image_stream, "image/png")},
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "id" in data
    assert data["status"] == "Reported"
    assert "uploads/" in data["image_path"]

    # Verify directly in DB
    db = TestingSessionLocal()
    complaint = db.query(Complaint).filter(Complaint.id == data["id"]).first()
    assert complaint is not None
    assert complaint.description == "Deep pothole causing vehicle damage near school gate"
    assert complaint.latitude == 28.6329
    assert complaint.longitude == 77.2195
    assert complaint.citizen_severity == "Severe"
    assert complaint.status == "Reported"
    db.close()


def test_t1_3_post_complaint_missing_required_fields(client):
    """T1.3: POST /api/complaints with missing required field -> 422."""
    image_stream = create_dummy_image_bytes()

    # Missing latitude & longitude
    response = client.post(
        "/api/complaints",
        data={
            "description": "Test complaint",
            "citizen_severity": "Minor",
        },
        files={"image": ("sample.png", image_stream, "image/png")},
    )
    assert response.status_code == 422

    # Missing image
    response_no_img = client.post(
        "/api/complaints",
        data={
            "description": "Test complaint",
            "latitude": "28.5",
            "longitude": "77.2",
            "citizen_severity": "Minor",
        },
    )
    assert response_no_img.status_code == 422

    # Invalid citizen severity value
    img2 = create_dummy_image_bytes()
    response_bad_sev = client.post(
        "/api/complaints",
        data={
            "description": "Test complaint",
            "latitude": "28.5",
            "longitude": "77.2",
            "citizen_severity": "Catastrophic",  # Invalid
        },
        files={"image": ("sample.png", img2, "image/png")},
    )
    assert response_bad_sev.status_code == 422


def test_t1_4_uploaded_image_saved_to_disk(client):
    """T1.4: Uploaded image is saved to disk at returned path and is a non-empty file."""
    image_stream = create_dummy_image_bytes()
    response = client.post(
        "/api/complaints",
        data={
            "description": "Garbage pile overflowing for three days",
            "latitude": "28.6508",
            "longitude": "77.2289",
            "citizen_severity": "Moderate",
        },
        files={"image": ("garbage_photo.png", image_stream, "image/png")},
    )
    assert response.status_code == 201
    img_rel_path = response.json()["image_path"]
    full_path = Path(__file__).resolve().parent.parent.parent / img_rel_path

    assert full_path.exists(), f"Image not found at {full_path}"
    assert full_path.stat().st_size > 0, "Saved image is 0 bytes"


def test_t1_5_get_complaints_filtering(client):
    """T1.5: GET /api/complaints returns correct list and filtering by status=Reported works."""
    response = client.get("/api/complaints?status=Reported")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 2
    for item in items:
        assert item["status"] == "Reported"


def test_t1_6_get_complaint_detail_with_all_fields(client):
    """T1.6: GET /api/complaints/{id} returns correct complaint with all fields."""
    # Retrieve complaint ID 1
    response = client.get("/api/complaints/1")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == 1
    assert "description" in data
    assert "image_path" in data
    assert "latitude" in data
    assert "longitude" in data
    assert "citizen_severity" in data
    assert "status" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "status_history" in data
    assert len(data["status_history"]) >= 1
    assert data["status_history"][0]["new_status"] == "Reported"

    # Non-existent complaint -> 404
    resp_404 = client.get("/api/complaints/99999")
    assert resp_404.status_code == 404


def test_t1_7_status_lifecycle_transitions(client):
    """T1.7: PATCH /api/complaints/{id}/status from Reported -> In Progress -> Resolved succeeds."""
    complaint_id = 1

    # Transition 1: Reported -> In Progress
    resp_prog = client.patch(
        f"/api/complaints/{complaint_id}/status",
        json={"new_status": "In Progress"},
    )
    assert resp_prog.status_code == 200
    data_prog = resp_prog.json()
    assert data_prog["status"] == "In Progress"

    # Transition 2: In Progress -> Resolved
    resp_res = client.patch(
        f"/api/complaints/{complaint_id}/status",
        json={"new_status": "Resolved"},
    )
    assert resp_res.status_code == 200
    data_res = resp_res.json()
    assert data_res["status"] == "Resolved"

    # Verify status history audit trail
    history = data_res["status_history"]
    assert len(history) == 3
    assert history[0]["new_status"] == "Reported"
    assert history[1]["old_status"] == "Reported" and history[1]["new_status"] == "In Progress"
    assert history[2]["old_status"] == "In Progress" and history[2]["new_status"] == "Resolved"


def test_t1_8_invalid_status_transition_rejected(client):
    """T1.8: PATCH /api/complaints/{id}/status with invalid transition -> 400 with explanation."""
    # Create fresh complaint (starts at Reported)
    img = create_dummy_image_bytes()
    resp_create = client.post(
        "/api/complaints",
        data={
            "description": "Streetlight dark for weeks",
            "latitude": "28.6280",
            "longitude": "77.2155",
            "citizen_severity": "Moderate",
        },
        files={"image": ("streetlight.png", img, "image/png")},
    )
    new_id = resp_create.json()["id"]

    # Attempt illegal skip: Reported -> Resolved
    resp_illegal = client.patch(
        f"/api/complaints/{new_id}/status",
        json={"new_status": "Resolved"},
    )
    assert resp_illegal.status_code == 400
    assert "Invalid status transition" in resp_illegal.json()["detail"]
    assert "In Progress" in resp_illegal.json()["detail"]


def test_t1_9_dashboard_summary_counts(client):
    """T1.9: GET /api/dashboard/summary returns correct counts for total, high_priority, and statuses."""
    db = TestingSessionLocal()

    # Clear and insert 5 known test complaints
    db.query(StatusHistory).delete()
    db.query(Complaint).delete()
    db.commit()

    test_data = [
        Complaint(
            description="Pothole 1",
            image_path="uploads/test1.png",
            latitude=28.1,
            longitude=77.1,
            citizen_severity="Severe",
            severity="High",
            priority_score=0.85,
            status="Reported",
        ),
        Complaint(
            description="Pothole 2",
            image_path="uploads/test2.png",
            latitude=28.2,
            longitude=77.2,
            citizen_severity="Minor",
            severity="Low",
            priority_score=0.30,
            status="Reported",
        ),
        Complaint(
            description="Garbage 1",
            image_path="uploads/test3.png",
            latitude=28.3,
            longitude=77.3,
            citizen_severity="Moderate",
            severity="Medium",
            priority_score=0.55,
            status="In Progress",
        ),
        Complaint(
            description="Garbage 2",
            image_path="uploads/test4.png",
            latitude=28.4,
            longitude=77.4,
            citizen_severity="Severe",
            severity="High",
            priority_score=0.75,
            status="In Progress",
        ),
        Complaint(
            description="Drainage 1",
            image_path="uploads/test5.png",
            latitude=28.5,
            longitude=77.5,
            citizen_severity="Minor",
            severity="Low",
            priority_score=0.25,
            status="Resolved",
        ),
    ]
    for c in test_data:
        db.add(c)
    db.commit()
    db.close()

    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    summary = resp.json()

    assert summary["total"] == 5
    assert summary["high_priority"] == 2  # Pothole 1 (0.85) and Garbage 2 (0.75)
    assert summary["pending"] == 2        # 2 in Reported
    assert summary["in_progress"] == 2    # 2 in In Progress
    assert summary["resolved"] == 1       # 1 in Resolved


def test_t1_10_sqlite_db_portability():
    """T1.10: SQLite DB file is portable — copy and open in a new connection shows correct data."""
    copy_path = TEST_DB_PATH.parent / "portable_copy.db"
    if copy_path.exists():
        copy_path.unlink()

    # Copy the SQLite file
    shutil.copyfile(TEST_DB_PATH, copy_path)
    assert copy_path.exists()

    # Query the copied file using raw sqlite3
    conn = sqlite3.connect(copy_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM complaints;")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT description, status FROM complaints LIMIT 1;")
    first_row = cursor.fetchone()
    conn.close()

    assert count == 5
    assert first_row is not None
    assert first_row[0] == "Pothole 1"
    assert first_row[1] == "Reported"

    # Cleanup copy
    copy_path.unlink()
