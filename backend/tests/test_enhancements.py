"""
Verification tests for CivicLens V1.0 Enhancements:
- Authentication & RBAC (Citizen vs Authority)
- Complaint ownership and /my endpoint
- Cross-citizen access protection (403)
- Status update and Notification generation
- Notification read-tracking
- Reverse geocoding (mocked HTTP)
"""

import io
import time
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import SessionLocal, init_db
from backend.models.user import User, UserRole
from backend.api.auth import get_password_hash, create_access_token


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


def create_dummy_png():
    """Generates a minimal 1x1 valid PNG."""
    return io.BytesIO(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_auth_registration_and_login(client):
    """Citizen registration creates citizen user and login returns valid JWT."""
    unique_suffix = int(time.time() * 1000)
    email = f"citizen_reg_{unique_suffix}@civiclens.local"
    password = "SecretPassword123"

    # Register
    reg_resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["token_type"] == "bearer"

    # Duplicate registration rejected
    dup_resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert dup_resp.status_code == 400

    # Login
    login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data

    # Verify user role in DB is CITIZEN
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.role == UserRole.CITIZEN


def test_authority_rbac_and_protection(client):
    """Citizens are blocked from authority endpoints with 403."""
    with SessionLocal() as db:
        c_user = db.query(User).filter(User.email == "citizen_rbac@test.com").first()
        if not c_user:
            c_user = User(
                email="citizen_rbac@test.com",
                hashed_password=get_password_hash("pass"),
                role=UserRole.CITIZEN,
            )
            db.add(c_user)
            db.commit()
            db.refresh(c_user)
        c_id = c_user.id

        a_user = db.query(User).filter(User.email == "authority_rbac@test.com").first()
        if not a_user:
            a_user = User(
                email="authority_rbac@test.com",
                hashed_password=get_password_hash("pass"),
                role=UserRole.AUTHORITY,
            )
            db.add(a_user)
            db.commit()
            db.refresh(a_user)
        a_id = a_user.id

    c_token = create_access_token({"sub": str(c_id), "role": "citizen"})
    a_token = create_access_token({"sub": str(a_id), "role": "authority"})

    # Citizen accessing authority dashboard summary -> 403
    resp_c_dash = client.get(
        "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {c_token}"},
    )
    assert resp_c_dash.status_code == 403

    # Authority accessing authority dashboard summary -> 200
    resp_a_dash = client.get(
        "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert resp_a_dash.status_code == 200

    # Citizen accessing all complaints list -> 403
    resp_c_all = client.get(
        "/api/complaints",
        headers={"Authorization": f"Bearer {c_token}"},
    )
    assert resp_c_all.status_code == 403

    # Authority accessing all complaints list -> 200
    resp_a_all = client.get(
        "/api/complaints",
        headers={"Authorization": f"Bearer {a_token}"},
    )
    assert resp_a_all.status_code == 200


def test_complaint_ownership_and_cross_citizen_isolation(client):
    """Complaints link to submitter; citizens see only own; cross-citizen access returns 403."""
    with SessionLocal() as db:
        u1 = db.query(User).filter(User.email == "citizen_u1@test.com").first()
        if not u1:
            u1 = User(email="citizen_u1@test.com", hashed_password=get_password_hash("p"), role=UserRole.CITIZEN)
            db.add(u1)
            db.commit()
            db.refresh(u1)
        u1_id = u1.id

        u2 = db.query(User).filter(User.email == "citizen_u2@test.com").first()
        if not u2:
            u2 = User(email="citizen_u2@test.com", hashed_password=get_password_hash("p"), role=UserRole.CITIZEN)
            db.add(u2)
            db.commit()
            db.refresh(u2)
        u2_id = u2.id

    t1 = create_access_token({"sub": str(u1_id), "role": "citizen"})
    t2 = create_access_token({"sub": str(u2_id), "role": "citizen"})

    # U1 submits complaint
    resp = client.post(
        "/api/complaints",
        headers={"Authorization": f"Bearer {t1}"},
        data={
            "description": "Garbage issue for ownership test",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Moderate",
        },
        files={"image": ("test.png", create_dummy_png(), "image/png")},
    )
    assert resp.status_code == 201
    c_id = resp.json()["id"]

    # Verify U1 sees it in /my
    my_resp = client.get("/api/complaints/my", headers={"Authorization": f"Bearer {t1}"})
    assert my_resp.status_code == 200
    ids_u1 = [c["id"] for c in my_resp.json()]
    assert c_id in ids_u1

    # Verify U2 does NOT see it in /my
    my_resp_u2 = client.get("/api/complaints/my", headers={"Authorization": f"Bearer {t2}"})
    assert my_resp_u2.status_code == 200
    ids_u2 = [c["id"] for c in my_resp_u2.json()]
    assert c_id not in ids_u2

    # U1 can view detail
    d1 = client.get(f"/api/complaints/{c_id}", headers={"Authorization": f"Bearer {t1}"})
    assert d1.status_code == 200

    # U2 attempting to view U1's detail gets 403 Forbidden
    d2 = client.get(f"/api/complaints/{c_id}", headers={"Authorization": f"Bearer {t2}"})
    assert d2.status_code == 403


def test_status_update_creates_notification_and_mark_read(client):
    """Authority status transition creates notification for owning citizen; read-tracking works."""
    with SessionLocal() as db:
        citizen = db.query(User).filter(User.email == "notif_citizen@test.com").first()
        if not citizen:
            citizen = User(email="notif_citizen@test.com", hashed_password=get_password_hash("p"), role=UserRole.CITIZEN)
            db.add(citizen)
            db.commit()
            db.refresh(citizen)
        c_id = citizen.id

        authority = db.query(User).filter(User.email == "notif_authority@test.com").first()
        if not authority:
            authority = User(email="notif_authority@test.com", hashed_password=get_password_hash("p"), role=UserRole.AUTHORITY)
            db.add(authority)
            db.commit()
            db.refresh(authority)
        a_id = authority.id

    c_token = create_access_token({"sub": str(c_id), "role": "citizen"})
    a_token = create_access_token({"sub": str(a_id), "role": "authority"})

    # Citizen submits complaint
    sub_resp = client.post(
        "/api/complaints",
        headers={"Authorization": f"Bearer {c_token}"},
        data={
            "description": "Streetlight failure notification test",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
        files={"image": ("light.png", create_dummy_png(), "image/png")},
    )
    cid = sub_resp.json()["id"]

    # Authority transitions status to "In Progress"
    up_resp = client.patch(
        f"/api/complaints/{cid}/status",
        headers={"Authorization": f"Bearer {a_token}"},
        json={"new_status": "In Progress"},
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["status"] == "In Progress"

    # Citizen checks notifications
    notif_resp = client.get("/api/notifications", headers={"Authorization": f"Bearer {c_token}"})
    assert notif_resp.status_code == 200
    n_data = notif_resp.json()
    assert n_data["unread_count"] >= 1
    found = [n for n in n_data["notifications"] if n["complaint_id"] == cid]
    assert len(found) > 0
    notif_item = found[0]
    assert "In Progress" in notif_item["message"] or "acknowledged" in notif_item["message"]
    assert notif_item["is_read"] is False

    # Citizen marks notification as read
    read_resp = client.patch(
        f"/api/notifications/{notif_item['id']}/read",
        headers={"Authorization": f"Bearer {c_token}"},
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True


def test_reverse_geocoding_success_and_failure_resilience():
    """Reverse geocoding resolves addresses cleanly and gracefully handles network failure."""
    import asyncio
    from backend.api.complaints import reverse_geocode

    # Mock success
    class MockSuccessResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"display_name": "Connaught Place, New Delhi, India"}

    with patch("httpx.AsyncClient.get", return_value=MockSuccessResponse()):
        res = asyncio.run(reverse_geocode(28.6329, 77.2195))
        assert res == "Connaught Place, New Delhi, India"

    # Mock network error -> returns None without crash
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection timeout")):
        res_fail = asyncio.run(reverse_geocode(28.6329, 77.2195))
        assert res_fail is None


def test_nearest_known_location_fallback():
    """If exact address is not present, falls back to nearest known location as 'Near <xyz>'."""
    from backend.api.complaints import (
        get_nearest_known_location_name,
        resolve_complaint_address,
    )

    # Coords close to City General Hospital (28.6139, 77.2090)
    loc_hospital = get_nearest_known_location_name(28.6140, 77.2091)
    assert loc_hospital == "City General Hospital"
    assert resolve_complaint_address(None, 28.6140, 77.2091) == "Near City General Hospital"

    # Coords close to Central Public School (28.6329, 77.2195)
    assert resolve_complaint_address("", 28.6330, 77.2196) == "Near Central Public School"

    # Coords with 'Address unavailable'
    assert resolve_complaint_address("Address unavailable", 28.6440, 77.2167) == "Near Main Bus Terminal"

    # Present exact address is preserved
    assert resolve_complaint_address("123 Civil Lines, New Delhi", 28.6140, 77.2091) == "123 Civil Lines, New Delhi"


def test_login_role_mode_enforcement(client):
    """Wrong-mode login rejection and correct-mode success for both Citizen and Authority."""
    unique_suffix = int(time.time() * 1000)
    c_email = f"citizen_mode_{unique_suffix}@civiclens.local"
    a_email = f"auth_mode_{unique_suffix}@civiclens.local"
    pwd = "ValidPassword123"

    with SessionLocal() as db:
        c_user = User(email=c_email, hashed_password=get_password_hash(pwd), role=UserRole.CITIZEN)
        a_user = User(email=a_email, hashed_password=get_password_hash(pwd), role=UserRole.AUTHORITY)
        db.add_all([c_user, a_user])
        db.commit()

    # 1. Citizen account logging in via Citizen mode -> SUCCESS (200)
    res_c_ok = client.post("/api/auth/login", json={"email": c_email, "password": pwd, "role": "citizen"})
    assert res_c_ok.status_code == 200
    assert "access_token" in res_c_ok.json()

    # 2. Citizen account logging in via Authority mode -> REJECTED (403)
    res_c_wrong = client.post("/api/auth/login", json={"email": c_email, "password": pwd, "role": "authority"})
    assert res_c_wrong.status_code == 403
    assert res_c_wrong.json()["detail"] == "This account is not an Authority account"

    # 3. Authority account logging in via Authority mode -> SUCCESS (200)
    res_a_ok = client.post("/api/auth/login", json={"email": a_email, "password": pwd, "role": "authority"})
    assert res_a_ok.status_code == 200
    assert "access_token" in res_a_ok.json()

    # 4. Authority account logging in via Citizen mode -> REJECTED (403)
    res_a_wrong = client.post("/api/auth/login", json={"email": a_email, "password": pwd, "role": "citizen"})
    assert res_a_wrong.status_code == 403
    assert res_a_wrong.json()["detail"] == "Please use Authority Login"

