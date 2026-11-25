"""
End-to-end integration verification script for CivicLens V1.0.
Verifies full user flow: citizen registration, complaint submission,
ownership isolation, authority management, status transitions, notifications,
and timeline updates.
"""

import os
import sys
import io
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient

os.environ["AUTHORITY_EMAIL"] = "admin_e2e@civiclens.local"
os.environ["AUTHORITY_PASSWORD"] = "AdminPass123!"
os.environ["STRICT_AUTH_TEST"] = "1"

from backend.main import app
from backend.models.database import init_db

init_db()

with TestClient(app) as client:
    print("[1] Health check & SPA serving...")
    h = client.get("/health")
    assert h.status_code == 200, f"Health check failed: {h.text}"
    assert h.json()["status"] == "healthy"

    spa = client.get("/app")
    assert spa.status_code == 200
    assert "text/html" in spa.headers.get("content-type", "")

    spa_c = client.get("/citizen")
    assert spa_c.status_code == 200
    print("    SPA and /health routes OK")

    print("[2] Citizen Registration & Login...")
    c_email = f"citizen_e2e_{int(time.time())}@civiclens.local"
    c_pwd = "CitizenPass123!"
    reg_res = client.post("/api/auth/register", json={"email": c_email, "password": c_pwd})
    assert reg_res.status_code == 201, reg_res.text
    c_token = reg_res.json()["access_token"]
    c_headers = {"Authorization": f"Bearer {c_token}"}
    print(f"    Citizen registered: {c_email}")

    print("[3] Submitting complaint as citizen...")
    dummy_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    sub_res = client.post(
        "/api/complaints",
        headers=c_headers,
        data={
            "description": "Massive pothole on Main Street near roundabout",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "citizen_severity": "Severe",
        },
        files={"image": ("pothole.png", io.BytesIO(dummy_png), "image/png")},
    )
    assert sub_res.status_code == 201, sub_res.text
    cid = sub_res.json()["id"]
    print(f"    Complaint #{cid} created successfully")

    print("[4] Checking My Complaints (/api/complaints/my)...")
    my_res = client.get("/api/complaints/my", headers=c_headers)
    assert my_res.status_code == 200
    my_list = my_res.json()
    assert any(c["id"] == cid for c in my_list), f"Complaint #{cid} missing from My Complaints"
    print(f"    Complaint #{cid} present in citizen's My Complaints list")

    print("[5] Testing RBAC: Citizen blocked from authority routes...")
    dash_res = client.get("/api/dashboard/summary", headers=c_headers)
    assert dash_res.status_code == 403, f"Expected 403 on dashboard summary, got {dash_res.status_code}"
    all_res = client.get("/api/complaints", headers=c_headers)
    assert all_res.status_code == 403, f"Expected 403 on all complaints, got {all_res.status_code}"
    print("    Citizen correctly blocked with 403 Forbidden on Authority endpoints")

    print("[6] Authority Login & Role Mode Enforcement...")
    # Citizen trying authority login mode -> rejected
    c_wrong_res = client.post(
        "/api/auth/login",
        json={"email": c_email, "password": c_pwd, "role": "authority"},
    )
    assert c_wrong_res.status_code == 403
    assert c_wrong_res.json()["detail"] == "This account is not an Authority account"
    print("    Citizen rejected on Authority mode login (403)")

    # Authority trying citizen login mode -> rejected
    a_wrong_res = client.post(
        "/api/auth/login",
        json={"email": "admin_e2e@civiclens.local", "password": "AdminPass123!", "role": "citizen"},
    )
    assert a_wrong_res.status_code == 403
    assert a_wrong_res.json()["detail"] == "Please use Authority Login"
    print("    Authority rejected on Citizen mode login (403)")

    # Authority logs in using Authority mode
    auth_res = client.post(
        "/api/auth/login",
        json={"email": "admin_e2e@civiclens.local", "password": "AdminPass123!", "role": "authority"},
    )
    assert auth_res.status_code == 200, f"Authority login failed: {auth_res.text}"
    a_token = auth_res.json()["access_token"]
    a_headers = {"Authorization": f"Bearer {a_token}"}
    print("    Authority successfully authenticated in Authority mode")

    summary_res = client.get("/api/dashboard/summary", headers=a_headers)
    assert summary_res.status_code == 200
    s_data = summary_res.json()
    print(f"    Authority Dashboard KPI: Total={s_data['total']}, Pending={s_data['pending']}")

    comps_res = client.get("/api/complaints", headers=a_headers)
    assert comps_res.status_code == 200
    comp_obj = next((c for c in comps_res.json() if c["id"] == cid), None)
    assert comp_obj is not None
    print(f"    Authority views complaint #{cid} with location: ({comp_obj['latitude']}, {comp_obj['longitude']}), address={comp_obj.get('address')}")

    print("[7] Authority transitions complaint status: Reported -> In Progress...")
    patch_res = client.patch(
        f"/api/complaints/{cid}/status",
        headers=a_headers,
        json={"new_status": "In Progress"},
    )
    assert patch_res.status_code == 200, patch_res.text
    assert patch_res.json()["status"] == "In Progress"
    print(f"    Complaint #{cid} successfully updated to 'In Progress'")

    print("[8] Citizen verifies in-app Notification...")
    notif_res = client.get("/api/notifications", headers=c_headers)
    assert notif_res.status_code == 200
    n_data = notif_res.json()
    assert n_data["unread_count"] >= 1
    target_notif = next(n for n in n_data["notifications"] if n["complaint_id"] == cid)
    assert target_notif["is_read"] is False
    print(f"    Citizen received notification: '{target_notif['message']}' (Unread: {n_data['unread_count']})")

    # Mark as read
    read_res = client.patch(f"/api/notifications/{target_notif['id']}/read", headers=c_headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    notif_res2 = client.get("/api/notifications", headers=c_headers)
    assert notif_res2.json()["unread_count"] == n_data["unread_count"] - 1
    print(f"    Notification #{target_notif['id']} marked as read. Unread count lowered by 1.")

    print("[9] Citizen checks complaint timeline & StatusHistory...")
    detail_res = client.get(f"/api/complaints/{cid}", headers=c_headers)
    assert detail_res.status_code == 200
    d_data = detail_res.json()
    history_statuses = [h["new_status"] for h in d_data["status_history"]]
    assert "Reported" in history_statuses
    assert "In Progress" in history_statuses
    print(f"    StatusHistory verified: {history_statuses}")

print("\n============================================================")
print("SUCCESS: Full End-to-End CivicLens workflow verified cleanly!")
print("============================================================")
