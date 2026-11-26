import openpyxl
from fastapi.testclient import TestClient

from app.main import app, WORKBOOK


def test_health_and_items():
    client = TestClient(app)
    assert client.get("/api/health").json()["ok"] is True
    response = client.get("/api/items")
    assert response.status_code == 200
    assert len(response.json()) >= 11


def test_workbook_is_valid_and_preserved():
    wb = openpyxl.load_workbook(WORKBOOK)
    assert "November 2026" in wb.sheetnames
    assert "Dashboard" in wb.sheetnames
    assert "Setup" in wb.sheetnames
    assert "Data" in wb.sheetnames


def test_entry_round_trip():
    client = TestClient(app)
    response = client.post("/api/entries", json={
        "date": "2026-11-26",
        "trackingItemId": "TRACK-001",
        "value": "✓",
        "status": "DONE",
        "note": "test",
    })
    assert response.status_code == 200
    month = client.get("/api/month/2026/11").json()
    assert any(e["trackingItemId"] == "TRACK-001" and e["date"] == "2026-11-26" for e in month["entries"])
