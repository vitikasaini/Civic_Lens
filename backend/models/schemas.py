"""
Pydantic schemas for request validation and response serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class StatusHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_at: datetime


class ComplaintCreateResponse(BaseModel):
    id: int
    status: str
    message: str
    image_path: str
    created_at: datetime


class ComplaintListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    image_path: str
    latitude: float
    longitude: float
    category: Optional[str] = None
    citizen_severity: str
    severity: Optional[str] = None
    priority_score: Optional[float] = None
    similar_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class ComplaintDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    image_path: str
    latitude: float
    longitude: float
    category: Optional[str] = None
    citizen_severity: str
    severity: Optional[str] = None
    severity_points: Optional[int] = None
    priority_score: Optional[float] = None
    priority_factors: Optional[Dict[str, Any]] = None
    group_id: Optional[int] = None
    similar_count: int
    status: str
    created_at: datetime
    updated_at: datetime
    status_history: List[StatusHistoryItem] = []


class StatusUpdateRequest(BaseModel):
    new_status: str = Field(..., description="Target status: Reported, In Progress, or Resolved")

    @field_validator("new_status")
    def validate_status_value(cls, v):
        valid = {"Reported", "In Progress", "Resolved"}
        if v not in valid:
            raise ValueError(f"Invalid status: '{v}'. Must be one of: {', '.join(sorted(valid))}")
        return v


class DashboardSummary(BaseModel):
    total: int
    high_priority: int
    pending: int
    in_progress: int
    resolved: int
    total_complaints: Optional[int] = None
    high_priority_complaints: Optional[int] = None
    pending_complaints: Optional[int] = None
    in_progress_complaints: Optional[int] = None
    resolved_complaints: Optional[int] = None
