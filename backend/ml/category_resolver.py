"""
Category Resolution Module for CivicLens V1.0.

Resolves multimodal category predictions from Image and Text classifiers
using the confidence-weighted decision rules established in Decision 3 (docs/decisions.md).
"""

import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger("civiclens.category_resolver")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

CANONICAL_CATEGORIES = {
    "Potholes / Damaged Roads",
    "Garbage Accumulation",
    "Waterlogging / Drainage Problems",
    "Streetlight Faults",
}


def canonicalize_category(name: Optional[str]) -> Optional[str]:
    """Helper to match shorthand or exact names to canonical category names."""
    if not name or name == "Unknown":
        return None
    name_lower = name.lower()
    if "pothole" in name_lower or "road" in name_lower:
        return "Potholes / Damaged Roads"
    if "garbage" in name_lower or "trash" in name_lower or "waste" in name_lower:
        return "Garbage Accumulation"
    if "water" in name_lower or "flood" in name_lower or "drain" in name_lower:
        return "Waterlogging / Drainage Problems"
    if "light" in name_lower or "lamp" in name_lower:
        return "Streetlight Faults"
    return name


def resolve(
    image_prediction: Tuple[str, float],
    text_prediction: Tuple[str, float],
) -> str:
    """
    Convenience wrapper returning just the final resolved category string.
    """
    result = resolve_detailed(image_prediction, text_prediction)
    return result["final_category"]


def resolve_detailed(
    image_prediction: Tuple[str, float],
    text_prediction: Tuple[str, float],
) -> Dict[str, Any]:
    """
    Combines image prediction (category, confidence) and text prediction (category, confidence)
    following Decision 3:

    Rule:
    1. If image == text: agreement -> final = image (confidence averaged)
    2. If one is Unknown: use the other
    3. If image_conf >= 0.80 and text_conf < 0.80: image wins
    4. If text_conf >= 0.80 and image_conf < 0.80: text wins
    5. If image_conf > text_conf + 0.15: image wins (significantly more confident)
    6. Else: default to text (tiebreaker, as citizen description carries rich semantic intent)

    Returns:
        {
            "final_category": str,
            "reason": str,
            "agreed": bool,
            "image_prediction": {"category": str, "confidence": float},
            "text_prediction": {"category": str, "confidence": float},
        }
    """
    img_cat_raw, img_conf = image_prediction
    txt_cat_raw, txt_conf = text_prediction

    img_cat = canonicalize_category(img_cat_raw)
    txt_cat = canonicalize_category(txt_cat_raw)

    # 1. Handle Unknown / missing cases
    if not img_cat and not txt_cat:
        decision = "Unknown"
        reason = "Both image and text classifiers were unable to classify the complaint."
        agreed = False
    elif not img_cat:
        decision = txt_cat
        reason = "Image classifier returned Unknown; using text classifier."
        agreed = False
    elif not txt_cat:
        decision = img_cat
        reason = "Text classifier returned Unknown; using image classifier."
        agreed = False
    elif img_cat == txt_cat:
        # 2. Both agree
        decision = img_cat
        reason = f"Both image ({img_conf:.2f}) and text ({txt_conf:.2f}) classifiers agree on '{img_cat}'."
        agreed = True
    elif img_conf >= 0.80 and txt_conf < 0.80:
        # 3. Image is highly confident
        decision = img_cat
        reason = f"Image classifier is highly confident ({img_conf:.2f} >= 0.80) while text is {txt_conf:.2f}."
        agreed = False
    elif txt_conf >= 0.80 and img_conf < 0.80:
        # 4. Text is highly confident
        decision = txt_cat
        reason = f"Text classifier is highly confident ({txt_conf:.2f} >= 0.80) while image is {img_conf:.2f}."
        agreed = False
    elif img_conf > txt_conf + 0.15:
        # 5. Image significantly more confident
        decision = img_cat
        reason = f"Image classifier ({img_conf:.2f}) is significantly more confident than text ({txt_conf:.2f}) by >0.15 margin."
        agreed = False
    else:
        # 6. Default to text as tiebreaker
        decision = txt_cat
        reason = f"Classifiers disagreed (img={img_cat}@{img_conf:.2f}, txt={txt_cat}@{txt_conf:.2f}); defaulted to text description as tiebreaker."
        agreed = False

    logger.info(
        "Resolved Category: '%s' | Agreed: %s | Reason: %s [Img: %s (%.2f), Txt: %s (%.2f)]",
        decision,
        agreed,
        reason,
        img_cat_raw,
        img_conf,
        txt_cat_raw,
        txt_conf,
    )

    return {
        "final_category": decision,
        "reason": reason,
        "agreed": agreed,
        "image_prediction": {"category": img_cat_raw, "confidence": img_conf},
        "text_prediction": {"category": txt_cat_raw, "confidence": txt_conf},
    }
