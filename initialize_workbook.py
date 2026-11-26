import datetime
import openpyxl

path = "data/MyStudyTracker.xlsx"
workbook = openpyxl.load_workbook(path)
monthly = workbook["November 2026"]

items = []
for row in range(5, 16):
    name = monthly.cell(row, 1).value
    if not name:
        continue
    items.append({
        "id": f"TRACK-{row - 4:03d}",
        "name": name,
        "type": "duration" if name == "Study 6 hrs+" else "checkbox",
        "target": 6 if name == "Study 6 hrs+" else 1,
        "unit": "hours" if name == "Study 6 hrs+" else "",
    })

setup = workbook["Setup"]
for merged_range in list(setup.merged_cells.ranges):
    setup.unmerge_cells(str(merged_range))
setup.delete_rows(1, setup.max_row)
setup.append(["ID", "NAME", "TYPE", "TARGET", "UNIT", "CATEGORY", "ICON", "ACTIVE", "SORT"])
for index, item in enumerate(items):
    setup.append([
        item["id"], item["name"], item["type"], item["target"], item["unit"],
        "Study", "📌", True, index,
    ])

if "Data" in workbook.sheetnames:
    del workbook["Data"]
data = workbook.create_sheet("Data")
data.append(["ID", "DATE", "TRACKING_ITEM_ID", "VALUE", "STATUS", "NOTE", "CREATED_AT", "UPDATED_AT"])

now = datetime.datetime.now().isoformat(timespec="seconds")
for item in items:
    row = next((r for r in range(5, 16) if monthly.cell(r, 1).value == item["name"]), None)
    if not row:
        continue
    for day in range(1, 31):
        value = monthly.cell(row, day + 1).value
        if value is not None:
            status = "DONE" if value == "✓" or item["type"] == "duration" else ("NOT_DONE" if value == "✕" else "DONE")
            data.append([
                f"ENT-{item['id'][-3:]}-{day:02d}",
                f"2026-11-{day:02d}",
                item["id"], value, status, "", now, now,
            ])

workbook.save(path)
print(f"Initialized {len(items)} items")
