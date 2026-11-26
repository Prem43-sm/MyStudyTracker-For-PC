$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv")) { python -m venv .venv }
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Setup failed. Python 3.11 or newer is required." }
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
Start-Process "http://127.0.0.1:8000"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
