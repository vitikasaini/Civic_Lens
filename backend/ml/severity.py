"""
Severity Assessment Engine for CivicLens V1.0.

Computes reproducible, rule-based severity (Low / Medium / High) from defined inputs
per plan.md Section 3.4:
1. Text cues (category-specific keywords: +2 for High, +1 for Medium, 0 default)
2. Citizen-reported severity (Minor = +0, Moderate = +1, Severe = +2)
3. Image-based heuristic (Pothole & Garbage only: +1 for large affected area via OpenCV)

Combination rule:
- 0-1 points -> Low
- 2-3 points -> Medium
- 4+ points  -> High
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Category-specific severity keywords per plan.md Section 3.4
SEVERITY_CUES = {
    "Potholes / Damaged Roads": {
        "high": ["accident", "deep", "large", "vehicle damage", "can't pass", "cannot pass", "caved in"],
        "medium": ["growing", "worsening", "multiple potholes", "bumpy", "uneven"],
    },
    "Garbage Accumulation": {
        "high": ["overflowing", "rotting", "days", "smell", "stench", "health hazard", "unhygienic"],
        "medium": ["not collected", "pile", "litter", "spilling"],
    },
    "Waterlogging / Drainage Problems": {
        "high": ["flooded", "knee-deep", "knee deep", "entering homes", "entering shops", "sewage", "submerged"],
        "medium": ["standing water", "slow drainage", "puddle", "ponding"],
    },
    "Streetlight Faults": {
        "high": ["no light for weeks", "safety", "dark street", "accident-prone", "pitch dark", "blackout", "danger"],
        "medium": ["flickering", "dim", "intermittent", "faulty"],
    },
}

CITIZEN_SEVERITY_POINTS = {
    "Minor": 0,
    "Moderate": 1,
    "Severe": 2,
}


def score_text_cues(text: str, category: Optional[str]) -> Tuple[int, List[str]]:
    """
    Scans text description for category-specific high (+2) and medium (+1) keywords.
    Returns: (score, list_of_matched_cues)
    """
    if not text or not category or category not in SEVERITY_CUES:
        return 0, []

    text_lower = text.lower()
    cues = SEVERITY_CUES[category]

    matched_high = [phrase for phrase in cues["high"] if re.search(r"\b" + re.escape(phrase) + r"\b", text_lower)]
    matched_med = [phrase for phrase in cues["medium"] if re.search(r"\b" + re.escape(phrase) + r"\b", text_lower)]

    if matched_high:
        return 2, matched_high + matched_med
    elif matched_med:
        return 1, matched_med
    else:
        return 0, []


def score_image_cue(image_path: Optional[str], category: Optional[str]) -> int:
    """
    Applies coarse OpenCV proportion-of-affected-area heuristic:
    - Only applicable to 'Potholes / Damaged Roads' and 'Garbage Accumulation'.
    - Returns +1 if affected area ratio exceeds threshold, else 0.
    - Waterlogging and Streetlight always return 0 per project plan.
    """
    if not image_path or not category:
        return 0

    # Strictly restricted to Pothole and Garbage categories
    if category not in {"Potholes / Damaged Roads", "Garbage Accumulation"}:
        return 0

    p = Path(image_path)
    if not p.is_absolute():
        p = BASE_DIR / p

    if not p.exists():
        return 0

    img = cv2.imread(str(p))
    if img is None or img.size == 0:
        return 0

    h, w = img.shape[:2]
    total_pixels = h * w

    if category == "Potholes / Damaged Roads":
        # Estimate dark cavity / depression area
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Asphalt depressions generally have pixel values < 65
        dark_mask = cv2.inRange(gray, 0, 65)
        affected_pixels = cv2.countNonZero(dark_mask)
        ratio = affected_pixels / total_pixels
        return 1 if ratio >= 0.12 else 0

    elif category == "Garbage Accumulation":
        # Estimate high-contrast edge & color clutter characteristic of trash piles
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = cv2.countNonZero(edges)
        ratio = edge_pixels / total_pixels
        return 1 if ratio >= 0.08 else 0

    return 0


def assess_severity(
    description: str,
    category: Optional[str],
    citizen_severity: str,
    image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculates combined severity points and categorizes as Low, Medium, or High.

    Points system:
    severity_points = text_cue_score + citizen_score + image_cue_score

    0-1 points -> Low
    2-3 points -> Medium
    4+ points  -> High

    Returns detailed breakdown dictionary.
    """
    # 1. Text cues
    text_cue_score, matched_cues = score_text_cues(description, category)

    # 2. Citizen severity input
    norm_cit = citizen_severity.strip().capitalize() if citizen_severity else "Minor"
    citizen_score = CITIZEN_SEVERITY_POINTS.get(norm_cit, 0)

    # 3. Image-based cue (Pothole & Garbage only)
    image_cue_score = score_image_cue(image_path, category)

    # 4. Total points
    total_points = text_cue_score + citizen_score + image_cue_score

    # 5. Mapping to tier
    if total_points <= 1:
        tier = "Low"
    elif total_points <= 3:
        tier = "Medium"
    else:
        tier = "High"

    return {
        "severity": tier,
        "points": total_points,
        "text_cue": text_cue_score,
        "citizen": citizen_score,
        "image_cue": image_cue_score,
        "matched_cues": matched_cues,
    }
