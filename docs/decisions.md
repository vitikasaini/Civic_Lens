# CivicLens V1.0 — Design Decisions

> This document records the resolved open decisions from [plan.md](../plan.md) Section 9.
> Each decision includes the chosen option, alternatives considered, and rationale.

---

## Decision 1: Normalization Rules for Priority Factors

**Status:** ✅ Resolved

Each priority factor is normalized to the range [0, 1] before applying weights.

### 1.1 Severity (Weight: 0.40)

| Severity Level | Normalized Value |
|---------------|-----------------|
| Low           | 0.33            |
| Medium        | 0.67            |
| High          | 1.00            |

**Rationale:** Three evenly-spaced levels mapped to the lower two-thirds and top of the
[0, 1] range. Low is not zero because even a Low severity complaint has some importance.

### 1.2 Similar Complaint Count (Weight: 0.25)

```
normalized = min(similar_count / 10, 1.0)
```

- **Cap:** 10 similar complaints = maximum (1.0)
- **0 similar complaints** → 0.0
- **5 similar complaints** → 0.5
- **10+ similar complaints** → 1.0

**Rationale:** Cap of 10 prevents outlier clusters from disproportionately skewing
priority. 10 reports about the same issue is already a strong signal. The cap can be
adjusted based on real data patterns.

### 1.3 Location Importance (Weight: 0.20)

```
normalized = 1.0   if complaint is within 200m of any sensitive location
normalized = 0.5   otherwise (default — every location has some importance)
```

**Rationale:** Binary scoring is the simplest reliable approach for V1.0. The 200-meter
radius accounts for GPS imprecision and the effective impact zone around sensitive
locations. A non-zero default (0.5) ensures non-sensitive locations still contribute.

### 1.4 Time Since Reporting (Weight: 0.15)

```
normalized = min(days_elapsed / 30, 1.0)
```

- **Max days cap:** 30 days
- **0 days** → 0.0
- **15 days** → 0.5
- **30+ days** → 1.0

**Rationale:** After 30 days unresolved, urgency is at maximum. Linear scaling is simple
and interpretable. This factor naturally increases over time, pushing older unresolved
complaints up in priority.

---

## Decision 2: Location-Importance List (Sensitive Locations)

**Status:** ✅ Resolved

The following are initial sample sensitive locations for development and testing. In a
production deployment, this list would be populated with real coordinates from the target
city's data.

| # | Place Type | Name (Sample) | Latitude | Longitude | Radius (m) |
|---|-----------|---------------|----------|-----------|------------|
| 1 | Hospital | City General Hospital | 28.6139 | 77.2090 | 200 |
| 2 | School | Central Public School | 28.6329 | 77.2195 | 200 |
| 3 | Bus Stop | Main Bus Terminal | 28.6440 | 77.2167 | 200 |
| 4 | Market | Central Market | 28.6508 | 77.2289 | 200 |
| 5 | Government Office | Municipal Corporation HQ | 28.6353 | 77.2250 | 200 |
| 6 | Railway Station | City Railway Station | 28.6425 | 77.2210 | 200 |
| 7 | Religious Place | Community Temple | 28.6280 | 77.2155 | 200 |
| 8 | Park/Playground | Children's Park | 28.6180 | 77.2310 | 200 |

**Storage:** This list will be stored as a JSON configuration file at
`backend/ml/config/sensitive_locations.json` so it can be updated without code changes.

**Lookup method:** For each complaint, compute Haversine distance to every sensitive
location. If any distance ≤ 200m, location_importance = 1.0. Otherwise 0.5.

**Rationale:** These represent places where civic issues have outsized impact (health
risk near hospitals, child safety near schools, high foot traffic at bus stops/markets).
Sample coordinates are from Delhi, India for development/testing.

---

## Decision 3: Image–Text Category Conflict Resolution

**Status:** ✅ Resolved

**Chosen approach:** Confidence-weighted preference with text as tiebreaker.

### Rule

```
if image_category == text_category:
    final_category = image_category          # both agree

elif image_confidence >= 0.80:
    final_category = image_category          # image is very confident

elif text_confidence >= 0.80:
    final_category = text_category           # text is very confident

elif image_confidence > text_confidence + 0.15:
    final_category = image_category          # image is significantly more confident

else:
    final_category = text_category           # default to text (tiebreaker)
```

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Always prefer image | Images are direct evidence | Misclassification when image is ambiguous |
| Always prefer text | Citizen knows what they're reporting | Text may be vague |
| **Confidence-weighted (chosen)** | Uses best available signal | Slightly more complex |
| Ensemble voting | Most principled | Overkill for 2 classifiers |

**Rationale:** Text descriptions often carry more semantic detail about the issue type,
so text is the tiebreaker when both classifiers are uncertain. However, when the image
classifier is highly confident (≥ 0.80), it likely has clear visual evidence. The 0.15
margin prevents tiny confidence differences from swinging the decision.

**Logging:** Every resolution is logged with both predictions, confidences, and the
reason for the decision — enabling analysis and refinement.

---

## Decision 4: Dataset Availability & Fallback Strategy

**Status:** ✅ Resolved

### Image Datasets (Verified Sources)

| Category | Dataset | Source | Approx. Size | License |
|----------|---------|--------|-------------|---------|
| Potholes / Damaged Roads | RDD2022 / QR4Change / Kaggle Potholes | Mendeley Data, GitHub, Kaggle | 50,000+ total (sample 500 for training) | CC BY 4.0 / CC BY-SA 4.0 |
| Garbage Accumulation | QR4Change / TACO / Waste Classification v2 | Mendeley Data, GitHub (TACO), Kaggle | 15,000+ total (sample 500 for training) | CC BY 4.0 / MIT |
| Waterlogging / Drainage | AlleyFloodNet / Roadway Flooding / FloodNet | MDPI Electronics (Kaggle), Mendeley Data | 4,000+ total (sample 500 for training) | CC BY 4.0 |
| Streetlight Faults | Team16Project / Roboflow Damaged Lights | GitHub (Team16Project/Street-Light-Dataset), Roboflow | ~1,250 total (sample 500 for training) | Open Academic / CC BY 4.0 |

**Streetlight Faults Strategy:** While streetlight imagery has subtle visual failure modes (e.g. daytime unlit bulb vs working bulb), the combination of Team16Project (800+ images) and Roboflow (450+ images) satisfies the minimum threshold (≥50 images, targeting 500). Furthermore, the multimodal conflict resolution (Decision 3) gives precedence to unambiguous text descriptions ("light out", "pitch dark street") when image confidence is ambiguous.

### Text Datasets (Verified Sources)

Natural citizen grievance complaints will be extracted from:
1. **Boston 311 / NYC 311 Open Data:** Public domain 311 service request records filtered for "Pothole", "Sanitation / Dirty Conditions", "Street Flooding / Catch Basin", and "Street Light Out".
2. **FixMyStreet Sample Dataset:** Real citizen-written civic incident reports.
3. **Synthetic / Colloquial Augmentation:** 100–200 localized citizen phrasing variations per category to handle colloquial expressions.

1. **Synthetic generation:** Create 100–200 sample complaint descriptions per category
   based on real municipal complaint patterns. Document clearly as synthetic.
2. **Template-based:** Use complaint templates with varied wording, severity descriptions,
   and location references.
3. **Augmentation:** Synonym replacement, sentence reordering for variety.

**Documented as:** Synthetic training data. Evaluation metrics reflect performance on
synthetic test data and will be noted as such.

---

## Decision 5: Frontend Framework

**Status:** ✅ Resolved

**Chosen:** React with Vite

| Option | Pros | Cons |
|--------|------|------|
| **React + Vite (chosen)** | Fast dev server, huge ecosystem, beginner-friendly, great Leaflet integration (react-leaflet), massive community support | Slightly more boilerplate than simpler options |
| Vanilla JS + HTML | Zero dependencies, simplest | Hard to maintain as UI grows, manual DOM management |
| Svelte | Smaller bundle, simpler syntax | Smaller ecosystem, less Leaflet support |
| Vue | Good DX, lighter than React | Smaller community than React |

**Rationale:** React has the best ecosystem for our needs — `react-leaflet` for the map,
extensive UI component libraries, and the most beginner-friendly documentation. Vite
provides a fast dev server with hot module replacement, far superior to Create React App.

---

## Decision 6: Deep Learning Framework

**Status:** ✅ Resolved

**Chosen:** TensorFlow / Keras

| Option | Pros | Cons |
|--------|------|------|
| **TensorFlow/Keras (chosen)** | `tf.keras.applications.MobileNetV2` built-in, simpler high-level API, easier model saving/loading, better Windows support | Larger install size, slower import |
| PyTorch | More Pythonic, better for research | MobileNetV2 via torchvision (slightly more setup), model serving slightly more complex |

**Rationale:** For transfer learning with MobileNetV2, Keras provides the simplest path:
3 lines to load pretrained weights, freeze layers, and add a custom head. Model saving
is a single `.save()` call. Windows compatibility is generally smoother with TensorFlow.
The high-level Keras API aligns with the project's "beginner-friendly" requirement.

---

## Summary

| # | Decision | Choice | Key Reason |
|---|----------|--------|------------|
| 1 | Normalization rules | Defined caps: severity 3-level, similar/10, location binary, time/30 days | Simple, interpretable, documented |
| 2 | Sensitive locations | 8 sample locations (Delhi), 200m radius, JSON config | Configurable without code changes |
| 3 | Image–text conflict | Confidence-weighted, text as tiebreaker | Best signal wins, predictable fallback |
| 4 | Dataset availability | Kaggle datasets + synthetic text + augmentation for weak categories | Practical given public data landscape |
| 5 | Frontend framework | React + Vite | Best ecosystem for maps + UI + beginner docs |
| 6 | DL framework | TensorFlow / Keras | Simplest MobileNetV2 path, good Windows support |
