$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

try {
    python --version | Out-Null
}
catch {
    Write-Host "Python was not found. Install Python 3.11 or newer and enable 'Add Python to PATH'."
    exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete. Run run.ps1 to start MyStudyTracker."
