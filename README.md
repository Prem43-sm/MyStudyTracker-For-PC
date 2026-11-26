# MyStudyTracker

A fully local browser tracker backed by `data/MyStudyTracker.xlsx`.

## Start

### Windows

```bat
run.bat
```

Or PowerShell:

```powershell
.\run.ps1
```

Open <http://127.0.0.1:8000>.

## Setup

Python 3.11+ is required. The startup scripts create `.venv` and install the minimal dependencies.

Run `setup.bat` once:

```bat
setup.bat
```

PowerShell setup:

```powershell
.\setup.ps1
```

## Test

```powershell
.venv\Scripts\python -m pytest -q
```

## Data

- Workbook: `data/MyStudyTracker.xlsx`
- Backups: `data/backups/`
- Settings: `data/settings.json`
- The original supplied workbook remains at `MyStudyTracker_Sample.xlsx`.

Use the Settings screen to export XLSX/CSV/JSON or create a backup.
