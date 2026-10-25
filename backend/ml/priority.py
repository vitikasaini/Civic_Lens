"""
Explainable Priority Engine for CivicLens V1.0.

Implements Section 3.6 of plan.md and Decision 1 of docs/decisions.md:
Priority Formula:
  Priority = 0.40 * Severity + 0.25 * Similar Complaints + 0.20 * Location Importance + 0.15 * Time Since Reporting

All 4 contributing factors are normalized to the range [0.0, 1.0] and returned with
complete explainability: {value, normalized, weight, contribution}.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from backend.ml.grouping import haversine_distance
from backend.models.complaint import Complaint

logger = logging.getLogger("civiclens.priority")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SENSITIVE_LOCATIONS_FILE = BASE_DIR / "backend" / "ml" / "config" / "sensitive_locations.json"

# Weights per plan.md Section 3.6
WEIGHT_SEVERITY = 0.40
WEIGHT_SIMILAR = 0.25
WEIGHT_LOCATION = 0.20
WEIGHT_TIME = 0.15

# Normalization constants per docs/decisions.md Decision 1
SEVERITY_NORMALIZED = {
    "Low": 0.33,
    "Medium": 0.67,
    "High": 1.00,
}

SIMILAR_CAP = 10
DEFAULT_SENSITIVE_RADIUS = 200.0  # 200m radius
LOCATION_NORMALIZED_SENSITIVE = 1.00
LOCATION_NORMALIZED_STANDARD = 0.50
TIME_MAX_DAYS = 30.0

# Load sensitive locations list
_SENSITIVE_LOCATIONS: List[Dict[str, Any]] = []
if SENSITIVE_LOCATIONS_FILE.exists():
    try:
        with open(SENSITIVE_LOCATIONS_FILE, "r", encoding="utf-8") as f:
            _SENSITIVE_LOCATIONS = json.load(f).get("locations", [])
    except Exception as e:
        logger.error(f"Failed to load sensitive locations from {SENSITIVE_LOCATIONS_FILE}: {e}")


def normalize_severity(severity: Optional[str]) -> Tuple[float, str]:
    """
    Normalizes severity level to [0, 1]:
      Low -> 0.33, Medium -> 0.67, High -> 1.00
    """
    if not severity:
        return 0.33, "Low"
    sev_cap = severity.capitalize()
    norm = SEVERITY_NORMALIZED.get(sev_cap, 0.33)
    return norm, sev_cap


def normalize_similar_count(similar_count: int, cap: int = SIMILAR_CAP) -> Tuple[float, int]:
    """
    Normalizes similar complaints count:
      min(count / 10, 1.0)
    """
    cnt = max(0, int(similar_count or 0))
    norm = min(cnt / float(cap), 1.0)
    return round(norm, 4), cnt


def normalize_location(
    latitude: float,
    longitude: float,
    sensitive_locations: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[float, str, Optional[str]]:
    """
    Determines if complaint is within radius of any sensitive landmark.
    Returns: (normalized_score, label, matched_location_name)
      Sensitive (within 200m) -> 1.00
      Standard (otherwise) -> 0.50
    """
    locs = sensitive_locations if sensitive_locations is not None else _SENSITIVE_LOCATIONS
    for loc in locs:
        loc_lat = loc.get("latitude")
        loc_lon = loc.get("longitude")
        radius = loc.get("radius_meters", DEFAULT_SENSITIVE_RADIUS)

        dist = haversine_distance(latitude, longitude, loc_lat, loc_lon)
        if dist <= radius:
            return LOCATION_NORMALIZED_SENSITIVE, "Sensitive", loc.get("name")

    return LOCATION_NORMALIZED_STANDARD, "Standard", None


def normalize_time(
    created_at: Optional[datetime],
    now: Optional[datetime] = None,
    max_days: float = TIME_MAX_DAYS,
) -> Tuple[float, float, str]:
    """
    Normalizes time since reporting:
      min(days_elapsed / 30, 1.0)
    Returns: (normalized_score, days_elapsed, display_string)
    """
    if created_at is None:
        return 0.0, 0.0, "0.0 days"

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    delta = now - created_at
    days_elapsed = max(0.0, delta.total_seconds() / 86400.0)
    norm = min(days_elapsed / max_days, 1.0)
    return round(norm, 4), round(days_elapsed, 2), f"{days_elapsed:.1f} days"


def calculate_priority(
    severity: Optional[str],
    similar_count: int,
    latitude: float,
    longitude: float,
    created_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Calculates explainable priority score and factor breakdown:
      Priority = 0.40 * Severity + 0.25 * Similar + 0.20 * Location + 0.15 * Time
    """
    sev_norm, sev_val = normalize_severity(severity)
    sim_norm, sim_val = normalize_similar_count(similar_count)
    loc_norm, loc_label, matched_loc = normalize_location(latitude, longitude)
    time_norm, days_elapsed, time_label = normalize_time(created_at, now=now)

    sev_contrib = round(sev_norm * WEIGHT_SEVERITY, 4)
    sim_contrib = round(sim_norm * WEIGHT_SIMILAR, 4)
    loc_contrib = round(loc_norm * WEIGHT_LOCATION, 4)
    time_contrib = round(time_norm * WEIGHT_TIME, 4)

    total_score = round(sev_contrib + sim_contrib + loc_contrib + time_contrib, 4)

    return {
        "score": total_score,
        "severity": {
            "value": sev_val,
            "normalized": sev_norm,
            "weight": WEIGHT_SEVERITY,
            "contribution": sev_contrib,
        },
        "similar": {
            "value": sim_val,
            "normalized": sim_norm,
            "weight": WEIGHT_SIMILAR,
            "contribution": sim_contrib,
        },
        "location": {
            "value": loc_label,
            "matched_location": matched_loc,
            "normalized": loc_norm,
            "weight": WEIGHT_LOCATION,
            "contribution": loc_contrib,
        },
        "time": {
            "value": time_label,
            "days_elapsed": days_elapsed,
            "normalized": time_norm,
            "weight": WEIGHT_TIME,
            "contribution": time_contrib,
        },
    }


def update_complaint_priority(complaint: Complaint, now: Optional[datetime] = None) -> float:
    """
    Computes priority for an individual Complaint ORM instance, updating
    complaint.priority_score and complaint.priority_factors in-place.
    """
    priority_result = calculate_priority(
        severity=complaint.severity,
        similar_count=complaint.similar_count,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        created_at=complaint.created_at,
        now=now,
    )

    complaint.priority_score = priority_result["score"]

    # Merge factor breakdown with existing factors (such as severity breakdown / ML metadata)
    current_factors = dict(complaint.priority_factors or {})
    current_factors["priority_breakdown"] = priority_result
    complaint.priority_factors = current_factors
    return priority_result["score"]


def recalculate_all_priorities(db: Session, now: Optional[datetime] = None) -> int:
    """
    Recalculates priority scores for all complaints in the database.
    Used after grouping changes or as periodic update.
    Returns number of complaints updated.
    """
    complaints = db.query(Complaint).all()
    if not complaints:
        return 0

    for c in complaints:
        update_complaint_priority(c, now=now)

    db.commit()
    logger.info(f"Recalculated priorities for {len(complaints)} complaints.")
    return len(complaints)
