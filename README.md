# CivicLens

**AI‑assisted civic‑issue management platform** – a full‑stack web application that lets citizens report local problems (potholes, garbage, water‑logging, street‑light faults, etc.) and gives municipal authorities a live dashboard to triage, prioritize, and resolve those reports.

---

## Table of Contents
- [New Features in V1.0](#new-features-in-v10)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Installation & Setup](#installation--setup)
  - [1️⃣ Clone the repo](#1-clone-the-repo)
  - [2️⃣ Backend (FastAPI)](#2-backend-fastapi)
  - [3️⃣ Frontend (React + Vite)](#3-frontend-react--vite)
  - [4️⃣ Build & Run locally](#4-build--run-locally)
- [Authority Account Setup](#authority-account-setup)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## New Features in V1.0
- 🔐 **Role-Based Authentication (RBAC):** Secure JWT authentication with citizen and authority roles. Registration automatically creates citizen accounts.
- 👤 **Complaint Ownership:** Complaints are linked to citizens (`citizen_id`). Citizens can access their submitted complaints via `/api/complaints/my` and track real-time resolution timelines.
- 🔔 **Persistent Notifications:** Status changes (`Reported` → `In Progress` → `Resolved`) trigger atomic in-app notifications for the owning citizen with unread counts and read tracking.
- 📍 **Reverse Geocoding:** Integration with OpenStreetMap Nominatim automatically resolves latitude/longitude into human-readable addresses, cached in the database without blocking submissions.
- 🏛️ **Separated Citizen & Authority Dashboards:**
  - **Citizen Dashboard:** Welcome screen, issue submission form, own complaints list with status badges, verified status history timeline, and real-time notification bell.
  - **Authority Dashboard:** Full KPI overview, issue filtering, priority hotspot map with address tooltips, location column, interactive detail modal with Leaflet map view, and status workflow controls.

---

## Architecture Overview
```
civicLens/
├─ backend/                     # FastAPI server (Python)
│   ├─ api/                     # routers: auth, complaints, dashboard, notifications
│   ├─ ml/                      # classification, grouping, and priority scoring
│   ├─ models/                  # Pydantic schemas & SQLAlchemy ORM models
│   ├─ main.py                  # entry point, mounts static /uploads and React SPA
│   └─ tests/                   # automated pytest suite
│
├─ frontend/                    # React 19 + Vite SPA
│   ├─ src/
│   │   ├─ components/          # AuthorityDashboard, CitizenSubmission, NotificationBell, etc.
│   │   ├─ context/             # AuthContext (JWT management & authenticated fetch)
│   │   ├─ pages/               # CitizenDashboard, LoginPage, RegisterPage
│   │   ├─ App.jsx              # Role-based router & protected route guards
│   │   └─ main.jsx
│   ├─ public/                  # static assets (favicon, icons)
│   └─ index.html
│
├─ requirements.txt             # Python dependencies
└─ README.md                    # Project documentation
```

*The FastAPI server serves API endpoints at `/api/*`, static uploads at `/uploads/*`, and the compiled React SPA.*

---

## Prerequisites
| Tool | Minimum version |
|------|-----------------|
| **Node.js** | v20.x (includes npm) |
| **Python** | v3.11+ |
| **Git** | any recent version |
| **PowerShell** | v5.1+ (Windows) – or `bash` / `zsh` |
| **SQLite** | bundled with Python – zero additional setup |

---

## Environment Variables
Configure these environment variables in your environment or a `.env` file in the project root:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `JWT_SECRET` | Recommended | Secret key for signing JSON Web Tokens | `civiclens_dev_secret_change_me` |
| `AUTHORITY_EMAIL` | For Seed | Email for the municipal authority admin | `admin@civiclens.local` |
| `AUTHORITY_PASSWORD` | For Seed | Password for the municipal authority admin | `Admin123!` |
| `DATABASE_URL` | Optional | SQLAlchemy database connection string | `sqlite:///civiclens.db` |
| `SMTP_HOST` | Optional | Future email transport server hostname | None (In-app notifications active) |
| `SMTP_PORT` | Optional | Future email transport server port | `587` |
| `SMTP_USER` | Optional | Future email transport username | None |
| `SMTP_PASSWORD` | Optional | Future email transport password | None |

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
.\venv\Scripts\Activate.ps1   # PowerShell (or source venv/bin/activate on Linux/macOS)

# Install Python dependencies
pip install -r requirements.txt
```

### 3️⃣ Frontend (React + Vite)
```powershell
cd frontend
npm install          # creates node_modules and package-lock.json
npm run build        # produces ./dist (production assets)
cd ..                # back to project root
```

### 4️⃣ Build & Run locally
```powershell
# (With the venv active)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open a browser → `http://127.0.0.1:8000/app` or `http://127.0.0.1:8000/login`

---

## Authority Account Setup
Authority accounts cannot be self-registered via the public registration form (which strictly creates citizen accounts). Authority credentials are seeded automatically on backend startup using environment variables.

1. Set the authority environment variables before starting the server:
   ```powershell
   $env:AUTHORITY_EMAIL="admin@civiclens.local"
   $env:AUTHORITY_PASSWORD="Admin123!"
   ```
2. Start the FastAPI server:
   ```powershell
   python -m uvicorn backend.main:app --reload
   ```
3. Navigate to `http://127.0.0.1:8000/login` and sign in using `admin@civiclens.local` and `Admin123!`.
4. You will automatically be redirected to `/authority` (the Authority Dashboard).

---

## Running the Application
| Action | Command | Description |
|--------|---------|-------------|
| **Start API only** | `python -m uvicorn backend.main:app --reload` | Auto‑reload on code changes (dev mode). |
| **Start API + hot‑reload frontend** | `npm run dev` (inside `frontend/`) **and** `uvicorn …` | Vite dev server runs on `http://localhost:5173`; API on `127.0.0.1:8000`. |
| **Production** | `npm run build` (in `frontend/`) **then** `uvicorn backend.main:app --host 0.0.0.0 --port 8000` | Serves the compiled SPA from `frontend/dist`. |

---

## API Reference
The API documentation is interactively available via Swagger UI at `/docs` and ReDoc at `/redoc`.

### Authentication
- `POST /api/auth/register` – Citizen account registration (returns JWT).
- `POST /api/auth/login` – Login with email and password (returns JWT).

### Complaints
- `POST /api/complaints` – Submit a new complaint with an uploaded image (Requires Citizen).
- `GET /api/complaints/my` – List complaints submitted by the authenticated citizen (Requires Citizen).
- `GET /api/complaints` – List and filter all complaints (Requires Authority).
- `GET /api/complaints/{id}` – Get complaint details and status history (Owner or Authority).
- `GET /api/complaints/{id}/similar` – Get duplicate / grouped complaints.
- `PATCH /api/complaints/{id}/status` – Transition complaint status (`Reported` → `In Progress` → `Resolved`) (Requires Authority).

### Dashboard
- `GET /api/dashboard/summary` – Get KPI summary metrics (total, pending, high priority, in-progress, resolved) (Requires Authority).

### Notifications
- `GET /api/notifications` – List authenticated user's notifications and unread count.
- `PATCH /api/notifications/{id}/read` – Mark an individual notification as read.
- `PATCH /api/notifications/read-all` – Mark all notifications as read.

---

## Testing
### Backend
```powershell
pytest backend/tests
```
Runs the automated test suite covering authentication, RBAC authorization, ownership validation, notifications, AI classification, explainable priority scoring, and reverse geocoding.

### Frontend
```powershell
cd frontend
npm run build
```
Validates component compilation, syntax, and asset bundling.

---

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/awesome-thing`).
3. Make your changes and verify with `pytest backend/tests` and `npm run build`.
4. Commit with clear messages (`git commit -m "feat: add description"`).
5. Push to your fork and open a Pull Request.

---

## License
This project is licensed under the **MIT License**.

---

## Acknowledgements
- **FastAPI** – high‑performance Python web framework.
- **React 19** – UI library, used with **Vite** for fast builds.
- **Leaflet & OpenStreetMap** – interactive mapping and reverse geocoding.
- **Tailwind CSS & CSS variables** – modular, responsive UI design.
- **oxlint** – JavaScript/TypeScript linter.
