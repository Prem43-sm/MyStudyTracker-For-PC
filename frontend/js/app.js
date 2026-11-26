const $ = (selector) => document.querySelector(selector);
const content = $("#content");
let monthData = null;
let current = new Date();

function pad(value) {
  return String(value).padStart(2, "0");
}

async function api(path, options) {
  const response = await fetch(path, options || {});
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? null : response.json();
}

function setView(name) {
  document.querySelectorAll(".nav").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === name);
  });
  $("#pageTitle").textContent = name.charAt(0).toUpperCase() + name.slice(1);
  if (name === "today") renderToday();
  if (name === "worksheet") renderWorksheet();
  if (name === "dashboard") renderDashboard();
  if (name === "calendar") renderCalendar();
  if (name === "setup") renderSetup();
  if (name === "settings") renderSettings();
}

async function loadMonth() {
  monthData = await api("/api/month/" + current.getFullYear() + "/" + (current.getMonth() + 1));
}

function findEntry(itemId, date) {
  return monthData.entries.find((entry) => entry.trackingItemId === itemId && entry.date === date);
}

async function renderToday() {
  await loadMonth();
  const date = current.getFullYear() + "-" + pad(current.getMonth() + 1) + "-" + pad(current.getDate());
  $("#todayDate").textContent = current.toLocaleDateString(undefined, {
    weekday: "long", month: "long", day: "numeric", year: "numeric"
  });
  let completed = 0;
  const rows = monthData.items.map((item) => {
    const entry = findEntry(item.id, date);
    if (entry && entry.status === "DONE") completed++;
    const value = entry ? entry.value : "";
    const display = value || (entry && entry.status === "DONE" ? "✓" : "Mark");
    return '<div class="item-row">' +
      '<div>' + (item.icon || "📌") + ' <b>' + item.name + '</b></div>' +
      '<button class="toggle ' + (entry && entry.status === "DONE" ? "done" : "") +
      '" data-id="' + item.id + '" data-type="' + item.type + '">' + display + "</button>" +
      '<span class="target">' + item.target + " " + (item.unit || "") + "</span></div>";
  }).join("");
  const percent = monthData.items.length ? Math.round(completed / monthData.items.length * 100) : 0;
  content.innerHTML = '<div class="cards"><div class="card"><small>Today\'s completion</small><b>' +
    percent + '%</b></div><div class="card"><small>Completed</small><b>' + completed +
    "/" + monthData.items.length + '</b></div></div><div class="panel" style="margin-top:14px">' +
    rows + "</div>";
  document.querySelectorAll(".toggle").forEach((button) => {
    button.onclick = () => quickToggle(button);
  });
}

async function quickToggle(button) {
  const date = current.getFullYear() + "-" + pad(current.getMonth() + 1) + "-" + pad(current.getDate());
  const entry = findEntry(button.dataset.id, date);
  const done = entry && entry.status === "DONE";
  if (button.dataset.type !== "checkbox") {
    openNumberModal(button.dataset.id, date);
    return;
  }
  await api("/api/entries", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      date: date,
      trackingItemId: button.dataset.id,
      value: done ? "✕" : "✓",
      status: done ? "NOT_DONE" : "DONE"
    })
  });
  renderToday();
}

async function renderWorksheet() {
  await loadMonth();
  const year = current.getFullYear();
  const month = current.getMonth() + 1;
  const days = new Date(year, month, 0).getDate();
  let head = "<th>Tracking Item</th>";
  for (let day = 1; day <= days; day++) head += "<th>" + day + "</th>";
  const rows = monthData.items.map((item) => {
    let cells = "";
    for (let day = 1; day <= days; day++) {
      const date = year + "-" + pad(month) + "-" + pad(day);
      const entry = findEntry(item.id, date);
      const value = entry ? entry.value : "";
      cells += '<td><button class="cell-btn" data-id="' + item.id +
        '" data-date="' + date + '" data-type="' + item.type + '">' +
        (value || "·") + "</button></td>";
    }
    return "<tr><td>" + (item.icon || "📌") + " " + item.name + "</td>" + cells + "</tr>";
  }).join("");
  content.innerHTML = '<div style="display:flex;justify-content:space-between;margin-bottom:12px">' +
    "<h2>" + current.toLocaleDateString(undefined, {month: "long", year: "numeric"}) +
    '</h2><div><button class="primary" id="prevMonth">‹</button> <button class="primary" id="nextMonth">›</button></div></div>' +
    '<div class="worksheet-wrap"><table class="worksheet"><thead><tr>' + head +
    "</tr></thead><tbody>" + rows + "</tbody></table></div>";
  $("#prevMonth").onclick = () => { current.setMonth(current.getMonth() - 1); renderWorksheet(); };
  $("#nextMonth").onclick = () => { current.setMonth(current.getMonth() + 1); renderWorksheet(); };
  document.querySelectorAll(".cell-btn").forEach((button) => {
    button.onclick = () => {
      if (button.dataset.type === "checkbox") toggleDate(button);
      else openNumberModal(button.dataset.id, button.dataset.date);
    };
  });
}

async function toggleDate(button) {
  const entry = findEntry(button.dataset.id, button.dataset.date);
  const done = entry && entry.status === "DONE";
  await api("/api/entries", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      date: button.dataset.date,
      trackingItemId: button.dataset.id,
      value: done ? "✕" : "✓",
      status: done ? "NOT_DONE" : "DONE"
    })
  });
  renderWorksheet();
}

async function renderDashboard() {
  const dashboard = await api("/api/dashboard");
  await loadMonth();
  const totals = monthData.items.map((item) => {
    return monthData.entries.filter((entry) => entry.trackingItemId === item.id && entry.status === "DONE").length;
  });
  content.innerHTML = '<div class="cards"><div class="card"><small>Monthly Completion</small><b>' +
    dashboard.monthlyCompletion + '%</b></div><div class="card"><small>Study Time</small><b>' +
    dashboard.studyTime + 'h</b></div><div class="card"><small>Average Mood</small><b>' +
    (dashboard.averageMood || "—") + '</b></div><div class="card"><small>Completed Tasks</small><b>' +
    dashboard.completedTasks + '</b></div></div><div class="panel" style="margin-top:14px">' +
    '<h3>Habit Completion</h3><div class="chart">' +
    totals.map((total) => '<div class="bar" style="height:' + Math.min(100, total * 5) + '%"></div>').join("") +
    "</div></div>";
}

async function renderSetup() {
  const items = await api("/api/items");
  content.innerHTML = '<div class="setup-list">' + items.map((item) =>
    '<div class="setup-row"><span>' + (item.ICON || "📌") + "</span><b>" + item.NAME +
    "</b><span>" + item.TYPE + "</span><span>" + item.TARGET + " " + (item.UNIT || "") +
    '<button class="toggle" data-id="' + item.ID + '">Edit</button></div>'
  ).join("") + "</div>";
  document.querySelectorAll(".setup-row button").forEach((button) => {
    button.onclick = () => editItem(items.find((item) => item.ID === button.dataset.id));
  });
}

async function renderSettings() {
  const settings = await api("/api/settings");
  content.innerHTML = '<div class="panel form-grid"><h2>Settings</h2>' +
    '<label>Theme<select id="themeSetting"><option>light</option><option>dark</option><option>system</option></select></label>' +
    '<button class="primary" id="saveSettings">Save Settings</button><hr><h3>Data</h3>' +
    '<button class="primary" id="backup">Create Backup</button> ' +
    '<a class="primary" href="/api/export/xlsx">Export XLSX</a> ' +
    '<a class="primary" href="/api/export/csv">Export CSV</a> ' +
    '<a class="primary" href="/api/export/json">Export JSON</a></div>';
  $("#themeSetting").value = settings.theme;
  $("#saveSettings").onclick = async () => {
    const theme = $("#themeSetting").value;
    await api("/api/settings", {
      method: "PUT", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({theme: theme})
    });
    applyTheme(theme);
  };
  $("#backup").onclick = async () => {
    const backup = await api("/api/backup", {method: "POST"});
    alert("Backup created: " + backup.name);
  };
}

function renderCalendar() {
  content.innerHTML = '<div class="panel"><h2>' +
    current.toLocaleDateString(undefined, {month: "long", year: "numeric"}) +
    '</h2><p>Open the worksheet to enter daily values.</p><button class="primary" id="calendarToMonth">Open Worksheet</button></div>';
  $("#calendarToMonth").onclick = () => setView("worksheet");
}

function openModal() {
  $("#modal").classList.add("open");
}

function closeModal() {
  $("#modal").classList.remove("open");
}

function openNumberModal(itemId, date) {
  $("#modalBody").innerHTML = '<h2>Quick entry</h2><div class="form-grid">' +
    '<input id="quickValue" type="number" step="0.25" value="1">' +
    '<button class="primary" id="saveQuick">Save</button></div>';
  openModal();
  $("#saveQuick").onclick = async () => {
    await api("/api/entries", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        date: date, trackingItemId: itemId,
        value: Number($("#quickValue").value), status: "DONE"
      })
    });
    closeModal();
    renderToday();
  };
}

function editItem(item) {
  $("#modalBody").innerHTML = '<h2>Edit tracking item</h2><div class="form-grid">' +
    '<input id="itemName" value="' + item.NAME + '">' +
    '<select id="itemType"><option>checkbox</option><option>duration</option><option>number</option><option>rating</option></select>' +
    '<input id="itemTarget" type="number" value="' + item.TARGET + '">' +
    '<input id="itemUnit" value="' + (item.UNIT || "") + '">' +
    '<button class="primary" id="saveItem">Save</button></div>';
  $("#itemType").value = item.TYPE;
  openModal();
  $("#saveItem").onclick = async () => {
    await api("/api/items/" + item.ID, {
      method: "PUT", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        name: $("#itemName").value, type: $("#itemType").value,
        target: Number($("#itemTarget").value), unit: $("#itemUnit").value,
        category: item.CATEGORY || "General", icon: item.ICON || "📌", active: true
      })
    });
    closeModal();
    renderSetup();
  };
}

function quickAdd() {
  $("#modalBody").innerHTML = '<h2>Add tracking item</h2><div class="form-grid">' +
    '<input id="newName" placeholder="Tracking item name">' +
    '<select id="newType"><option>checkbox</option><option>duration</option><option>number</option><option>rating</option></select>' +
    '<input id="newTarget" type="number" value="1">' +
    '<input id="newUnit" placeholder="Unit">' +
    '<button class="primary" id="addItem">Add Item</button></div>';
  openModal();
  $("#addItem").onclick = async () => {
    await api("/api/items", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        name: $("#newName").value, type: $("#newType").value,
        target: Number($("#newTarget").value), unit: $("#newUnit").value
      })
    });
    closeModal();
    renderSetup();
  };
}

function applyTheme(theme) {
  document.body.classList.toggle("dark",
    theme === "dark" || (theme === "system" && matchMedia("(prefers-color-scheme: dark)").matches));
}

$("#closeModal").onclick = closeModal;
$("#fab").onclick = quickAdd;
$("#themeBtn").onclick = () => document.body.classList.toggle("dark");
document.querySelectorAll(".nav").forEach((button) => {
  button.onclick = () => setView(button.dataset.view);
});

api("/api/settings").then((settings) => applyTheme(settings.theme));
setView("today");
