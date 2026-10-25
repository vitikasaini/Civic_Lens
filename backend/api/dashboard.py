"""
Dashboard summary API for authority overview metrics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from backend.models.database import get_db
from backend.models.complaint import Complaint
from backend.models.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get overview counts for authority dashboard",
)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns counts for total complaints, high-priority issues,
    and current status counts (pending/reported, in-progress, resolved).
    """
    total = db.query(func.count(Complaint.id)).scalar() or 0

    # High priority: priority_score >= 0.70 OR severity == "High"
    high_priority = (
        db.query(func.count(Complaint.id))
        .filter(or_(Complaint.priority_score >= 0.70, Complaint.severity == "High"))
        .scalar()
        or 0
    )

    pending = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.status == "Reported")
        .scalar()
        or 0
    )

    in_progress = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.status == "In Progress")
        .scalar()
        or 0
    )

    resolved = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.status == "Resolved")
        .scalar()
        or 0
    )

    return DashboardSummary(
        total=total,
        high_priority=high_priority,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        total_complaints=total,
        high_priority_complaints=high_priority,
        pending_complaints=pending,
        in_progress_complaints=in_progress,
        resolved_complaints=resolved,
    )
