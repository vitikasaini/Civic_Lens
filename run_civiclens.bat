@echo off
setlocal

:: Change to the directory where this script lives
cd /d "%~dp0"

:: Activate the Python virtual environment
call venv\Scripts\activate.bat

:: Install backend dependencies (idempotent)
echo Installing backend dependencies...
pip install -r requirements.txt

:: Build the frontend if it hasn't been built yet
if not exist "frontend\dist" (
    echo Building frontend...
    pushd frontend
    npm ci
    npm run build
    popd
) else (
    echo Frontend already built.
)

:: Start the FastAPI server
echo Starting FastAPI server on http://127.0.0.1:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause
