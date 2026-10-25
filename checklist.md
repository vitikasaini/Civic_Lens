# CivicLens V1.0 — Development Checklist

> Derived from [plan.md](./plan.md).
> Every phase contains **subtasks**, **deliverables**, and **verification tests**.
> A phase may not begin until the previous phase's verification tests all pass.
> Workflow: **Build → Test → Fix → Verify → Continue.**

---

## Phase 0: Project Bootstrap & Open-Decision Resolution

Before any code is written, resolve the open decisions listed in Section 9 of the plan and set up the development environment.

### Subtasks

- [x] **0.1 — Resolve open decisions**
  - [x] 0.1.1 — Decide normalization rules for each priority factor (caps / ranges for severity, similar-complaint count, location importance, time-since-reporting).
  - [x] 0.1.2 — Define the location-importance list (sensitive places + their coordinates; e.g., hospitals, schools, bus stops).
  - [x] 0.1.3 — Define the conflict-resolution rule when image-predicted category ≠ text-predicted category (e.g., prefer higher-confidence, prefer text, or flag for review).
  - [x] 0.1.4 — Confirm dataset availability for all 4 categories (Potholes, Garbage, Waterlogging, Streetlight Faults). Define a fallback plan for any category with insufficient data.
  - [x] 0.1.5 — Finalize frontend framework choice: React vs. lightweight alternative.
  - [x] 0.1.6 — Finalize deep-learning framework choice: TensorFlow/Keras vs. PyTorch.

- [x] **0.2 — Repository & environment setup**
  - [x] 0.2.1 — Initialize Git repository with `.gitignore` (Python, Node, data files, model weights).
  - [x] 0.2.2 — Create project folder structure:
    ```
    civicLens/
    ├── backend/          # FastAPI app
    │   ├── api/          # route handlers
    │   ├── models/       # SQLAlchemy / DB models
    │   ├── ml/           # ML modules (image, text, severity, grouping, priority)
    │   └── tests/
    ├── frontend/         # React (or chosen framework)
    ├── data/             # datasets, sample images
    ├── notebooks/        # exploration / training notebooks
    ├── scripts/          # one-off utilities
    └── docs/             # documentation
    ```
  - [x] 0.2.3 — Set up Python virtual environment & `requirements.txt` (FastAPI, uvicorn, SQLAlchemy, scikit-learn, TF/PyTorch, OpenCV, pandas, numpy).
  - [x] 0.2.4 — Set up frontend project (e.g., `npx create-react-app` or Vite).
  - [x] 0.2.5 — Verify both backend dev server (`uvicorn`) and frontend dev server start without errors.

### Phase 0 — Verification Tests

- [x] T0.1 — All 6 open decisions in Section 9 have documented answers in a `docs/decisions.md` file. **Pass:** Each decision has a clear choice + short rationale.
- [x] T0.2 — `git log` shows initial commit. **Pass:** Repo initialized.
- [x] T0.3 — `pip install -r requirements.txt` succeeds in the virtual environment. **Pass:** No install errors.
- [x] T0.4 — Backend: `uvicorn backend.main:app --reload` starts and responds at `http://localhost:8000/docs`. **Pass:** 200 OK on Swagger UI.
- [x] T0.5 — Frontend: dev server starts and shows the default page. **Pass:** Page renders in browser.
- [x] T0.6 — Folder structure matches the agreed layout. **Pass:** `tree` output matches spec.

---

## Phase 1: Database & Core Backend API

Build the SQLite database schema and the CRUD API for complaints. No ML yet — this phase is pure data plumbing.

### Subtasks

- [x] **1.1 — Database schema**
  - [x] 1.1.1 — Define `complaints` table: `id` (PK, auto), `description` (TEXT), `image_path` (TEXT), `latitude` (REAL), `longitude` (REAL), `category` (TEXT, nullable — set by ML later), `citizen_severity` (TEXT — Minor/Moderate/Severe), `severity` (TEXT, nullable — computed later), `severity_points` (INT, nullable), `priority_score` (REAL, nullable), `priority_factors` (JSON/TEXT, nullable), `group_id` (INT, nullable), `similar_count` (INT, default 0), `status` (TEXT, default "Reported"), `created_at` (DATETIME), `updated_at` (DATETIME).
  - [x] 1.1.2 — Define `status_history` table: `id` (PK), `complaint_id` (FK), `old_status` (TEXT), `new_status` (TEXT), `changed_at` (DATETIME).
  - [x] 1.1.3 — Create SQLAlchemy models for both tables.
  - [x] 1.1.4 — Write a DB initialization script that creates tables if they don't exist.

- [x] **1.2 — Complaint submission API**
  - [x] 1.2.1 — `POST /api/complaints` — accepts multipart form: image file, description text, latitude, longitude, citizen_severity. Validates all required fields. Saves image to disk, stores record in DB. Returns complaint ID + status.
  - [x] 1.2.2 — `GET /api/complaints` — returns list of complaints with filtering (category, severity, status, priority) and sorting (by priority descending, by date).
  - [x] 1.2.3 — `GET /api/complaints/{id}` — returns full complaint detail including priority factors and status history.
  - [x] 1.2.4 — `PATCH /api/complaints/{id}/status` — updates status (Reported → In Progress → Resolved). Appends to `status_history`. Rejects invalid transitions.

- [x] **1.3 — Dashboard summary API**
  - [x] 1.3.1 — `GET /api/dashboard/summary` — returns counts: total, high-priority, pending (Reported), in-progress, resolved.

### Phase 1 — Verification Tests

- [x] T1.1 — Run DB init script twice — second run doesn't error or duplicate tables. **Pass:** Idempotent schema creation.
- [x] T1.2 — `POST /api/complaints` with valid payload → 201, record exists in DB. **Pass:** Complaint ID returned, DB row matches input.
- [x] T1.3 — `POST /api/complaints` with missing required field → 422. **Pass:** Validation error with clear message.
- [x] T1.4 — `POST /api/complaints` — uploaded image is saved to disk at the returned path. **Pass:** File exists, is a valid image.
- [x] T1.5 — `GET /api/complaints` returns correct list; filtering by `status=Reported` returns only matching. **Pass:** JSON array, correct count.
- [x] T1.6 — `GET /api/complaints/{id}` returns correct complaint with all fields. **Pass:** Fields match what was submitted.
- [x] T1.7 — `PATCH /api/complaints/{id}/status` from Reported → In Progress → Resolved succeeds. **Pass:** Status updated, status_history rows created.
- [x] T1.8 — `PATCH /api/complaints/{id}/status` with invalid transition (e.g., Reported → Resolved) → 400. **Pass:** Error message explains valid transitions.
- [x] T1.9 — `GET /api/dashboard/summary` after inserting 5 test complaints (mixed statuses) returns correct counts. **Pass:** All counts match manual count.
- [x] T1.10 — SQLite DB file is portable — copy and open in a SQLite viewer shows correct data. **Pass:** Schema and data visible.

---

## Phase 2: Image Classification Model

Train the image classifier using transfer learning with MobileNetV2 (or verified alternative).

> **Note:** Phase 2 and Phase 3 can be developed **in parallel** since they are independent.

### Subtasks

- [x] **2.1 — Dataset preparation**
  - [x] 2.1.1 — Collect / download datasets for all 4 categories. Document source, size, and license for each.
  - [x] 2.1.2 — Organize into `data/images/{category}/` folder structure.
  - [x] 2.1.3 — Preprocess images: resize to model input size (e.g., 224×224), normalize pixel values. Use OpenCV or framework utilities.
  - [x] 2.1.4 — Split into train / validation / test sets (e.g., 70/15/15). Document split sizes.
  - [x] 2.1.5 — Apply data augmentation (rotation, flip, brightness) for training set to handle class imbalance.

- [x] **2.2 — Model training**
  - [x] 2.2.1 — Load pretrained MobileNetV2 (ImageNet weights), freeze base layers.
  - [x] 2.2.2 — Add custom classification head: GlobalAveragePooling → Dense(128, relu) → Dropout → Dense(4, softmax).
  - [x] 2.2.3 — Train on training set, validate on validation set. Track loss and accuracy curves.
  - [x] 2.2.4 — Fine-tune top layers if initial accuracy is insufficient.
  - [x] 2.2.5 — Save trained model weights to `backend/ml/models/image_model.*`.

- [x] **2.3 — Model evaluation**
  - [x] 2.3.1 — Evaluate on held-out test set: accuracy, precision, recall, F1-score per class.
  - [x] 2.3.2 — Generate and save confusion matrix.
  - [x] 2.3.3 — Document results in `docs/evaluation.md`. If a category performs poorly, document why and potential improvements.

- [x] **2.4 — Inference module**
  - [x] 2.4.1 — Create `backend/ml/image_classifier.py` with a `predict(image_path) → (category, confidence)` function.
  - [x] 2.4.2 — Module loads model once on startup, reuses for all predictions.
  - [x] 2.4.3 — Handle edge cases: corrupted image, unsupported format, very small image.

### Phase 2 — Verification Tests

- [x] T2.1 — Dataset folders contain images for all 4 categories, each with ≥ 50 images (or documented minimum). **Pass:** `ls data/images/*/` shows files.
- [x] T2.2 — Train/val/test split has no data leakage (no image in more than one split). **Pass:** Script verifies no filename overlap.
- [x] T2.3 — Model training completes without errors, loss decreases over epochs. **Pass:** Training log shows convergence.
- [x] T2.4 — Test-set accuracy ≥ baseline (document actual number, don't invent it). **Pass:** Metrics printed and logged.
- [x] T2.5 — Confusion matrix saved as image file. **Pass:** File exists, visually interpretable.
- [x] T2.6 — `predict("path/to/pothole.jpg")` returns `("Potholes / Damaged Roads", 0.XX)`. **Pass:** Correct category, float confidence.
- [x] T2.7 — `predict("path/to/corrupted_file")` raises/returns a handled error, not a crash. **Pass:** Graceful error handling.
- [x] T2.8 — `predict()` called 10 times in sequence: model is loaded only once (check timing or logs). **Pass:** No re-load overhead.
- [x] T2.9 — `docs/evaluation.md` exists with real metrics — no invented numbers. **Pass:** File review.

---

## Phase 3: Text Classification Model

Train the text classifier using TF-IDF + Logistic Regression (and optionally Random Forest).

> **Note:** Phase 2 and Phase 3 can be developed **in parallel** since they are independent.

### Subtasks

- [x] **3.1 — Dataset preparation**
  - [x] 3.1.1 — Collect or create text samples for each of the 4 categories. Document source and size.
  - [x] 3.1.2 — If generating synthetic data, document the method clearly and note it as synthetic.
  - [x] 3.1.3 — Clean text: lowercasing, punctuation removal, stopword removal (keep domain-relevant words).
  - [x] 3.1.4 — Split into train / test sets (e.g., 80/20).

- [x] **3.2 — Feature extraction & training**
  - [x] 3.2.1 — Fit TF-IDF vectorizer on training text. Save the fitted vectorizer.
  - [x] 3.2.2 — Train Logistic Regression classifier. Save model.
  - [x] 3.2.3 — (Optional) Train Random Forest classifier for comparison. Save model.
  - [x] 3.2.4 — Save models + vectorizer to `backend/ml/models/`.

- [x] **3.3 — Model evaluation**
  - [x] 3.3.1 — Evaluate on test set: accuracy, precision, recall, F1-score per class.
  - [x] 3.3.2 — Generate confusion matrix.
  - [x] 3.3.3 — If Random Forest was trained, compare side-by-side and pick the better model.
  - [x] 3.3.4 — Update `docs/evaluation.md` with text model results.

- [x] **3.4 — Inference module**
  - [x] 3.4.1 — Create `backend/ml/text_classifier.py` with a `predict(text) → (category, confidence)` function.
  - [x] 3.4.2 — Module loads TF-IDF vectorizer + model once on startup.
  - [x] 3.4.3 — Handle edge cases: empty string, very short text, non-English text.

### Phase 3 — Verification Tests

- [x] T3.1 — Text dataset has samples for all 4 categories. **Pass:** Count per category ≥ documented minimum.
- [x] T3.2 — TF-IDF + Logistic Regression training completes without errors. **Pass:** Model file saved.
- [x] T3.3 — Test-set metrics (accuracy, F1) computed and documented — no invented numbers. **Pass:** `docs/evaluation.md` updated.
- [x] T3.4 — `predict("There is a huge pothole on the main road")` returns Potholes category. **Pass:** Correct category.
- [x] T3.5 — `predict("Garbage piled up for days, bad smell")` returns Garbage category. **Pass:** Correct category.
- [x] T3.6 — `predict("")` or `predict("   ")` returns a handled result or error, not a crash. **Pass:** Graceful handling.
- [x] T3.7 — If Random Forest was trained, comparison table exists in `docs/evaluation.md`. **Pass:** Side-by-side metrics.
- [x] T3.8 — Inference latency per prediction < 100ms on local machine. **Pass:** Timed measurement.

---

## Phase 4: Category Resolution & Severity Assessment

Combine image + text predictions into a final category, then compute severity.

### Subtasks

- [x] **4.1 — Category resolution**
  - [x] 4.1.1 — Create `backend/ml/category_resolver.py` with function: `resolve(image_prediction, text_prediction) → final_category`.
  - [x] 4.1.2 — Implement the conflict-resolution rule decided in Phase 0 (subtask 0.1.3).
  - [x] 4.1.3 — Log the resolution decision (agreed / disagreed, which source won, confidences).

- [x] **4.2 — Severity assessment**
  - [x] 4.2.1 — Create `backend/ml/severity.py`.
  - [x] 4.2.2 — Implement text-cue scoring: category-specific keyword/phrase lookup per the table in plan.md Section 3.4. High cue → +2, Medium cue → +1, No cue → 0.
  - [x] 4.2.3 — Implement citizen-severity mapping: Minor → 0, Moderate → +1, Severe → +2.
  - [x] 4.2.4 — Implement image-based cue (Pothole & Garbage only): OpenCV proportion-of-affected-area heuristic. Large area → +1, otherwise → 0. Documented as coarse heuristic.
  - [x] 4.2.5 — Combine: `severity_points = text_cue + citizen_score + image_cue`. Map: 0–1 → Low, 2–3 → Medium, 4+ → High.
  - [x] 4.2.6 — Return detailed breakdown: `{severity: "High", points: 5, text_cue: 2, citizen: 2, image_cue: 1}`.

- [x] **4.3 — Integrate into complaint processing pipeline**
  - [x] 4.3.1 — After `POST /api/complaints`, trigger: image classification → text classification → category resolution → severity assessment. Update DB record with results.
  - [x] 4.3.2 — Ensure the pipeline runs synchronously within the request (for V1.0 simplicity) or as a clear background task if latency is too high.

### Phase 4 — Verification Tests

- [x] T4.1 — `resolve(("Pothole", 0.9), ("Pothole", 0.8))` → "Potholes / Damaged Roads". **Pass:** Agreement case works.
- [x] T4.2 — `resolve(("Garbage", 0.7), ("Pothole", 0.85))` → result follows the decided conflict rule. **Pass:** Documented rule applied.
- [x] T4.3 — Resolution logs show source confidences and decision reason. **Pass:** Log output verified.
- [x] T4.4 — Text cue: description with "deep pothole, accident" + category Pothole → text_cue = 2 (both are high-severity cues). **Pass:** Score matches rule.
- [x] T4.5 — Text cue: description with no severity keywords → text_cue = 0. **Pass:** Zero score.
- [x] T4.6 — Citizen severity: Minor → 0, Moderate → 1, Severe → 2. **Pass:** All three mappings correct.
- [x] T4.7 — Image cue on Pothole image with large affected area → image_cue = 1. **Pass:** Heuristic triggers.
- [x] T4.8 — Image cue on Waterlogging image → image_cue = 0 (not applicable). **Pass:** Category restriction works.
- [x] T4.9 — Combined: text_cue=2 + citizen=2 + image_cue=1 = 5 → "High". **Pass:** Correct severity.
- [x] T4.10 — Combined: text_cue=0 + citizen=0 + image_cue=0 = 0 → "Low". **Pass:** Correct severity.
- [x] T4.11 — Combined: text_cue=1 + citizen=1 + image_cue=0 = 2 → "Medium". **Pass:** Correct severity.
- [x] T4.12 — Submit a complaint via API → DB record has category, severity, severity_points filled. **Pass:** End-to-end pipeline.
- [x] T4.13 — Severity breakdown JSON is stored in DB and returned by `GET /api/complaints/{id}`. **Pass:** Detailed factors accessible.

---

## Phase 5: Duplicate / Nearby Complaint Grouping

Identify and group related complaints using location, text similarity, and category.

### Subtasks

- [x] **5.1 — Spatial grouping**
  - [x] 5.1.1 — Create `backend/ml/grouping.py`.
  - [x] 5.1.2 — Implement Haversine distance function between two lat/lng pairs.
  - [x] 5.1.3 — Implement DBSCAN-based spatial clustering on complaint coordinates. Define `eps` (e.g., 500m) and `min_samples` parameters (document chosen values).

- [x] **5.2 — Text similarity**
  - [x] 5.2.1 — Compute cosine similarity between TF-IDF vectors of complaint descriptions.
  - [x] 5.2.2 — Define similarity threshold (document the chosen value).

- [x] **5.3 — Combined grouping logic**
  - [x] 5.3.1 — Group complaints that share: same category AND (spatial cluster OR text similarity above threshold).
  - [x] 5.3.2 — Assign a `group_id` to grouped complaints and update `similar_count` for each.
  - [x] 5.3.3 — Re-run grouping when a new complaint is submitted (or batch periodically).

- [x] **5.4 — API exposure**
  - [x] 5.4.1 — `GET /api/complaints/{id}/similar` — returns list of complaints in the same group.
  - [x] 5.4.2 — Group info included in `GET /api/complaints/{id}` response.

### Phase 5 — Verification Tests

- [x] T5.1 — Haversine distance between two known coordinates matches expected value (±1m). **Pass:** Manual calculation verified.
- [x] T5.2 — DBSCAN clusters 3 complaints within 200m of each other into 1 group. **Pass:** Group IDs match.
- [x] T5.3 — DBSCAN keeps 2 complaints 5km apart in separate groups. **Pass:** Different group IDs.
- [x] T5.4 — Text similarity: two nearly identical descriptions → similarity > threshold. **Pass:** Cosine similarity checked.
- [x] T5.5 — Text similarity: unrelated descriptions → similarity < threshold. **Pass:** Below threshold.
- [x] T5.6 — Combined grouping: same category + nearby + similar text → grouped. **Pass:** Grouped correctly.
- [x] T5.7 — Combined grouping: same location but different category → NOT grouped. **Pass:** Separate groups.
- [x] T5.8 — `similar_count` for a grouped complaint reflects the correct count. **Pass:** Count matches.
- [x] T5.9 — `GET /api/complaints/{id}/similar` returns the correct related complaints. **Pass:** Correct list.
- [x] T5.10 — Submitting a new complaint near existing ones triggers re-grouping. **Pass:** Group updated.

---

## Phase 6: Explainable Priority Engine

Calculate and expose the priority score with its contributing factors.

### Subtasks

- [x] **6.1 — Priority calculation**
  - [x] 6.1.1 — Create `backend/ml/priority.py`.
  - [x] 6.1.2 — Implement normalization for each factor (0–1):
    - Severity: Low → 0.33, Medium → 0.67, High → 1.0.
    - Similar complaints: `min(count / cap, 1.0)` — define and document the cap.
    - Location importance: 1.0 if within radius of a sensitive location, 0.5 otherwise (or use the decided scheme from Phase 0).
    - Time since reporting: `min(days_elapsed / max_days, 1.0)` — define and document `max_days`.
  - [x] 6.1.3 — Apply formula: `Priority = 0.40 × Severity + 0.25 × Similar + 0.20 × Location + 0.15 × Time`.
  - [x] 6.1.4 — Return the score AND factor breakdown: `{score: 0.73, severity: {value: "High", normalized: 1.0, weight: 0.40, contribution: 0.40}, ...}`.

- [x] **6.2 — Integration**
  - [x] 6.2.1 — After severity & grouping are computed, calculate priority and store `priority_score` + `priority_factors` in the DB.
  - [x] 6.2.2 — Recalculate priority when grouping changes (new similar complaint found) or time elapses (could be a batch job or on-read).

- [x] **6.3 — Dashboard priority API**
  - [x] 6.3.1 — `GET /api/complaints` sorted by `priority_score` descending by default.
  - [x] 6.3.2 — Priority factors included in complaint detail response.

### Phase 6 — Verification Tests

- [x] T6.1 — Severity normalization: Low → 0.33, Medium → 0.67, High → 1.0. **Pass:** All three correct.
- [x] T6.2 — Similar-complaint normalization: 0 complaints → 0.0, at cap → 1.0. **Pass:** Boundary values correct.
- [x] T6.3 — Location importance: complaint at a known sensitive location → 1.0. **Pass:** Lookup works.
- [x] T6.4 — Time normalization: 0 days → 0.0, max_days → 1.0. **Pass:** Boundary values correct.
- [x] T6.5 — Formula: hand-calculated example matches code output. **Pass:** Manual check against formula.
- [x] T6.6 — Priority factors JSON contains all 4 factors with value, normalized, weight, contribution. **Pass:** Structure validated.
- [x] T6.7 — Two complaints: one High severity + 8 similar + sensitive location + 10 days; one Low severity + 0 similar + non-sensitive + 1 day. First has higher priority. **Pass:** Correct ordering.
- [x] T6.8 — `GET /api/complaints?sort=priority` returns complaints in descending priority order. **Pass:** Order verified.
- [x] T6.9 — Dashboard shows contributing factors, not just a number. **Pass:** API response includes breakdown.
- [x] T6.10 — Adding a new similar complaint to a group updates the priority of existing complaints in that group. **Pass:** Scores recalculated.

---

## Phase 7: Frontend — Citizen Submission Interface

Build the citizen-facing complaint submission form.

> **Note:** Phase 7 can begin as soon as Phase 1 is complete and can progress **in parallel** with Phases 2–6.

### Subtasks

- [x] **7.1 — Complaint form**
  - [x] 7.1.1 — Create submission page with fields: image upload (with preview), text description (textarea), location picker (map click or manual lat/lng), citizen severity dropdown (Minor / Moderate / Severe).
  - [x] 7.1.2 — Client-side validation: all fields required, image must be an image file, description min length (e.g., 10 chars).
  - [x] 7.1.3 — Submit form data to `POST /api/complaints` via multipart fetch/axios call.
  - [x] 7.1.4 — Show success confirmation with complaint ID after submission.
  - [x] 7.1.5 — Show meaningful error messages on failure (server errors, validation errors).

- [x] **7.2 — Location picker**
  - [x] 7.2.1 — Integrate Leaflet map for location selection.
  - [x] 7.2.2 — User clicks on map → lat/lng populated into the form.
  - [x] 7.2.3 — Show a marker at the selected location.
  - [x] 7.2.4 — (Optional) Reverse geocode to display a readable address.

- [x] **7.3 — Styling & UX**
  - [x] 7.3.1 — Clean, accessible, mobile-friendly layout.
  - [x] 7.3.2 — Loading indicator during submission (API may take a few seconds due to ML processing).

### Phase 7 — Verification Tests

- [x] T7.1 — Form renders with all required fields visible. **Pass:** Visual inspection.
- [x] T7.2 — Submitting with empty fields shows validation errors. **Pass:** Client-side validation fires.
- [x] T7.3 — Uploading a non-image file is rejected. **Pass:** Error message shown.
- [x] T7.4 — Clicking on the Leaflet map populates lat/lng in the form. **Pass:** Values appear in fields / state.
- [x] T7.5 — Submitting a valid complaint: success message shown with complaint ID. **Pass:** ID visible on screen.
- [x] T7.6 — After submission, complaint appears in `GET /api/complaints`. **Pass:** API returns the new complaint.
- [x] T7.7 — Loading indicator appears during submission and disappears after response. **Pass:** UX verified.
- [x] T7.8 — Form is usable on a narrow viewport (mobile width ≈ 375px). **Pass:** Responsive layout works.
- [x] T7.9 — Submitting an image + description + map location + severity "Severe" → DB record has all fields correctly populated including ML-computed category and severity. **Pass:** Full pipeline end-to-end from UI.

---

## Phase 8: Frontend — Authority Dashboard

Build the authority-facing dashboard with complaint table, filters, status management, and map.

### Subtasks

- [x] **8.1 — Dashboard overview**
  - [x] 8.1.1 — Summary cards at top: Total Complaints, High Priority, Pending (Reported), In Progress, Resolved. Data from `GET /api/dashboard/summary`.
  - [x] 8.1.2 — Auto-refresh or manual refresh button.

- [x] **8.2 — Complaint table**
  - [x] 8.2.1 — Table columns: ID, Category, Location (lat/lng or name), Severity, Priority Score, Similar Count, Status, Timestamp.
  - [x] 8.2.2 — Rows color-coded or badged by priority level (High = red, Medium = yellow, Low = green).
  - [x] 8.2.3 — Click on a row → expand or navigate to detail view showing: image, description, severity breakdown, priority factors, similar complaints, status history.

- [x] **8.3 — Filtering & sorting**
  - [x] 8.3.1 — Filter dropdowns: Category (all 4 + "All"), Severity (Low/Medium/High + "All"), Status (Reported/In Progress/Resolved + "All"), Priority level (High/Medium/Low + "All").
  - [x] 8.3.2 — Default sort: priority descending. Toggle to sort by date.
  - [x] 8.3.3 — Filters compose: e.g., category = Pothole AND status = Reported.

- [x] **8.4 — Status management**
  - [x] 8.4.1 — Status update button/dropdown on each complaint: Reported → In Progress → Resolved.
  - [x] 8.4.2 — Calls `PATCH /api/complaints/{id}/status`.
  - [x] 8.4.3 — Dashboard updates after status change (optimistic or refetch).
  - [x] 8.4.4 — Status history visible in complaint detail view.

- [x] **8.5 — Interactive map**
  - [x] 8.5.1 — Leaflet map showing all complaint locations.
  - [x] 8.5.2 — Markers color-coded by priority level (High = red, Medium = orange, Low = green).
  - [x] 8.5.3 — Click on marker → popup showing complaint summary (ID, category, severity, status).
  - [x] 8.5.4 — Map filters sync with table filters (filtering by category hides non-matching markers too).

### Phase 8 — Verification Tests

- [x] T8.1 — Dashboard summary cards show correct counts (verified against DB). **Pass:** Numbers match query.
- [x] T8.2 — Complaint table displays all complaints with correct data in each column. **Pass:** Spot-check 5 rows against DB.
- [x] T8.3 — Clicking a row shows detail view with image, description, severity breakdown, priority factors. **Pass:** All fields present.
- [x] T8.4 — Filter by category "Garbage" → only Garbage complaints shown in table AND map. **Pass:** Count matches.
- [x] T8.5 — Filter by severity "High" + status "Reported" → only matching complaints shown. **Pass:** Composite filter works.
- [x] T8.6 — Default sort is by priority descending. **Pass:** First row has highest priority.
- [x] T8.7 — Changing status from Reported → In Progress: API call succeeds, row updates, summary card counts update. **Pass:** All three verified.
- [x] T8.8 — Status history shows the transition timestamps. **Pass:** History entries visible.
- [x] T8.9 — Map shows markers at correct lat/lng positions. **Pass:** Visual check against data.
- [x] T8.10 — Map markers are color-coded by priority. **Pass:** Red/orange/green visible.
- [x] T8.11 — Clicking a map marker shows popup with complaint info. **Pass:** Popup content correct.
- [x] T8.12 — Map filters sync with table filters. **Pass:** Markers and rows match.

---

## Phase 9: End-to-End Integration & System Testing

Wire everything together and verify the complete workflow from citizen submission to authority action.

### Subtasks

- [ ] **9.1 — End-to-end pipeline verification**
  - [ ] 9.1.1 — Submit 10+ test complaints covering all 4 categories, varying severities, and both nearby and distant locations.
  - [ ] 9.1.2 — Verify each complaint flows through: submission → image classification → text classification → category resolution → severity assessment → grouping → priority calculation → appears on dashboard → appears on map.
  - [ ] 9.1.3 — Verify grouped complaints share `group_id` and correct `similar_count`.
  - [ ] 9.1.4 — Verify priority ordering on dashboard makes intuitive sense for the test data.

- [ ] **9.2 — Status workflow**
  - [ ] 9.2.1 — Walk a complaint through Reported → In Progress → Resolved and verify status history.
  - [ ] 9.2.2 — Verify dashboard summary cards update correctly.

- [ ] **9.3 — Edge cases & error handling**
  - [ ] 9.3.1 — Submit complaint with very large image (>10MB) — system handles gracefully (reject or resize).
  - [ ] 9.3.2 — Submit complaint with minimal description (1–2 words) — text classifier handles gracefully.
  - [ ] 9.3.3 — Submit complaint at coordinates (0, 0) or extreme values — system handles gracefully.
  - [ ] 9.3.4 — What happens if the ML model file is missing on startup? — clear error message, not a silent failure.

- [ ] **9.4 — Performance sanity check**
  - [ ] 9.4.1 — Measure end-to-end latency: complaint submission to result available on dashboard.
  - [ ] 9.4.2 — Dashboard loads within a reasonable time with 50+ complaints in DB.

### Phase 9 — Verification Tests

- [ ] T9.1 — 10 test complaints submitted → all 10 visible on dashboard with category, severity, priority. **Pass:** 100% pipeline completion.
- [ ] T9.2 — At least 2 nearby same-category complaints are grouped together. **Pass:** Grouping visible in detail view.
- [ ] T9.3 — Priority ordering: a High-severity, multi-complaint, sensitive-location issue ranks higher than a Low-severity isolated issue. **Pass:** Correct relative order.
- [ ] T9.4 — Full status lifecycle (Reported → In Progress → Resolved) works, status history shows 2 transitions. **Pass:** History has 2 entries.
- [ ] T9.5 — Dashboard summary cards match manual count of test data. **Pass:** All 5 counts correct.
- [ ] T9.6 — Map shows all 10 complaints with correct color-coded markers. **Pass:** Visual verification.
- [ ] T9.7 — Complaint detail view shows: image, description, category, severity breakdown, priority factors, similar complaints, status history. **Pass:** All sections present.
- [ ] T9.8 — Large image submission handled gracefully. **Pass:** No crash, appropriate response.
- [ ] T9.9 — Empty/short description handled gracefully. **Pass:** No crash, fallback behavior documented.
- [ ] T9.10 — End-to-end submission latency < 30 seconds on local machine. **Pass:** Measured and logged.
- [ ] T9.11 — Dashboard with 50+ complaints loads in < 5 seconds. **Pass:** Measured and logged.

---

## Phase 10: Evaluation & Documentation

Formal evaluation of ML models and system performance. Final documentation.

### Subtasks

- [ ] **10.1 — ML model evaluation (formal)**
  - [ ] 10.1.1 — Image classifier: report final accuracy, precision, recall, F1 per class, confusion matrix on test set.
  - [ ] 10.1.2 — Text classifier: report final accuracy, precision, recall, F1 per class, confusion matrix on test set.
  - [ ] 10.1.3 — If any metric was not computed, state "Not yet evaluated" — do not invent numbers.

- [ ] **10.2 — Severity validation**
  - [ ] 10.2.1 — Select 20–30 complaints. Have a few human reviewers rate each as Low / Medium / High.
  - [ ] 10.2.2 — Compute agreement rate between system severity and human ratings.
  - [ ] 10.2.3 — Document results and analysis.

- [ ] **10.3 — Priority validation**
  - [ ] 10.3.1 — Select a sample of complaints. Have human reviewers rank them by priority.
  - [ ] 10.3.2 — Compute Spearman correlation between system ranking and human ranking.
  - [ ] 10.3.3 — Document results and analysis.

- [ ] **10.4 — Documentation**
  - [ ] 10.4.1 — Update `docs/evaluation.md` with all final metrics.
  - [ ] 10.4.2 — Write `README.md` with: project overview, setup instructions, how to run, architecture diagram, API reference, known limitations.
  - [ ] 10.4.3 — Document all design decisions in `docs/decisions.md`.
  - [ ] 10.4.4 — Ensure code has adequate inline comments and docstrings.

### Phase 10 — Verification Tests

- [ ] T10.1 — `docs/evaluation.md` contains image classifier metrics with real numbers. **Pass:** No placeholder values.
- [ ] T10.2 — `docs/evaluation.md` contains text classifier metrics with real numbers. **Pass:** No placeholder values.
- [ ] T10.3 — Confusion matrices (image & text) saved and referenced in docs. **Pass:** Files exist.
- [ ] T10.4 — Severity validation: agreement rate computed for 20–30 complaints. **Pass:** Result documented.
- [ ] T10.5 — Priority validation: Spearman correlation computed. **Pass:** Result documented.
- [ ] T10.6 — `README.md` has setup instructions that a new developer can follow to run the project. **Pass:** Tested by following the README from scratch.
- [ ] T10.7 — Following `README.md` instructions: `pip install`, `npm install`, start backend, start frontend — all succeed. **Pass:** Full local setup works.
- [ ] T10.8 — All Python modules have docstrings on public classes and functions. **Pass:** Spot-check 10 modules.

---

## Quick Reference

| Phase | Focus | Subtasks | Tests | Dependencies |
|-------|-------|----------|-------|-------------|
| 0 | Bootstrap & Decisions | 11 | 6 | — |
| 1 | Database & API | 9 | 10 | Phase 0 |
| 2 | Image Classifier | 14 | 9 | Phase 1 |
| 3 | Text Classifier | 11 | 8 | Phase 1 |
| 4 | Category Resolution & Severity | 8 | 13 | Phases 2, 3 |
| 5 | Duplicate Grouping | 10 | 10 | Phase 4 |
| 6 | Priority Engine | 7 | 10 | Phase 5 |
| 7 | Citizen Frontend | 8 | 9 | Phase 1 |
| 8 | Authority Dashboard | 14 | 12 | Phase 6 |
| 9 | End-to-End Testing | 10 | 11 | Phases 7, 8 |
| 10 | Evaluation & Docs | 10 | 8 | Phase 9 |
| **Totals** | | **112 items** | **106 items** | |

> **Parallelizable work:**
> - Phase 2 (Image) and Phase 3 (Text) can run in parallel.
> - Phase 7 (Citizen Frontend) can start after Phase 1 and run in parallel with Phases 2–6.
