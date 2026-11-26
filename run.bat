@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Running setup first...
  call "%~dp0setup.bat"
)
if not exist ".venv\Scripts\python.exe" (
  echo Setup failed. Python 3.11 or newer is required.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
