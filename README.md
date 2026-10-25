# CivicLens V1.0

> **AI-Assisted Civic Issue Management & Decision-Support Platform**  
> Multimodal categorization, rule-based severity scoring, spatial/semantic duplicate grouping, and explainable priority dispatch. Zero external cloud dependencies.

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-emerald.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.2-cyan.svg)](https://react.dev/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-green.svg)](https://leafletjs.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.21-orange.svg)](https://www.tensorflow.org/)

---

## 1. Overview

Civic complaints submitted to municipal portals frequently languish in unprocessed backlogs due to missing categorization, inconsistent citizen descriptions, duplicate reports for the same incident, and arbitrary first-come-first-served scheduling.

**CivicLens** solves this by implementing an end-to-end, reproducible, offline-first pipeline:
1. **Multimodal Classification:** Dual-pipeline classification combining transfer-learning image inference (MobileNetV2) and NLP feature extraction (TF-IDF + Logistic Regression) across 4 core municipal issue categories:
   - *Potholes / Damaged Roads*
   - *Garbage Accumulation*
   - *Waterlogging / Drainage Problems*
   - *Streetlight Faults*
2. **Transparent Severity Assessment:** Predictable rule-based scoring combining category-specific text cues, citizen inputs, and OpenCV contour-based area heuristics.
3. **Duplicate & Nearby Grouping:** Automated spatial clustering (Haversine metric + DBSCAN) fused with semantic text similarity to group related reports.
4. **Explainable Priority Engine:** Mathematical multi-factor formula calculating actionable dispatch scores with full factor breakdowns.
5. **Interactive Authority & Citizen Interfaces:** Modern React + Leaflet map interfaces for citizen submissions and municipal dispatch oversight.

---

## 2. System Architecture

```text
                             +------------------------+
                             |  Citizen Web Form / UI |
                             +------------------------+
                                         |
                                         | Multipart POST
                                         v
+---------------------------------------------------------------------------------+
|                                FastAPI Backend                                  |
|                                                                                 |
|   +-----------------------+              +----------------------------------+   |
|   |   Image Classifier    |              |         Text Classifier          |   |
|   |  (MobileNetV2 .keras) |              | (TF-IDF + Logistic Regression)   |   |
|   +-----------------------+              +----------------------------------+   |
|               \                                     /                           |
|                \                                   /                            |
|                 v                                 v                             |
|          +-----------------------------------------------+                      |
|          |    Multimodal Category Conflict Resolver      |                      |
|          +-----------------------------------------------+                      |
|                                  |                                              |
|                                  v                                              |
|          +-----------------------------------------------+                      |
|          |     Rule-Based Severity Assessment Engine     |                      |
|          +-----------------------------------------------+                      |
|                                  |                                              |
|                                  v                                              |
|          +-----------------------------------------------+                      |
|          |     Duplicate / Proximity Grouping (DBSCAN)   |                      |
|          +-----------------------------------------------+                      |
|                                  |                                              |
|                                  v                                              |
|          +-----------------------------------------------+                      |
|          |          Explainable Priority Engine          |                      |
|          +-----------------------------------------------+                      |
|                                  |                                              |
+----------------------------------|----------------------------------------------+
                                   v
                      +-------------------------+
                      |   SQLite Database ORM   |
                      +-------------------------+
                                   |
                                   v
                      +-------------------------+
                      |   Authority Dashboard   |
                      |   (React + Leaflet Map) |
                      +-------------------------+
```

---

## 3. Technology Stack

- **Backend:** Python 3.13, FastAPI, Uvicorn, SQLAlchemy, Pydantic V2, SQLite.
- **Machine Learning & Computer Vision:** TensorFlow 2.21 / Keras 3.15, Scikit-learn, OpenCV (`cv2`), NumPy, SciPy.
- **Frontend:** React 19, Vite, Leaflet, HTML5 Canvas.
- **Testing:** Pytest, FastApi TestClient.

---

## 4. Quick Start (Local Setup)

### 4.1 Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Node.js 18+ & npm

### 4.2 Backend Setup
```bash
# 1. Clone repository
git clone https://github.com/your-org/civicLens.git
cd civicLens

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # On Windows
# source venv/bin/activate # On Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize Database
python scripts/init_db.py

# 5. Start Backend API Server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
API docs available at: `http://127.0.0.1:8000/docs`

### 4.3 Frontend Setup
```bash
# In a new terminal:
cd frontend
npm install
npm run build   # Production bundle (served directly by FastAPI at http://127.0.0.1:8000/app)

# Or for local development with Hot-Module-Replacement:
npm run dev     # Starts Vite dev server at http://localhost:5173
```

---

## 5. Mathematical Formulations

### 5.1 Explainable Priority Engine
Priority is calculated as a normalized linear combination:
$$\text{Priority Score} = 0.40 \cdot S + 0.25 \cdot D + 0.20 \cdot L + 0.15 \cdot T$$

Where:
- **Severity ($S \in [0, 1]$):** Low $\to 0.33$, Medium $\to 0.67$, High $\to 1.00$.
- **Similar Count ($D \in [0, 1]$):** $\min(\frac{\text{similar\_count}}{10}, 1.0)$.
- **Location Importance ($L \in [0, 1]$):** $1.00$ if within $200\text{m}$ radius of any sensitive municipal landmark (Hospitals, Schools, Transit Hubs); $0.50$ otherwise.
- **Time Elapsed ($T \in [0, 1]$):** $\min(\frac{\text{days\_unresolved}}{30}, 1.0)$.

### 5.2 Severity Assessment Rule
$$\text{Points} = \text{Text Cue Score} + \text{Citizen Severity Points} + \text{Image Heuristic}$$
- **Text Cue:** $+2$ for high-urgency keywords ("accident", "caved in", "stench"), $+1$ for medium ("bumpy", "flickering"), $0$ default.
- **Citizen Score:** Minor $= 0$, Moderate $= 1$, Severe $= 2$.
- **Image Heuristic:** $+1$ if OpenCV contour area of road/garbage obstruction exceeds $15\%$ of frame; $0$ otherwise.
- **Mapping:** $0 - 1 \to \text{Low}$, $2 - 3 \to \text{Medium}$, $4+ \to \text{High}$.

---

## 6. Formal Evaluation Results

All evaluation figures are actual measured numbers from local held-out test splits (see [`docs/evaluation.md`](docs/evaluation.md)):

| Component | Benchmark Metric | Measured Result |
|---|---|---|
| **Text Classifier** | Test Set F1-Score (Macro) | **1.0000** (160 held-out samples) |
| **Image Classifier** | Test Set Accuracy (MobileNetV2) | **1.0000** (36 held-out benchmark images) |
| **Severity Scoring** | Human Reviewer Agreement Rate | **100.00%** (25 benchmark cases, $\kappa = 1.0000$) |
| **Priority Ranking** | Spearman Rank Correlation ($\rho$) | **0.9929** ($p = 2.17 \times 10^{-13}$, 15 multi-criteria scenarios) |
| **System Latency** | Full Multimodal ML Pipeline | **< 3.5s** per submission |

---

## 7. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/complaints` | Submit new complaint (multipart form: image, text, lat, lon, severity) |
| `GET` | `/api/complaints` | List complaints with category, severity, status, and priority filters |
| `GET` | `/api/complaints/{id}` | Full detail view with explainable factor breakdown & history |
| `GET` | `/api/complaints/{id}/similar` | List related duplicate/nearby complaints in the same group |
| `PATCH` | `/api/complaints/{id}/status` | Transition status (`Reported` $\to$ `In Progress` $\to$ `Resolved`) |
| `GET` | `/api/dashboard/summary` | KPI aggregate counts for authority oversight |
| `GET` | `/app` | Serves compiled React Single Page Application |

---

## 8. Verification & Test Suite

CivicLens includes 83 automated verification tests across all development phases:
```bash
# Run complete test suite
pytest -v backend/tests/
```
```text
======================= 83 passed in 23.22s =======================
```

---

## 9. Known Limitations & Roadmap

- **V1.0 Scope:** Focuses on immediate triage, classification, and explainable dispatch.
- **V2.0 Planned Enhancements:**
  - Automated worker dispatch routing with road network graph traversal.
  - Multi-lingual translation for citizen reports in regional languages.
  - Periodic cron job for time-elapsed priority decay/escalation.
