const WEB_REFRESH = 30;
const DB_REFRESH = 30;
const STATUS_TIMEOUT = 120;

let webTick = WEB_REFRESH;
let dbTick = DB_REFRESH;
let lastStatusOk = 0;

/* ===== ELEMENTS ===== */
const loaderEl = document.getElementById("loader");
const statusEl = document.getElementById("statusText");
const vendorInput = document.getElementById("vendor");
const vendorDropdown = document.getElementById("vendorDropdown");
const routerSelect = document.getElementById("routerSelect");

/* ===== STATE ===== */
let currentRouter = "";
let lastInput = [];
let lastVendor = "";
let lastSearch = "";
let hasProcessed = false;
let checkedState = {};
let lastRenderedRows = [];
let vendorCache = new Set();

/* ===== LOADER ===== */
function loader(show) {
  loaderEl.classList.toggle("hidden", !show);
}

/* ===== LOAD ROUTERS LIST ===== */
function loadRouters() {
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
    })
    .catch(err => {
      console.error("Failed to load routers:", err);
    });
}

/* ===== CHANGE ROUTER ===== */
function changeRouter() {
  const routerId = routerSelect.value;
  
  if (!routerId) {
    currentRouter = "";
    table.innerHTML = '<tr><td colspan="6">Select a router to start...</td></tr>';
    router.innerText = "-";
    statusEl.innerText = "-";
    statusEl.className = "";
    return;
  }

  // Start collector for selected router
  loader(true);
  fetch(`/connect/${routerId}`, { method: "POST" })
    .then(r => r.json())
    .then(result => {
      if (result.success) {
        currentRouter = routerId;
        console.log(result.message);
        
        // Reset state
        hasProcessed = false;
        checkedState = {};
        vendorCache.clear();
        
        // Load initial data
        setTimeout(() => {
          loadStatus();
          if (hasProcessed) {
            refreshResult();
          }
        }, 1000);
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

/* ===== STATUS ===== */
function loadStatus() {
  if (!currentRouter) return;

  fetch(`/status/${currentRouter}`)
    .then(r => r.json())
    .then(d => {
      router.innerText = d.router_ip || "-";
      const now = Date.now() / 1000;

      if (d.connected) {
        lastStatusOk = now;
        statusEl.innerText = "CONNECTED";
        statusEl.className = "ok";
        dbTick = DB_REFRESH;
      } else {
        statusEl.innerText = "DISCONNECTED";
        statusEl.className = "down";
      }
    })
    .catch(() => {});
}

/* ===== SECRETS ===== */
function loadSecrets() {
  if (!currentRouter) {
    alert("Please select a router first");
    return;
  }

  loader(true);
  fetch(`/secrets/${currentRouter}`)
    .then(r => r.json())
    .then(list => {
      names.value = list.join("\n");
      loader(false);
    })
    .catch(() => {
      loader(false);
    });
}

/* ===== PROCESS ===== */
function processInput() {
  if (!currentRouter) {
    alert("Please select a router first");
    return;
  }

  lastVendor = vendorInput.value.toLowerCase();
  lastSearch = search.value.toLowerCase();
  lastInput = names.value.split("\n").map(x => x.trim()).filter(Boolean);

  hasProcessed = true;
  webTick = WEB_REFRESH;
  refreshResult();
}

/* ===== UPDATE VENDOR CACHE ===== */
function updateVendorCache(rows) {
  rows.forEach(r => {
    if (r.vendor) vendorCache.add(r.vendor);
  });
}

/* ===== REFRESH RESULT ===== */
function refreshResult() {
  if (!hasProcessed || !currentRouter) return;

  loader(true);

  fetch(`/data/${currentRouter}`)
    .then(r => r.json())
    .then(rows => {
      updateVendorCache(rows);

      let map = {};
      rows.forEach(r => map[r.name] = r);

      let html = "";
      let online = 0;
      lastRenderedRows = [];

      lastInput.forEach(name => {
        if (lastSearch && !name.toLowerCase().includes(lastSearch)) return;

        let r = map[name];
        if (r) {
          if (lastVendor && !r.vendor.toLowerCase().includes(lastVendor)) return;

          online++;
          let checked = !!checkedState[name];

          lastRenderedRows.push({ ...r, name, checked });

          html += `
          <tr class="${checked ? "checked" : ""}">
            <td>${name}</td>
            <td><a href="http://${r.ip}" target="_blank">${r.ip}</a></td>
            <td>${r.mac}</td>
            <td>${r.vendor}</td>
            <td>${r.uptime}</td>
            <td><input type="checkbox" data-name="${name}" ${checked ? "checked" : ""}></td>
          </tr>`;
        } else if (!lastVendor) {
          html += `<tr class="offline"><td>${name}</td><td colspan="5">Not Connected</td></tr>`;
        }
      });

      table.innerHTML = html || "<tr><td colspan='6'>No data</td></tr>";
      onlineCount.innerText = online;
      loader(false);
    })
    .catch(() => {
      loader(false);
    });
}

/* ===== CHECKBOX ===== */
table.addEventListener("change", e => {
  if (e.target.type === "checkbox") {
    const name = e.target.dataset.name;
    checkedState[name] = e.target.checked;
    e.target.closest("tr").classList.toggle("checked", e.target.checked);
  }
});

/* ===== CUSTOM AUTOSUGGEST LOGIC ===== */
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
    .slice(0, 10)
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
  if (!e.target.closest(".vendor-wrap")) {
    vendorDropdown.classList.add("hidden");
  }
});

/* ===== EXPORT CSV ===== */
function exportCSV(checkedOnly) {
  if (!lastRenderedRows.length) return;

  let csv = ["Name,IP,MAC,Vendor,Uptime,Checked"];
  lastRenderedRows.forEach(r => {
    if (checkedOnly && !r.checked) return;
    csv.push([r.name, r.ip, r.mac, r.vendor, r.uptime, r.checked].join(","));
  });

  const blob = new Blob([csv.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ppp-monitor.csv";
  a.click();
  URL.revokeObjectURL(url);
}

/* ===== COUNTDOWN ===== */
function tickCountdown() {
  if (!currentRouter) return;

  webTick--;
  dbTick--;

  const now = Date.now() / 1000;
  if (lastStatusOk && now - lastStatusOk > STATUS_TIMEOUT) {
    statusEl.innerText = "DISCONNECTED";
    statusEl.className = "down";
  }

  if (webTick <= 0) {
    webTick = WEB_REFRESH;
    refreshResult();
  }

  if (dbTick <= 0) dbTick = DB_REFRESH;

  webCountdown.innerText = webTick;
  dbCountdown.innerText = dbTick;
}

function preloadVendorCache() {
  if (!currentRouter) return;
  
  fetch(`/data/${currentRouter}`)
    .then(r => r.json())
    .then(rows => {
      rows.forEach(r => {
        if (r.vendor) vendorCache.add(r.vendor);
      });
    })
    .catch(() => {});
}

/* ===== INIT ===== */
loadRouters();
setInterval(tickCountdown, 1000);
setInterval(() => {
  if (currentRouter) loadStatus();
}, 5000);