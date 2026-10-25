"""
Duplicate and Nearby Complaint Grouping Module for CivicLens V1.0.

Implements Section 3.5 of plan.md:
1. Spatial grouping via Haversine distance and DBSCAN clustering (default eps = 500m).
2. Semantic text similarity via TF-IDF cosine similarity (threshold = 0.65).
3. Combined multi-criteria grouping: same category AND (spatial proximity OR text similarity).
4. Group ID assignment and similar_count calculation.
"""

import math
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from backend.ml.text_classifier import TextClassifier
from backend.models.complaint import Complaint

logger = logging.getLogger("civiclens.grouping")

# Constants per plan.md Section 3.5 & Design Decisions
EARTH_RADIUS_METERS = 6371000.0
DEFAULT_EPS_METERS = 500.0  # 500 meters spatial neighborhood
DEFAULT_MIN_SAMPLES = 2     # At least 2 complaints to form a group
DEFAULT_TEXT_SIMILARITY_THRESHOLD = 0.65  # TF-IDF cosine threshold


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in meters.
    Formula:
      a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
      c = 2 ⋅ atan2( √a, √(1−a) )
      d = R ⋅ c
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Computes cosine similarity between two text descriptions using
    the fitted TF-IDF vectorizer from backend.ml.text_classifier.
    Returns float in range [0.0, 1.0].
    """
    if not text1 or not text2:
        return 0.0

    t1_clean = text1.strip()
    t2_clean = text2.strip()
    if not t1_clean or not t2_clean:
        return 0.0

    classifier = TextClassifier.get_instance()
    vectorizer = classifier.vectorizer

    try:
        vecs = vectorizer.transform([t1_clean, t2_clean])
        sim = float(cosine_similarity(vecs[0:1], vecs[1:2])[0][0])
        return max(0.0, min(1.0, sim))
    except Exception as e:
        logger.warning(f"Error computing text similarity: {e}")
        return 0.0


def cluster_coordinates_dbscan(
    coords: List[Tuple[float, float]],
    eps_meters: float = DEFAULT_EPS_METERS,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> List[int]:
    """
    Performs DBSCAN spatial clustering on geographic coordinates.
    Uses precomputed Haversine distance matrix in meters.
    Returns: list of cluster labels (-1 for noise/unclustered, 0, 1, ... for clusters).
    """
    n = len(coords)
    if n == 0:
        return []
    if n < min_samples:
        return [-1] * n

    dist_matrix = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_distance(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    db = DBSCAN(eps=eps_meters, min_samples=min_samples, metric="precomputed")
    labels = db.fit_predict(dist_matrix)
    return labels.tolist()


class DisjointSet:
    """Disjoint Set Union (Union-Find) with path compression and union by rank."""

    def __init__(self, elements: List[int]):
        self.parent = {x: x for x in elements}
        self.rank = {x: 0 for x in elements}

    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        rx = self.find(x)
        ry = self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            self.parent[rx] = ry
        elif self.rank[rx] > self.rank[ry]:
            self.parent[ry] = rx
        else:
            self.parent[ry] = rx
            self.rank[rx] += 1


def group_complaints_data(
    complaints: List[Dict[str, Any]],
    eps_meters: float = DEFAULT_EPS_METERS,
    similarity_threshold: float = DEFAULT_TEXT_SIMILARITY_THRESHOLD,
) -> Dict[int, Dict[str, Any]]:
    """
    Pure grouping function operating on a list of complaint dicts:
    Each dict must contain: 'id', 'category', 'latitude', 'longitude', 'description'.

    Rule per Section 3.5 & Subtask 5.3.1:
    Complaints are grouped IF AND ONLY IF:
      - same category AND
      - (spatial distance <= eps_meters OR text similarity >= similarity_threshold)

    Returns a mapping:
      complaint_id -> {'group_id': Optional[int], 'similar_count': int}
    """
    results: Dict[int, Dict[str, Any]] = {}
    if not complaints:
        return results

    # Partition by category
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for c in complaints:
        cat = c.get("category")
        if not cat:
            # Uncategorized complaints cannot be grouped
            results[c["id"]] = {"group_id": None, "similar_count": 0}
            continue
        by_category.setdefault(cat, []).append(c)

    for cat, cat_complaints in by_category.items():
        n = len(cat_complaints)
        if n <= 1:
            for c in cat_complaints:
                results[c["id"]] = {"group_id": None, "similar_count": 0}
            continue

        ids = [c["id"] for c in cat_complaints]
        dsu = DisjointSet(ids)

        for i in range(n):
            c_i = cat_complaints[i]
            for j in range(i + 1, n):
                c_j = cat_complaints[j]

                # Check spatial distance
                dist = haversine_distance(
                    c_i["latitude"], c_i["longitude"],
                    c_j["latitude"], c_j["longitude"],
                )
                nearby = (dist <= eps_meters)

                # Check text similarity
                sim = compute_text_similarity(c_i["description"], c_j["description"])
                similar_text = (sim >= similarity_threshold)

                if nearby or similar_text:
                    dsu.union(c_i["id"], c_j["id"])

        # Collect components
        clusters: Dict[int, List[int]] = {}
        for cid in ids:
            root = dsu.find(cid)
            clusters.setdefault(root, []).append(cid)

        # Assign group_id and similar_count
        for root, cluster_ids in clusters.items():
            if len(cluster_ids) > 1:
                group_id = min(cluster_ids)  # Deterministic group id: root minimum ID
                count = len(cluster_ids) - 1
                for cid in cluster_ids:
                    results[cid] = {"group_id": group_id, "similar_count": count}
            else:
                cid = cluster_ids[0]
                results[cid] = {"group_id": None, "similar_count": 0}

    return results


def recompute_all_groups(
    db: Session,
    eps_meters: float = DEFAULT_EPS_METERS,
    similarity_threshold: float = DEFAULT_TEXT_SIMILARITY_THRESHOLD,
) -> int:
    """
    Fetches all complaints from the database, recalculates grouping,
    and updates group_id and similar_count fields in DB.
    Returns number of complaints updated.
    """
    complaints = db.query(Complaint).all()
    if not complaints:
        return 0

    data = [
        {
            "id": c.id,
            "category": c.category,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "description": c.description,
        }
        for c in complaints
    ]

    group_map = group_complaints_data(data, eps_meters=eps_meters, similarity_threshold=similarity_threshold)

    updated_count = 0
    for c in complaints:
        if c.id in group_map:
            info = group_map[c.id]
            if c.group_id != info["group_id"] or c.similar_count != info["similar_count"]:
                c.group_id = info["group_id"]
                c.similar_count = info["similar_count"]
                updated_count += 1

    db.commit()
    logger.info(f"Recomputed grouping for {len(complaints)} complaints ({updated_count} updated).")
    return updated_count
