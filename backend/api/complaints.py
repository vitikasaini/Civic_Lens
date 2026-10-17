"""
API route handlers for complaint submission, retrieval, and status management.
"""

import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    status,
)
from sqlalchemy.orm import Session
from sqlalchemy import desc, nullslast

from backend.models.database import get_db, BASE_DIR
from backend.models.complaint import Complaint, StatusHistory
from backend.models.schemas import (
    ComplaintCreateResponse,
    ComplaintListItem,
    ComplaintDetail,
    StatusUpdateRequest,
)

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
    "Resolved": set(),  # Terminal state for V1.0
}


def get_utc_now():
    return datetime.now(timezone.utc)


@router.post(
    "",
    response_model=ComplaintCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a citizen complaint",
)
async def create_complaint(
    description: str = Form(..., description="Description of the civic issue"),
    latitude: float = Form(..., description="GPS Latitude (-90 to 90)"),
    longitude: float = Form(..., description="GPS Longitude (-180 to 180)"),
    citizen_severity: str = Form(..., description="Citizen-reported severity: Minor, Moderate, or Severe"),
    image: UploadFile = File(..., description="Image file illustrating the issue"),
    db: Session = Depends(get_db),
):
    """
    Submits and validates a citizen complaint with an uploaded image.
    Stores record in database and saves the image to disk.
    """
    # 1. Validate text fields
    clean_desc = description.strip()
    if not clean_desc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Description cannot be empty or only whitespace.",
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
            detail=f"Invalid citizen_severity: '{citizen_severity}'. Must be one of: {sorted(VALID_CITIZEN_SEVERITIES)}",
        )

    # 2. Validate uploaded file
    if not image.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An image file is required.",
        )

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {sorted(allowed_extensions)}",
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
            detail=f"Failed to save uploaded image: {str(exc)}",
        )

    # Store relative path for portability across environments
    relative_image_path = f"uploads/{unique_filename}"

    # 4. Save complaint record in SQLite DB
    now = get_utc_now()
    new_complaint = Complaint(
        description=clean_desc,
        image_path=relative_image_path,
        latitude=latitude,
        longitude=longitude,
        citizen_severity=clean_severity,
        status="Reported",
        similar_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(new_complaint)
    db.flush()  # populate new_complaint.id

    # 5. Record initial status in status_history
    initial_history = StatusHistory(
        complaint_id=new_complaint.id,
        old_status=None,
        new_status="Reported",
        changed_at=now,
    )
    db.add(initial_history)
    db.commit()
    db.refresh(new_complaint)

    return ComplaintCreateResponse(
        id=new_complaint.id,
        status=new_complaint.status,
        message="Complaint submitted and stored successfully.",
        image_path=new_complaint.image_path,
        created_at=new_complaint.created_at,
    )


@router.get(
    "",
    response_model=List[ComplaintListItem],
    summary="List complaints with optional filtering and sorting",
)
def list_complaints(
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[str] = Query(None, description="Filter by severity (Low, Medium, High)"),
    status: Optional[str] = Query(None, description="Filter by status (Reported, In Progress, Resolved)"),
    priority: Optional[str] = Query(None, description="Filter by priority tier (High, Medium, Low)"),
    sort: Optional[str] = Query("priority", description="Sort by: 'priority' (descending) or 'date' (descending)"),
    db: Session = Depends(get_db),
):
    """
    Returns filtered and sorted list of complaints for the dashboard and citizen lists.
    """
    query = db.query(Complaint)

    if category:
        query = query.filter(Complaint.category == category)
    if severity:
        query = query.filter(Complaint.severity == severity)
    if status:
        query = query.filter(Complaint.status == status)

    if priority:
        # Priority tiers based on priority_score (0.0 - 1.0)
        p_tier = priority.strip().capitalize()
        if p_tier == "High":
            query = query.filter(Complaint.priority_score >= 0.70)
        elif p_tier == "Medium":
            query = query.filter(Complaint.priority_score >= 0.40, Complaint.priority_score < 0.70)
        elif p_tier == "Low":
            query = query.filter(Complaint.priority_score < 0.40)

    # Sorting
    if sort == "date":
        query = query.order_by(desc(Complaint.created_at))
    else:  # default to priority descending (nulls last)
        query = query.order_by(nullslast(desc(Complaint.priority_score)), desc(Complaint.created_at))

    return query.all()


@router.get(
    "/{complaint_id}",
    response_model=ComplaintDetail,
    summary="Get full complaint detail with factors and history",
)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    """
    Returns full complaint details including status transition history and priority breakdown.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found.",
        )
    return complaint


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintDetail,
    summary="Update complaint status with lifecycle validation",
)
def update_complaint_status(
    complaint_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Transitions a complaint through the workflow: Reported -> In Progress -> Resolved.
    Rejects invalid transitions with 400 Bad Request.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID {complaint_id} not found.",
        )

    current_status = complaint.status
    target_status = payload.new_status

    if current_status == target_status:
        return complaint  # No-op if already in target status

    allowed_targets = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_targets:
        allowed_msg = (
            f"Allowed next status from '{current_status}': {', '.join(sorted(allowed_targets))}"
            if allowed_targets
            else f"Status '{current_status}' is terminal; cannot transition further."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition from '{current_status}' to '{target_status}'. "
                f"Valid workflow is Reported -> In Progress -> Resolved. {allowed_msg}"
            ),
        )

    now = get_utc_now()
    # Record in history
    history_entry = StatusHistory(
        complaint_id=complaint.id,
        old_status=current_status,
        new_status=target_status,
        changed_at=now,
    )
    db.add(history_entry)

    # Update complaint
    complaint.status = target_status
    complaint.updated_at = now
    db.commit()
    db.refresh(complaint)

    return complaint
