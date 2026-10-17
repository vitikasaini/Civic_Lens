"""
SQLAlchemy ORM models for CivicLens.
Defines complaints and status_history tables.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from backend.models.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Complaint(Base):
    """
    Core complaint model.
    Stores citizen report, ML predictions, severity scoring, priority calculation,
    and workflow status.
    """
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    description = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # ML & Resolution Fields (nullable initially, populated during processing)
    category = Column(String(100), nullable=True)  # Potholes, Garbage, Waterlogging, Streetlight
    citizen_severity = Column(String(20), nullable=False)  # Minor, Moderate, Severe
    severity = Column(String(20), nullable=True)  # Low, Medium, High (computed)
    severity_points = Column(Integer, nullable=True)

    # Explainable Priority Fields
    priority_score = Column(Float, nullable=True)
    priority_factors = Column(JSON, nullable=True)  # Contributing factor breakdown

    # Grouping / Duplicate Info
    group_id = Column(Integer, nullable=True, index=True)
    similar_count = Column(Integer, default=0, nullable=False)

    # Workflow Status: Reported -> In Progress -> Resolved
    status = Column(String(50), default="Reported", nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationship to history
    status_history = relationship(
        "StatusHistory",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at.asc()",
    )


class StatusHistory(Base):
    """
    Audit log of complaint status transitions.
    """
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    complaint = relationship("Complaint", back_populates="status_history")
