# CivicLens V1.0 — Project Plan (READ-ONLY)

> This file is the approved scope and roadmap for CivicLens V1.0.
> Treat it as READ-ONLY. Any change to architecture, scope, database, frontend,
> backend, AI model, dataset, or major UI behavior requires explicit approval
> from the project owner before this file is edited.

---

## 1. Project Vision

CivicLens is an AI-assisted civic issue management and decision-support platform.
The core problem is not collecting citizen complaints — it's what happens
**after** many complaints arrive: authorities can't easily tell which reports
describe the same problem, which are most serious, or why one should be
handled before another.

CivicLens converts raw citizen complaints into structured, grouped, and
explainably prioritized information.

**Goal:** Move from "collect complaints" to "understand, group, prioritize,
and support decisions."

---

## 2. Version Positioning

CivicLens V1.0 is **not** a complaint form, a CRUD app, a static dashboard, a
plain map, or an image classifier in isolation. It is a pipeline:

```
Citizen Report → AI/ML Analysis → Issue Classification → Severity Assessment
→ Duplicate/Nearby Grouping → Explainable Priority Calculation
→ Authority Dashboard → Map Visualization → Decision Support
```

V2.0 (CivicLens: Predictive Civic Intelligence Platform) is future scope only.
**Do not implement V2.0 features during V1.0** unless explicitly approved.

---

## 3. V1.0 Scope

### 3.1 Citizen Side
- Complaint submission: image, text description, location (map/location picker).
- System validates and stores the submission.

### 3.2 Issue Categories (fixed for V1.0 — do not expand without approval)
1. Potholes / Damaged Roads
2. Garbage Accumulation
3. Waterlogging / Drainage Problems
4. Streetlight Faults

System must stay modular so categories can be added later.

### 3.3 AI/ML Components
- **Image classification:** transfer learning with a practical pretrained CNN
  (e.g. MobileNetV2), subject to dataset/hardware verification. Preprocessing
  via OpenCV and/or the chosen ML framework.
- **Text classification:** TF-IDF features + Logistic Regression baseline;
  Random Forest as a comparison if feasible.
- Do not claim a model is trained or accurate until it has actually been
  trained and evaluated.

### 3.4 Severity Assessment

Severity (Low / Medium / High) is estimated from **defined, documented,
reproducible rules** applied to information the system actually has —
never directly from classifier confidence. (Confidence ≠ severity.)

**Sources combined into a point score:**

1. **Text cues** — category-specific keyword/phrase lookup against the
   complaint description.

   | Category | High-severity cues (+2) | Medium cues (+1) |
   |---|---|---|
   | Pothole/Road | "accident," "deep," "large," "vehicle damage," "can't pass" | "growing," "worsening," "multiple potholes" |
   | Garbage | "overflowing," "rotting," "days," "smell," "health hazard" | "not collected," "pile" |
   | Waterlogging | "flooded," "knee-deep," "entering homes," "sewage" | "standing water," "slow drainage" |
   | Streetlight | "no light for weeks," "safety," "dark street," "accident-prone" | "flickering," "dim" |

   No cue matched → 0 points (routine/default).

2. **Citizen-reported severity** — a submission-form dropdown
   (Minor / Moderate / Severe), mapped to +0 / +1 / +2. This is a direct
   citizen input, not a model output, and is documented as such.

3. **Image-based cue (optional, category-limited)** — for Pothole and
   Garbage only, a coarse OpenCV proportion-of-affected-area heuristic
   (large affected area → +1). Not attempted for Waterlogging/Streetlight,
   where an image proxy isn't reliably meaningful. Documented explicitly in
   the report as a coarse heuristic, not calibrated severity.

**Combination rule:**

```
severity_points = text_cue_score + citizen_score + (image_cue_score if applicable)

0–1 points → Low
2–3 points → Medium
4+ points  → High
```

**Validation:** a sample of 20–30 complaints will be rated Low/Medium/High
by a few human reviewers and compared against the rule output (agreement
rate) as part of the evaluation (see Section 8).

### 3.5 Duplicate / Nearby Complaint Grouping
- Identify potentially related reports using geographic distance, text
  similarity, and issue category.
- Practical approach: Haversine distance + DBSCAN for spatial grouping,
  combined with text similarity.
- Output: grouped complaint count contributes to priority.

### 3.6 Explainable Priority Engine
Normalized factors (0–1 each):

```
Priority Score = 0.40 × Severity
               + 0.25 × Similar Complaints
               + 0.20 × Location Importance
               + 0.15 × Time Since Reporting
```

- Weights are initial project assumptions, documented as such, and may later
  be evaluated against human reviewer rankings.
- Dashboard must show the **contributing factors**, not just a number
  (e.g. "Severity: High · Similar complaints: 8 · Location importance: High ·
  Time unresolved: 5 days").

### 3.7 Authority Dashboard
- Overview counts: total / high-priority / pending / in-progress / resolved.
- Complaint list: ID, category, location, severity, priority, similar-complaint
  count, status, timestamp.
- Filtering: category, priority, severity, status.
- Sorting: by priority.

### 3.8 Complaint Status
- Reported → In Progress → Resolved, with status history stored.

### 3.9 Map Interface
- Interactive map (Leaflet by default) showing complaint locations, with
  visual indicators for priority level.

### 3.10 Database
- SQLite by default (local, simple). Stores: complaint ID, description,
  image reference, location, category, severity, priority score, priority
  factors, grouping info, status, timestamp.
- Schema should stay modular enough to migrate to a larger DB later if needed.

---

## 4. System Architecture

```
Citizen GUI
   ↓
Frontend
   ↓
Backend API (FastAPI)
   ↓
Complaint Processing
   ├── Image Model
   ├── Text Model
   ├── Severity Module
   ├── Duplicate/Grouping Module
   └── Priority Engine
   ↓
Database (SQLite)
   ↓
Authority Dashboard
   ├── Complaint Table
   ├── Priority View
   ├── Filters
   ├── Status Management
   └── Interactive Map
```

No unnecessary microservices or complex infrastructure.

---

## 5. Technology Stack

| Layer | Choice |
|---|---|
| Frontend | React, or another lightweight practical option — finalize before implementation |
| Backend | FastAPI |
| Database | SQLite |
| ML | Scikit-learn |
| Deep Learning | TensorFlow/Keras or PyTorch — finalize before implementation |
| Image Processing | OpenCV |
| Data Processing | Pandas, NumPy |
| Map | Leaflet |
| Version Control | Git/GitHub |

Do not add technologies just to look advanced.

---

## 6. End-to-End Workflow

1. Citizen opens CivicLens.
2. Citizen submits image + description + location.
3. Backend validates the submission.
4. Complaint is stored.
5. Image model analyzes the image.
6. Text classifier analyzes the description.
7. System determines the civic issue category.
8. Severity is estimated per defined criteria.
9. System checks for nearby/similar existing complaints.
10. Related complaints are grouped where appropriate.
11. Priority score is calculated.
12. Complaint appears on the authority dashboard.
13. Authority filters/sorts/inspects/views location/updates status.
14. Map displays the issue geographically.

Must work end-to-end, locally.

---

## 7. Testing Strategy

Build → Test → Fix → Verify → Continue, after **every** major feature.
Never leave testing to the end.

Checklist:
- [ ] Citizen can submit a complaint
- [ ] Complaint correctly stored in database
- [ ] Image model returns a valid category
- [ ] Text classifier works on sample descriptions
- [ ] Severity calculation follows defined rules
- [ ] Duplicate/nearby grouping works on known sample complaints
- [ ] Priority formula produces expected score
- [ ] Dashboard retrieves and displays complaints
- [ ] Status updating works
- [ ] Map correctly displays complaint locations
- [ ] Full end-to-end workflow works

---

## 8. Evaluation Plan

- **Classification:** accuracy, precision, recall, F1-score, confusion matrix.
- **Priority system:** rank a small sample of complaints manually (human
  reviewers) and compare to system ranking via Spearman correlation.
- **Functional:** submission, classification, grouping, priority calc,
  dashboard, filtering, status updates, map — all tested.
- Never report accuracy/F1/etc. without having actually measured it. If
  untested, say "Not yet evaluated."

---

## 9. Open Decisions (must be resolved, not assumed)

- [x] Exact severity criteria — resolved, see Section 3.4 (rule-based point
      score: text cues + citizen input + optional image heuristic)
- [ ] Normalization rules for each priority factor (caps/ranges)
- [ ] Location-importance list: sensitive places + coordinates
- [ ] What happens when image and text predictions disagree
- [ ] Confirm dataset availability per category (esp. streetlight faults);
      fallback category if unavailable
- [ ] Frontend framework: React vs. lightweight alternative
- [ ] DL framework: TensorFlow/Keras vs. PyTorch

---

## 10. Development Rules

1. **Stay inside scope.** No features outside the approved version.
2. **V1 first.** No V2.0 features during V1.0.
3. **This file is read-only** unless the project owner approves a change.
4. **`/goal` workflow:** understand the goal → check this plan → explain
   approach → identify affected files → ask necessary confirmation questions
   → implement only the approved task → test it → report the result.
5. **Confirmation required** before decisions materially affecting:
   architecture, scope, database, frontend, backend, AI model, dataset,
   external API, or major UI behavior. No unnecessary questions on trivial
   details.
6. **Better suggestions:** never silently swap the requested approach.
   State current approach → alternative → reason → pros/cons → let owner decide.
7. **Test after every major feature** — never batch testing to the end.
8. **Practicality first.** Simplest reliable solution; no technology added
   just to look advanced.
9. **Local system.** Must run on the developer's local computer. Avoid
   unnecessary paid APIs or cloud dependencies.
10. **No fake results.** Never invent accuracy, F1, dataset size, performance,
    user numbers, deployment or validation results. Untested = "Not yet
    evaluated."
11. **Beginner-friendly.** Explain important implementation decisions before
    or while implementing. No huge unexplained codebase.
12. **Maintainability.** Keep modules separate so V1.0 can extend into V2.0
    without a rewrite.

---

## 11. Definition of Done (V1.0)

A user can: submit a civic issue → system analyzes it → groups related
reports → calculates an explainable priority → authority sees it on
dashboard/map → authority updates its status — end to end, working, locally.

Optimize for: **Working + Understandable + Testable + Practical + Expandable.**
Not for: number of technologies used.

---

## 12. Future Scope — CivicLens 2.0 (not in V1.0)

Predictive Civic Intelligence Platform — moves from reactive management to
prediction, using historical complaints, weather, traffic, infrastructure
condition, and repair records:
- Predictive risk estimation (e.g. waterlogging risk from rainfall + history)
- Problem-relationship / root-cause chains (e.g. rainfall → blocked drain →
  waterlogging → pothole)
- Resource-aware action planning across available teams
- What-if simulation (adjust variables, recalculate risk/priority/resources)
- Advanced map layers: infrastructure health, predicted risk, recommended
  preventive actions

V2.0 extends the V1.0 architecture — it is not a separate rebuild.
