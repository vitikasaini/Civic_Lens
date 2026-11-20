# CivicLens

**AI‑assisted civic‑issue management platform** – a full‑stack web application that lets citizens report local problems (potholes, garbage, water‑logging, street‑light faults, etc.) and gives municipal authorities a live dashboard to triage, prioritize, and resolve those reports.

---

## Table of Contents
- [Demo](#demo)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
  - [1️⃣ Clone the repo](#1-clone-the-repo)
  - [2️⃣ Backend (FastAPI)](#2-backend-fastapi)
  - [3️⃣ Frontend (React + Vite)](#3-frontend-react--vite)
  - [4️⃣ Build & Run locally](#4-build--run-locally)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [CI / GitHub Actions](#ci--github-actions)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Demo
> **⚡️ Live demo:** `https://civiclens-demo.example.com` *(placeholder – replace with your deployed URL)*

![CivicLens dashboard screenshot](https://raw.githubusercontent.com/vitikasaini/Civic_Lens/main/.github/screenshots/dashboard.png)

---

## Features
| Citizen side | Authority side |
|--------------|----------------|
| 📸 **Photo upload** – drag‑and‑drop or file picker (JPEG/PNG/WEBP/BMP ≤ 10 MB) | 📊 **KPI cards** – total reports, high‑priority, pending, in‑progress, resolved |
| 📝 **Rich description** – auto‑character count & validation | 🗺️ **Interactive map** (Leaflet) – heat‑map of reports and priority hotspots |
| 🎚️ **Severity rating** (Low / Medium / High) | 🎯 **Quick status updates** – click‑to‑change from “Reported → In Progress → Resolved” |
| 📍 **Location picker** – click on a map to set latitude/longitude | 📂 **Detailed complaint view** – modal with AI‑derived category, severity, priority score |
| ✅ **Client‑side validation** – placeholder, min‑length, image type/size checks | 🛠️ **Admin‑only API** – FastAPI endpoints secured with CORS, upload handling, SQLite DB |
| ✨ **Responsive UI** – built with React 19, Tailwind‑styled components | 📡 **Health & metrics endpoint** – `/health` returns component status |

---

## Architecture Overview
```
civicLens/
├─ backend/                     # FastAPI server (Python)
│   ├─ api/                     # routers: complaints, dashboard
│   ├─ models/                  # Pydantic schemas & SQLAlchemy models
│   ├─ main.py                  # entry point, mounts static /uploads
│   └─ init_db.py               # SQLite DB creation on startup
│
├─ frontend/                    # React + Vite SPA
│   ├─ src/
│   │   ├─ components/          # CitizenSubmission, AuthorityDashboard, etc.
│   │   ├─ App.jsx
│   │   └─ main.jsx
│   ├─ public/                  # static assets (favicon, icons)
│   ├─ index.html
│   └─ tailwind.config.js
│
├─ .github/workflows/ci.yml     # GitHub Actions CI (tests + build)
├─ requirements.txt             # Python deps
├─ package.json & package-lock.json
└─ README.md (this file)
```

*The FastAPI server serves the built React SPA at `/app` and static uploads at `/uploads`.*

---

## Prerequisites
| Tool | Minimum version |
|------|-----------------|
| **Node.js** | v20.x (includes npm) |
| **Python** | v3.11 |
| **Git** | any recent version |
| **PowerShell** | v5.1+ (Windows) – or use `cmd`/`bash` |
| **SQLite** | bundled with Python – no extra install needed |

> **Optional:** Docker (if you prefer containerised development).

---

## Installation & Setup
### 1️⃣ Clone the repo
```powershell
git clone https://github.com/vitikasaini/Civic_Lens.git
cd Civic_Lens
```
### 2️⃣ Backend (FastAPI)
```powershell
# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # PowerShell (or activate.bat from cmd)

# Install Python dependencies
pip install -r requirements.txt
```
### 3️⃣ Frontend (React + Vite)
```powershell
cd frontend
npm install          # creates node_modules and package-lock.json
npm run build        # produces ./dist (production assets)
cd ..                # back to project root
```
> **Tip:** If you ever need a clean install, delete `frontend/node_modules` and run `npm ci` (requires a lockfile).
### 4️⃣ Build & Run locally
```powershell
# (Back in the project root, with the venv still active)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
The server will output something like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```
Open a browser → `http://127.0.0.1:8000/app`

---

## Running the Application
| Action | Command | Description |
|--------|---------|-------------|
| **Start API only** | `python -m uvicorn backend.main:app --reload` | Auto‑reload on code changes (dev mode). |
| **Start API + hot‑reload frontend** | `npm run dev` (inside `frontend/`) **and** `uvicorn …` (in another terminal) | Vite dev server runs on `http://localhost:5173`; API on `127.0.0.1:8000`. CORS is already configured for both origins. |
| **Production** | `npm run build` **then** `uvicorn backend.main:app --host 0.0.0.0 --port 8000` | Serves the compiled SPA from `frontend/dist`. |

---

## Testing
### Backend
```powershell
# Ensure venv is active
pytest backend/tests
```
All tests should pass (`95 passed, 7 warnings` as of the latest commit).

### Frontend
> No explicit tests are in the repo yet, but you can add Jest / Playwright later.
```bash
cd frontend
npm run test            # (if you add a test script)
```
---

## CI / GitHub Actions
A CI workflow (`.github/workflows/ci.yml`) runs on every push:
1. **Install** Python & Node dependencies.
2. **Run** backend tests via `pytest`.
3. **Build** the React app (`npm ci && npm run build`).
4. **Upload** the `dist/` folder as an artifact (useful for downstream deployment jobs).
You can view the pipeline status on the **Actions** tab of the repo.

---

## Contributing
1. **Fork** the repository.
2. **Create a feature branch** (`git checkout -b feature/awesome-thing`).
3. **Make your changes** – run `npm ci && npm run build` and `pytest` to ensure everything still passes.
4. **Commit** with clear messages (`git commit -m "feat: add <description>"`).
5. **Push** to your fork and open a **Pull Request**.

Please adhere to the coding style enforced by **oxlint** (run `npm run lint` locally) and **flake8**/**mypy** for Python (installed via `pip install oxlint` if desired).

---

## License
This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

## Acknowledgements
- **FastAPI** – high‑performance Python web framework.
- **React 19** – UI library, used with **Vite** for fast builds.
- **Leaflet** – interactive maps.
- **Tailwind CSS** – utility‑first styling (used for rapid UI prototyping).
- **oxlint** – JavaScript/TypeScript linter that powers the repository’s CI checks.
- **GitHub Actions** – automated CI pipeline.

---

### Quick “One‑Liner” to spin up the whole stack (PowerShell)
```powershell
git clone https://github.com/vitikasaini/Civic_Lens.git; cd Civic_Lens;
python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt;
cd frontend; npm install; npm run build; cd ..;
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/app` and you’re ready to report and manage civic issues!

---

**Enjoy building a smarter, more responsive city with CivicLens!**