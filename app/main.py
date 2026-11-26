import csv
import io
import json
import shutil
import threading
from datetime import date, datetime
from pathlib import Path

import openpyxl
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WORKBOOK = DATA / "MyStudyTracker.xlsx"
BACKUPS = DATA / "backups"
SETTINGS = DATA / "settings.json"
FRONTEND = ROOT / "frontend"
LOCK = threading.RLock()
DEFAULTS = {"theme": "system", "compact": False, "showTotals": True, "autoSave": True, "backupRetention": 30}

app = FastAPI(title="MyStudyTracker", docs_url=None, redoc_url=None)


def ensure_state():
    DATA.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    if not SETTINGS.exists():
        SETTINGS.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
    if not WORKBOOK.exists():
        wb = openpyxl.Workbook()
        wb.active.title = "November 2026"
        wb.create_sheet("Dashboard")
        wb.create_sheet("Setup")
        wb.create_sheet("Data")
        wb.save(WORKBOOK)
    wb = openpyxl.load_workbook(WORKBOOK)
    setup = wb["Setup"]
    headers = [setup.cell(1, col).value for col in range(1, 10)]
    if headers[1:4] != ["NAME", "TYPE", "TARGET"]:
        for merged_range in list(setup.merged_cells.ranges):
            setup.unmerge_cells(str(merged_range))
        for col, value in enumerate(["ID", "NAME", "TYPE", "TARGET", "UNIT", "CATEGORY", "ICON", "ACTIVE", "SORT"], 1):
            setup.cell(1, col).value = value
        wb.save(WORKBOOK)


def wb_load():
    ensure_state()
    return openpyxl.load_workbook(WORKBOOK)


def wb_save(wb):
    temp = WORKBOOK.with_suffix(".tmp.xlsx")
    wb.save(temp)
    openpyxl.load_workbook(temp)
    temp.replace(WORKBOOK)


def now():
    return datetime.now().isoformat(timespec="seconds")


class ItemModel(BaseModel):
    name: str
    type: str = "checkbox"
    target: float = 1
    unit: str = ""
    category: str = "General"
    icon: str = "📌"
    active: bool = True


class EntryModel(BaseModel):
    date: str
    trackingItemId: str
    value: object
    status: str | None = None
    note: str = ""


class MoodModel(BaseModel):
    date: str
    mood: str
    score: int
    note: str = ""


@app.get("/api/health")
def health():
    ensure_state()
    return {"ok": True, "workbook": str(WORKBOOK)}


@app.get("/api/items")
def items():
    with LOCK:
        ws = wb_load()["Setup"]
        headers = [c.value for c in ws[1]]
        return [dict(zip(headers, [c.value for c in row])) for row in ws.iter_rows(min_row=2)]


@app.post("/api/items")
def add_item(item: ItemModel):
    with LOCK:
        wb = wb_load()
        ws = wb["Setup"]
        ids = [str(ws.cell(r, 1).value) for r in range(2, ws.max_row + 1)]
        number = max([int(x[-3:]) for x in ids if x.startswith("TRACK-") and x[-3:].isdigit()] or [0]) + 1
        item_id = f"TRACK-{number:03d}"
        ws.append([item_id, item.name, item.type, item.target, item.unit, item.category, item.icon, item.active, ws.max_row - 1])
        wb_save(wb)
        return {"id": item_id}


@app.put("/api/items/{item_id}")
def update_item(item_id: str, item: ItemModel):
    with LOCK:
        wb = wb_load()
        ws = wb["Setup"]
        for row in range(2, ws.max_row + 1):
            if ws.cell(row, 1).value == item_id:
                values = [item_id, item.name, item.type, item.target, item.unit, item.category, item.icon, item.active, ws.cell(row, 9).value]
                for col, value in enumerate(values, 1):
                    ws.cell(row, col).value = value
                wb_save(wb)
                return {"ok": True}
        raise HTTPException(404, "Item not found")


@app.delete("/api/items/{item_id}")
def delete_item(item_id: str):
    with LOCK:
        wb = wb_load()
        ws = wb["Setup"]
        for row in range(2, ws.max_row + 1):
            if ws.cell(row, 1).value == item_id:
                ws.delete_rows(row)
                wb_save(wb)
                return {"ok": True}
        raise HTTPException(404, "Item not found")


@app.post("/api/items/reorder")
def reorder_items(body: dict):
    ids = body.get("ids", [])
    with LOCK:
        wb = wb_load()
        ws = wb["Setup"]
        rows = {}
        for row in range(2, ws.max_row + 1):
            rows[str(ws.cell(row, 1).value)] = [ws.cell(row, col).value for col in range(1, 10)]
        for sort, item_id in enumerate(ids):
            if item_id in rows:
                rows[item_id][8] = sort
        ws.delete_rows(2, ws.max_row)
        for row in sorted(rows.values(), key=lambda x: x[8]):
            ws.append(row)
        wb_save(wb)
        return {"ok": True}


@app.post("/api/items/{item_id}/archive")
def archive_item(item_id: str):
    with LOCK:
        wb = wb_load()
        ws = wb["Setup"]
        for row in range(2, ws.max_row + 1):
            if ws.cell(row, 1).value == item_id:
                ws.cell(row, 8).value = False
                wb_save(wb)
                return {"ok": True}
        raise HTTPException(404, "Item not found")


@app.get("/api/month/{year}/{month}")
def month(year: int, month: int):
    with LOCK:
        wb = wb_load()
        setup = wb["Setup"]
        result_items = []
        for row in range(2, setup.max_row + 1):
            if setup.cell(row, 8).value is not False:
                result_items.append({"id": setup.cell(row, 1).value, "name": setup.cell(row, 2).value,
                                     "type": setup.cell(row, 3).value, "target": setup.cell(row, 4).value,
                                     "unit": setup.cell(row, 5).value, "icon": setup.cell(row, 7).value})
        data = wb["Data"]
        prefix = f"{year:04d}-{month:02d}-"
        entries = []
        for row in range(2, data.max_row + 1):
            date_value = str(data.cell(row, 2).value or "")
            if date_value.startswith(prefix):
                entries.append({"id": data.cell(row, 1).value, "date": date_value,
                                "trackingItemId": data.cell(row, 3).value, "value": data.cell(row, 4).value,
                                "status": data.cell(row, 5).value, "note": data.cell(row, 6).value})
        return {"year": year, "month": month, "items": result_items, "entries": entries}


@app.post("/api/entries")
def save_entry(entry: EntryModel):
    with LOCK:
        wb = wb_load()
        ws = wb["Data"]
        for row in range(2, ws.max_row + 1):
            if str(ws.cell(row, 2).value) == entry.date and str(ws.cell(row, 3).value) == entry.trackingItemId:
                ws.cell(row, 4).value = entry.value
                ws.cell(row, 5).value = entry.status or "DONE"
                ws.cell(row, 6).value = entry.note
                ws.cell(row, 8).value = now()
                wb_save(wb)
                return {"ok": True}
        entry_id = f"ENT-{ws.max_row:05d}"
        ws.append([entry_id, entry.date, entry.trackingItemId, entry.value, entry.status or "DONE", entry.note, now(), now()])
        wb_save(wb)
        return {"id": entry_id}


@app.delete("/api/entries/{entry_id}")
def delete_entry(entry_id: str):
    with LOCK:
        wb = wb_load()
        ws = wb["Data"]
        for row in range(2, ws.max_row + 1):
            if str(ws.cell(row, 1).value) == entry_id:
                ws.delete_rows(row)
                wb_save(wb)
                return {"ok": True}
        raise HTTPException(404, "Entry not found")


@app.get("/api/mood/{year}/{month}")
def mood_month(year: int, month: int):
    prefix = f"{year:04d}-{month:02d}-"
    ws = wb_load()["Data"]
    return [{"id": ws.cell(r, 1).value, "date": ws.cell(r, 2).value, "mood": ws.cell(r, 4).value,
             "score": ws.cell(r, 5).value, "note": ws.cell(r, 6).value}
            for r in range(2, ws.max_row + 1)
            if str(ws.cell(r, 3).value).startswith("MOOD-") and str(ws.cell(r, 2).value).startswith(prefix)]


@app.post("/api/mood")
def add_mood(mood: MoodModel):
    return save_entry(EntryModel(date=mood.date, trackingItemId="MOOD-Daily", value=mood.mood, status=str(mood.score), note=mood.note))


@app.get("/api/dashboard")
def dashboard():
    today = date.today()
    data = month(today.year, today.month)
    entries = data["entries"]
    done = sum(1 for e in entries if str(e["status"]) == "DONE")
    moods = [int(e["status"]) for e in entries if e["trackingItemId"] == "MOOD-Daily" and str(e["status"]).isdigit()]
    study = sum(float(e["value"]) for e in entries if e["trackingItemId"] == "TRACK-005" and isinstance(e["value"], (int, float)))
    return {"monthlyCompletion": round(done / max(1, len(data["items"]) * today.day) * 100),
            "currentStreak": 0, "bestStreak": 0, "studyTime": round(study, 1),
            "averageMood": round(sum(moods) / len(moods), 1) if moods else 0,
            "completedTasks": done, "days": []}


@app.get("/api/settings")
def get_settings():
    ensure_state()
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


@app.put("/api/settings")
def put_settings(body: dict):
    settings = {**DEFAULTS, **body}
    SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings


@app.post("/api/backup")
def create_backup():
    ensure_state()
    name = f"MyStudyTracker_{datetime.now():%Y-%m-%d_%H%M%S}.xlsx"
    shutil.copy2(WORKBOOK, BACKUPS / name)
    return {"name": name}


@app.get("/api/backups")
def backups():
    return [{"name": p.name, "size": p.stat().st_size} for p in sorted(BACKUPS.glob("*.xlsx"), reverse=True)]


@app.post("/api/restore")
def restore_backup(body: dict):
    name = body.get("name")
    source = BACKUPS / name if name else None
    if not source or not source.exists():
        raise HTTPException(404, "Backup not found")
    create_backup()
    shutil.copy2(source, WORKBOOK)
    openpyxl.load_workbook(WORKBOOK)
    return {"ok": True}


@app.post("/api/import")
async def import_workbook(file: UploadFile = File(...)):
    temp = DATA / "import.tmp.xlsx"
    temp.write_bytes(await file.read())
    try:
        openpyxl.load_workbook(temp)
        create_backup()
        temp.replace(WORKBOOK)
    except Exception:
        temp.unlink(missing_ok=True)
        raise HTTPException(400, "Invalid XLSX workbook")
    return {"ok": True}


@app.get("/api/export/xlsx")
def export_xlsx():
    return FileResponse(WORKBOOK, filename="MyStudyTracker.xlsx")


@app.get("/api/export/csv")
def export_csv():
    ws = wb_load()["Data"]
    output = io.StringIO()
    csv.writer(output).writerows([[c.value for c in row] for row in ws.iter_rows()])
    return StreamingResponse(io.BytesIO(output.getvalue().encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=MyStudyTracker.csv"})


@app.get("/api/export/json")
def export_json():
    ws = wb_load()["Data"]
    rows = [[c.value for c in row] for row in ws.iter_rows()]
    records = [dict(zip(rows[0], row)) for row in rows[1:] if any(row)]
    return StreamingResponse(io.BytesIO(json.dumps(records, ensure_ascii=False, indent=2).encode()),
                             media_type="application/json",
                             headers={"Content-Disposition": "attachment; filename=MyStudyTracker.json"})


ensure_state()
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
