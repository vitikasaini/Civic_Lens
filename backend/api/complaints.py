"""
API route handlers for complaint submission, retrieval, and status management.
"""

import logging
import os
import uuid
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    BackgroundTasks,
    status,
)
from sqlalchemy.orm import Session
from sqlalchemy import desc, nullslast

from backend.models.database import get_db, BASE_DIR, SessionLocal
from backend.models.complaint import Complaint, StatusHistory
from backend.models.user import User, UserRole
from backend.models.notification import Notification
from backend.models.schemas import (
    ComplaintCreateResponse,
    ComplaintListItem,
    ComplaintDetail,
    StatusUpdateRequest,
)
from backend.api.dependencies import require_citizen, require_authority, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

# Upload directory configuration
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Valid citizen severity inputs
VALID_CITIZEN_SEVERITIES = {"Minor", "Moderate", "Severe"}

# Allowed status transitions: current_status -> set of allowable next statuses
VALID_STATUS_TRANSITIONS = {
    "Reported": {"In Progress"},
    "In Progress": {"Resolved"},
    "Resolved": set(),  # Terminal state
}

# Notification messages per status
NOTIFICATION_MESSAGES = {
    "In Progress": "Your complaint #{id} has been acknowledged. The authority has started working on your reported issue.",
    "Resolved": "Your complaint #{id} has been marked as resolved by the authority.",
    "Reported": "Your complaint #{id} is awaiting action from the authority.",
}


def get_utc_now():
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Reverse geocoding & Nearest Known Location Fallback
# ---------------------------------------------------------------------------

from backend.ml.priority import _SENSITIVE_LOCATIONS
from backend.ml.grouping import haversine_distance


def get_nearest_known_location(lat: float, lon: float) -> Optional[dict]:
    """Finds the closest sensitive location from sensitive_locations.json."""
    if not _SENSITIVE_LOCATIONS:
        return None
    return min(
        _SENSITIVE_LOCATIONS,
        key=lambda loc: haversine_distance(lat, lon, loc["latitude"], loc["longitude"]),
    )


def get_nearest_known_location_name(lat: float, lon: float) -> Optional[str]:
    """Returns the name of the closest sensitive location."""
    loc = get_nearest_known_location(lat, lon)
    return loc["name"] if loc else None


def resolve_complaint_address(address: Optional[str], lat: float, lon: float) -> str:
    """
    Returns an address string. If an exact address is not present,
    falls back to the nearest known location formatted as 'Near <location>'.
    """
    if address and address.strip() and address.strip().lower() != "address unavailable":
        return address.strip()
    nearest_name = get_nearest_known_location_name(lat, lon)
    if nearest_name:
        return f"Near {nearest_name}"
    return "Address unavailable"


async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """Calls OSM Nominatim to convert lat/lon to a human-readable address."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 0}
    headers = {"User-Agent": "CivicLens/1.0 (academic-project@example.com)"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("display_name")
    except Exception as exc:
        logger.warning(f"Reverse geocoding failed for ({lat},{lon}): {exc}")
        return None


async def reverse_geocode_and_update(complaint_id: int):
    """Background task: fetch address and update complaint row (never blocks submission)."""
    await asyncio.sleep(1)  # Respect 1 req/sec OSM limit
    db = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            osm_addr = await reverse_geocode(complaint.latitude, complaint.longitude)
            if osm_addr:
                complaint.address = osm_addr
            elif not complaint.address:
                complaint.address = resolve_complaint_address(None, complaint.latitude, complaint.longitude)
            db.add(complaint)
            db.commit()
    except Exception as exc:
        logger.warning(f"Background geocode update failed: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/my",
    response_model=List[ComplaintListItem],
    summary="List complaints submitted by the authenticated citizen",
)
def list_my_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_citizen),
):
    """Return only complaints owned by the logged-in citizen, newest first."""
    results = (
        db.query(Complaint)
        .filter(Complaint.citizen_id == current_user.id)
        .order_by(desc(Complaint.created_at))
        .all()
    )
    for c in results:
        if not c.address:
            c.address = resolve_complaint_address(c.address, c.latitude, c.longitude)
    return results


@router.post(
    "",
    response_model=ComplaintCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a citizen complaint",
)
async def create_complaint(
    background_tasks: BackgroundTasks,
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    citizen_severity: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_citizen),
):
    """
    Submits and validates a citizen complaint with an uploaded image.
    Requires authentication as a citizen.
    """
    # 1. Validate text fields
    clean_desc = description.strip()
    if not clean_desc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Description cannot be empty.",
        )
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Latitude must be between -90 and 90. Got: {latitude}",
        )
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Longitude must be between -180 and 180. Got: {longitude}",
        )
    clean_severity = citizen_severity.strip().capitalize()
    if clean_severity not in VALID_CITIZEN_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid severity '{citizen_severity}'. Must be one of: {sorted(VALID_CITIZEN_SEVERITIES)}",
        )

    # 2. Validate uploaded file
    if not image.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="An image file is required.")
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format '{file_ext}'. Allowed: {sorted(allowed_extensions)}",
        )
    image.file.seek(0, 2)
    file_size = image.file.tell()
    image.file.seek(0)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image exceeds 10MB ({file_size/(1024*1024):.2f}MB).",
        )

    # 3. Save file to disk
    unique_filename = f"{uuid.uuid4().hex[:12]}_{Path(image.filename).name}"
    target_filepath = UPLOAD_DIR / unique_filename
    try:
        with target_filepath.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save image: {str(exc)}",
        )
    relative_image_path = f"uploads/{unique_filename}"

    # 4. AI/ML Processing Pipeline
    try:
        from backend.ml.image_classifier import predict as predict_image
        img_prediction = predict_image(str(target_filepath))
    except Exception:
        img_prediction = ("Unknown", 0.0)

    try:
        from backend.ml.text_classifier import predict as predict_text
        txt_prediction = predict_text(clean_desc)
    except Exception:
        txt_prediction = ("Unknown", 0.0)

    from backend.ml.category_resolver import resolve_detailed
    resolution = resolve_detailed(img_prediction, txt_prediction)
    resolved_category = resolution["final_category"]

    from backend.ml.severity import assess_severity
    severity_breakdown = assess_severity(
        description=clean_desc,
        category=resolved_category,
        citizen_severity=clean_severity,
        image_path=str(target_filepath),
    )

    # 5. Save complaint record
    now = get_utc_now()
    initial_address = resolve_complaint_address(None, latitude, longitude)
    new_complaint = Complaint(
        description=clean_desc,
        image_path=relative_image_path,
        latitude=latitude,
        longitude=longitude,
        address=initial_address,
        citizen_severity=clean_severity,
        category=resolved_category,
        severity=severity_breakdown["severity"],
        severity_points=severity_breakdown["points"],
        priority_factors={
            "severity_breakdown": severity_breakdown,
            "resolution_data": resolution,
        },
        status="Reported",
        similar_count=0,
        created_at=now,
        updated_at=now,
        citizen_id=current_user.id,
    )
    db.add(new_complaint)
    db.flush()

    # 6. Record initial status history
    initial_history = StatusHistory(
        complaint_id=new_complaint.id,
        old_status=None,
        new_status="Reported",
        changed_at=now,
    )
    db.add(initial_history)
    db.commit()

    # 7. Recompute grouping and priority
    try:
        from backend.ml.grouping import recompute_all_groups
        from backend.ml.priority import recalculate_all_priorities
        recompute_all_groups(db)
        recalculate_all_priorities(db)
    except Exception as exc:
        logger.warning(f"Error recomputing groups/priorities: {exc}")

    db.refresh(new_complaint)

    # 8. Schedule reverse geocoding in background
    background_tasks.add_task(reverse_geocode_and_update, new_complaint.id)

    return ComplaintCreateResponse(
        id=new_complaint.id,
        status=new_complaint.status,
        message="Complaint submitted successfully.",
        image_path=new_complaint.image_path,
        created_at=new_complaint.created_at,
    )


@router.get(
    "",
    response_model=List[ComplaintListItem],
    summary="List complaints with optional filtering and sorting (authority only)",
)
def list_complaints(
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    sort: Optional[str] = Query("priority"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authority),
):
    """Returns filtered and sorted list of complaints for the authority dashboard."""
    query = db.query(Complaint)

    if category:
        query = query.filter(Complaint.category == category)
    if severity:
        query = query.filter(Complaint.severity == severity)
    if status:
        query = query.filter(Complaint.status == status)
    if priority:
        p_tier = priority.strip().capitalize()
        if p_tier == "High":
            query = query.filter(Complaint.priority_score >= 0.70)
        elif p_tier == "Medium":
            query = query.filter(Complaint.priority_score >= 0.40, Complaint.priority_score < 0.70)
        elif p_tier == "Low":
            query = query.filter(Complaint.priority_score < 0.40)

    if sort == "date":
        query = query.order_by(desc(Complaint.created_at))
    else:
        query = query.order_by(nullslast(desc(Complaint.priority_score)), desc(Complaint.created_at))

    complaints = query.all()
    for c in complaints:
        if not c.address:
            c.address = resolve_complaint_address(c.address, c.latitude, c.longitude)
    return complaints


@router.get(
    "/{complaint_id}",
    response_model=ComplaintDetail,
    summary="Get full complaint detail with factors and history",
)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full complaint details including status transition history.
    Citizens can only view their own complaints; authorities can view any.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found.",
        )
    if current_user.role == UserRole.CITIZEN:
        if complaint.citizen_id is not None and complaint.citizen_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to other citizen's complaint.",
            )
    if not complaint.address:
        complaint.address = resolve_complaint_address(complaint.address, complaint.latitude, complaint.longitude)
    return complaint


@router.get(
    "/{complaint_id}/similar",
    response_model=List[ComplaintListItem],
    summary="Get similar and duplicate complaints in the same group",
)
def get_similar_complaints(complaint_id: int, db: Session = Depends(get_db)):
    """Returns list of complaints in the same group (excluding self)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found.",
        )
    if complaint.group_id is None:
        return []
    similar = (
        db.query(Complaint)
        .filter(Complaint.group_id == complaint.group_id, Complaint.id != complaint.id)
        .order_by(desc(Complaint.created_at))
        .all()
    )
    for c in similar:
        if not c.address:
            c.address = resolve_complaint_address(c.address, c.latitude, c.longitude)
    return similar


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintDetail,
    summary="Update complaint status with lifecycle validation (authority only)",
)
def update_complaint_status(
    complaint_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authority),
):
    """
    Transitions a complaint through the workflow: Reported -> In Progress -> Resolved.
    Rejects invalid transitions with 400. Sends notification to owning citizen.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found.",
        )

    current_status_val = complaint.status
    target_status = payload.new_status

    if current_status_val == target_status:
        return complaint

    allowed_targets = VALID_STATUS_TRANSITIONS.get(current_status_val, set())
    if target_status not in allowed_targets:
        allowed_msg = (
            f"Allowed next: {', '.join(sorted(allowed_targets))}"
            if allowed_targets
            else f"Status '{current_status_val}' is terminal."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current_status_val}' to '{target_status}'. {allowed_msg}",
        )

    now = get_utc_now()
    # Record in history
    history_entry = StatusHistory(
        complaint_id=complaint.id,
        old_status=current_status_val,
        new_status=target_status,
        changed_at=now,
    )
    db.add(history_entry)

    # Update complaint
    complaint.status = target_status
    complaint.updated_at = now

    # Create notification for owning citizen (if any)
    if complaint.citizen_id:
        msg_template = NOTIFICATION_MESSAGES.get(
            target_status,
            f"Your complaint #{{id}} status changed to {target_status}."
        )
        message = msg_template.format(id=complaint.id)
        notif = Notification(
            user_id=complaint.citizen_id,
            complaint_id=complaint.id,
            message=message,
            is_read=False,
        )
        db.add(notif)

    db.commit()
    db.refresh(complaint)
    return complaint
