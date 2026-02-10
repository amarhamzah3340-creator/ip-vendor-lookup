const WEB_REFRESH = 30;
const DB_REFRESH = 30;
const STATUS_TIMEOUT = 120;

let webTick = WEB_REFRESH;
let dbTick = DB_REFRESH;
let lastStatusOk = 0;

const loaderEl = document.getElementById("loader");
const statusEl = document.getElementById("statusText");
const statusNavTextEl = document.getElementById("statusNavText");
const vendorInput = document.getElementById("vendor");
const vendorDropdown = document.getElementById("vendorDropdown");
const routerSelect = document.getElementById("routerSelect");
const tableEl = document.getElementById("table");
const routerEl = document.getElementById("router");
const namesEl = document.getElementById("names");
const searchEl = document.getElementById("search");
const onlineCountEl = document.getElementById("onlineCount");
const onlineTotalEl = document.getElementById("onlineTotal");
const webCountdownEl = document.getElementById("webCountdown");
const dbCountdownEl = document.getElementById("dbCountdown");
const logPanelEl = document.getElementById("logPanel");

let currentRouter = "";
let lastInput = [];
let lastVendor = "";
let lastSearch = "";
let hasProcessed = false;
let checkedState = {};
let lastRenderedRows = [];
let vendorCache = new Set();

function loader(show) {
  loaderEl.classList.toggle("hidden", !show);
}

function setDisconnected(text = "DISCONNECTED") {
  statusEl.innerText = text;
  statusEl.className = "down";
  statusNavTextEl.innerText = "Disconnected";
  document.querySelector(".router-pill")?.classList.remove("connected");
}

function setConnected() {
  statusEl.innerText = "CONNECTED";
  statusEl.className = "ok";
  statusNavTextEl.innerText = "Connected";
  document.querySelector(".router-pill")?.classList.add("connected");
}

function loadRouters() {
  const selected = routerSelect.value;

  fetch("/routers")
    .then(r => r.json())
    .then(routers => {
      routerSelect.innerHTML = '<option value="">Select Router...</option>';
      routers.forEach(router => {
        const option = document.createElement("option");
        option.value = router.id;
        option.textContent = `${router.name} (${router.ip})`;
        routerSelect.appendChild(option);
      });

      if (selected && routers.some(r => r.id === selected)) {
        routerSelect.value = selected;
      }
    })
    .catch(err => console.error("Failed to load routers:", err));
}

function loadVendorList() {
  fetch("/vendors")
    .then(r => r.json())
    .then(vendors => vendors.forEach(v => vendorCache.add(v)))
    .catch(err => console.error("Failed to load vendors:", err));
}

function loadLogs() {
  fetch("/logs")
    .then(r => r.json())
    .then(rows => {
      let html = "";
      rows.slice(-200).forEach(row => {
        const level = (row.level || "INFO").toLowerCase();
        html += `<div class="log-entry ${level}"><span class="t">[${row.time}]</span><span class="lvl">${row.level}</span>${row.message}</div>`;
      });
      logPanelEl.innerHTML = html || '<div class="log-entry info">No logs yet.</div>';
      logPanelEl.scrollTop = logPanelEl.scrollHeight;
    })
    .catch(() => {});
}

function changeRouter() {
  const routerId = routerSelect.value;

  if (!routerId) {
    currentRouter = "";
    tableEl.innerHTML = '<tr><td colspan="7">Select a router to start...</td></tr>';
    routerEl.innerText = "-";
    statusEl.innerText = "-";
    statusEl.className = "";
    onlineCountEl.innerText = "0";
    onlineTotalEl.innerText = "0";
    return;
  }

  loader(true);
  fetch(`/connect/${routerId}`, { method: "POST" })
    .then(r => r.json())
    .then(result => {
      if (result.success) {
        currentRouter = routerId;
        hasProcessed = false;
        checkedState = {};
        loadStatus();
      } else {
        alert(`Failed to connect: ${result.message}`);
      }
      loader(false);
    })
    .catch(err => {
      console.error("Connection error:", err);
      alert("Failed to connect to router");
      loader(false);
    });
}

function loadStatus() {
  if (!currentRouter) return;

  fetch(`/status/${currentRouter}`)
    .then(r => r.json())
    .then(d => {
      routerEl.innerText = d.router_ip || "-";
      const now = Date.now() / 1000;

      if (d.connected) {
        lastStatusOk = now;
        setConnected();
        dbTick = DB_REFRESH;
      } else {
        setDisconnected("DISCONNECTED");
        if (d.last_error) statusEl.title = d.last_error;
      }
    })
    .catch(() => setDisconnected("DISCONNECTED"));
}

function loadSecrets() {
  if (!currentRouter) {
    alert("Please select a router first");
    return;
  }

  loader(true);
  fetch(`/secrets/${currentRouter}`)
    .then(r => r.json())
    .then(list => {
      namesEl.value = list.join("\n");
      loader(false);
      processInput();
    })
    .catch(() => loader(false));
}

function processInput() {
  if (!currentRouter) {
    alert("Please select a router first");
    return;
  }

  lastVendor = vendorInput.value.toLowerCase();
  lastSearch = searchEl.value.toLowerCase();
  lastInput = namesEl.value.split("\n").map(x => x.trim()).filter(Boolean);

  hasProcessed = true;
  webTick = WEB_REFRESH;
  refreshResult();
}

function updateVendorCache(rows) {
  rows.forEach(r => {
    if (r.vendor) vendorCache.add(r.vendor);
  });
}

function refreshResult() {
  if (!hasProcessed || !currentRouter) return;

  loader(true);
  fetch(`/data/${currentRouter}`)
    .then(r => r.json())
    .then(rows => {
      updateVendorCache(rows);
      const map = {};
      rows.forEach(r => {
        map[r.name] = r;
      });

      let html = "";
      let shownOnline = 0;
      let totalOnline = rows.length;
      lastRenderedRows = [];

      lastInput.forEach(name => {
        const r = map[name];
        if (!r) {
          if (!lastSearch || name.toLowerCase().includes(lastSearch)) {
            html += `<tr class="offline"><td>${name}</td><td colspan="5" class="offline-status">❌ Not connected</td></tr>`;
          }
          return;
        }

        if (lastVendor && !r.vendor.toLowerCase().includes(lastVendor)) return;
        if (lastSearch && !name.toLowerCase().includes(lastSearch)) return;

        shownOnline++;
        const checked = !!checkedState[name];
        lastRenderedRows.push({ ...r, name, checked });

        html += `
          <tr class="${checked ? "checked" : ""}">
            <td>${name}</td>
            <td><a href="http://${r.ip}" target="_blank">${r.ip}</a></td>
            <td>${r.mac}</td>
            <td>${r.vendor}</td>
            <td>${r.uptime}</td>
            <td><span class="status-pill online">Connected</span></td>
            <td><input type="checkbox" data-name="${name}" ${checked ? "checked" : ""}></td>
          </tr>`;
      });

      tableEl.innerHTML = html || "<tr><td colspan='6'>No data</td></tr>";
      onlineCountEl.innerText = shownOnline;
      onlineTotalEl.innerText = totalOnline;
      loader(false);
    })
    .catch(() => loader(false));
}

tableEl.addEventListener("change", e => {
  if (e.target.type === "checkbox") {
    const name = e.target.dataset.name;
    checkedState[name] = e.target.checked;
    e.target.closest("tr").classList.toggle("checked", e.target.checked);
  }
});

let activeIndex = -1;
vendorInput.addEventListener("input", () => {
  const val = vendorInput.value.toLowerCase();
  vendorDropdown.innerHTML = "";
  activeIndex = -1;

  if (!val) {
    vendorDropdown.classList.add("hidden");
    return;
  }

  [...vendorCache]
    .filter(v => v.toLowerCase().includes(val))
    .slice(0, 12)
    .forEach(v => {
      const div = document.createElement("div");
      div.innerText = v;
      div.onclick = () => {
        vendorInput.value = v;
        vendorDropdown.classList.add("hidden");
        processInput();
      };
      vendorDropdown.appendChild(div);
    });

  vendorDropdown.classList.toggle("hidden", !vendorDropdown.children.length);
});

vendorInput.addEventListener("keydown", e => {
  const items = vendorDropdown.children;
  if (!items.length) return;

  if (e.key === "ArrowDown") {
    activeIndex = (activeIndex + 1) % items.length;
  } else if (e.key === "ArrowUp") {
    activeIndex = (activeIndex - 1 + items.length) % items.length;
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (activeIndex >= 0) items[activeIndex].click();
    return;
  } else {
    return;
  }

  [...items].forEach(i => i.classList.remove("active"));
  items[activeIndex].classList.add("active");
});

document.addEventListener("click", e => {
  if (!e.target.closest(".vendor-wrap")) vendorDropdown.classList.add("hidden");
});

function exportCSV(checkedOnly) {
  if (!lastRenderedRows.length) return;

  const csv = ["Name,IP,MAC,Vendor,Uptime,Connected,Checked"];
  lastRenderedRows.forEach(r => {
    if (checkedOnly && !r.checked) return;
    csv.push([r.name, r.ip, r.mac, r.vendor, r.uptime, r.connected, r.checked].join(","));
  });

  const blob = new Blob([csv.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ppp-monitor.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function tickCountdown() {
  if (!currentRouter) return;

  webTick--;
  dbTick--;

  const now = Date.now() / 1000;
  if (lastStatusOk && now - lastStatusOk > STATUS_TIMEOUT) setDisconnected("DISCONNECTED");

  if (webTick <= 0) {
    webTick = WEB_REFRESH;
    refreshResult();
  }

  if (dbTick <= 0) dbTick = DB_REFRESH;

  webCountdownEl.innerText = webTick;
  dbCountdownEl.innerText = dbTick;
}

loadRouters();
loadVendorList();
loadLogs();
setInterval(tickCountdown, 1000);
setInterval(() => { if (currentRouter) loadStatus(); }, 5000);
setInterval(loadRouters, 15000);
setInterval(loadVendorList, 30000);
setInterval(loadLogs, 3000);
