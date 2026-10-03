let scanId = null;
let results = [];
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => { const node = document.createElement("div"); node.textContent = value == null || value === "" ? "Unavailable" : String(value); return node.innerHTML; };
const getJson = async (url) => { const response = await fetch(url); if (!response.ok) throw new Error(`Request failed (${response.status})`); return response.json(); };

async function loadInfo() {
  try { const data = await getJson("/api/system-info"); $("#system").innerHTML = `<b>${escapeHtml(data.computer_name)}</b><br>${escapeHtml(data.operating_system)}<br>Last scan: ${data.last_scan ? new Date(data.last_scan).toLocaleString() : "Not available"}`; } catch { $("#system").textContent = "System information unavailable."; }
  try { const data = await getJson("/api/permissions"); $("#permission").textContent = data.message; } catch { $("#permission").textContent = "Permission status unavailable."; }
}

async function loadHistory() {
  try { const scans = await getJson("/api/scans"); $("#history").innerHTML = scans.length ? scans.map((scan) => `<div class="scan-history"><span>${new Date(scan.date).toLocaleString()} · ${escapeHtml(scan.computer)}<br>${scan.drivers} drivers · ${scan.counts.NORMAL} normal · ${scan.counts.SUSPICIOUS} suspicious · ${scan.counts.FAULTY} faulty</span><span>${escapeHtml(scan.status)} ${scan.status === "completed" ? `<button class="link view-scan" data-id="${scan.id}">View</button>` : ""}</span></div>`).join("") : "No stored scans yet."; } catch { $("#history").textContent = "Scan history is unavailable. Check the local database connection."; }
}

async function poll() {
  try {
    const data = await getJson(`/api/scan/${scanId}/progress`);
    $("#stage").textContent = data.stage; $("#percent").textContent = `${data.progress}%`; $("#bar").style.width = `${data.progress}%`;
    $("#scanMeta").textContent = `${data.drivers_found || 0} drivers · ${data.events_processed || 0} events · ${data.crash_records || 0} crash records`;
    if (["completed", "failed", "cancelled"].includes(data.status)) { if (data.status === "completed") await showResults(scanId); else $("#scanMeta").textContent = data.message || `Scan ${data.status}.`; await loadHistory(); return; }
    setTimeout(poll, 1000);
  } catch (error) { $("#scanMeta").textContent = `Progress unavailable: ${error.message}`; }
}

async function startScan() {
  $("#resultsCard").classList.add("hidden"); $("#progressCard").classList.remove("hidden");
  try { const response = await fetch("/api/scans/start", { method: "POST" }); const data = await response.json(); if (!response.ok) throw new Error(data.error || "Unable to start scan."); scanId = data.id; poll(); } catch (error) { $("#scanMeta").textContent = error.message; }
}

function render(filter) {
  const visible = filter === "ALL" ? results : results.filter((item) => item.classification === filter);
  $("#rows").innerHTML = visible.map((item) => `<tr><td><b>${escapeHtml(item.driver)}</b></td><td>${escapeHtml(item.device)}</td><td><span class="tag ${item.classification}">${escapeHtml(item.classification)}</span></td><td>${(item.confidence * 100).toFixed(1)}%</td><td class="evidence">${escapeHtml(item.evidence)}</td><td><button class="link detail-driver" data-id="${item.id}">Details</button></td></tr>`).join("") || '<tr><td colspan="6">No matching drivers.</td></tr>';
}

async function showResults(id) {
  scanId = id; $("#progressCard").classList.add("hidden");
  try { const data = await getJson(`/api/scan/${id}/results`); results = data.results; $("#resultsCard").classList.remove("hidden"); const scanEvidence = data.scan.unassociated_event_count ? ` ${data.scan.unassociated_event_count} relevant event(s) were retained as scan-level evidence because they could not be confidently linked to a driver.` : ""; const warning = data.scan.warning ? `Collection note: ${data.scan.warning} ` : ""; render("ALL"); } catch (error) { $("#notice").textContent = `Results unavailable: ${error.message}`; }
}

async function detailsFor(driverId) {
  try { const data = await getJson(`/api/scan/${scanId}/driver/${driverId}`); const driver = data.driver, prediction = data.prediction; const predictionHtml = prediction ? `<p><span class="tag ${prediction.classification}">${prediction.classification}</span> ${(prediction.confidence * 100).toFixed(1)}% confidence</p><h3>Evidence</h3><p>${escapeHtml(prediction.evidence)}</p><h3>Recommendation</h3><p>${escapeHtml(prediction.recommendation)}</p>` : "<p class=\"note\">Prediction unavailable for this driver.</p>"; const eventHtml = data.events.length ? `<h3>Associated Event Log records</h3>${data.events.map((event) => `<p class="evidence"><b>${escapeHtml(event.time)}</b> · ${escapeHtml(event.source)} #${escapeHtml(event.id)} · ${escapeHtml(event.severity)}<br>${escapeHtml(event.message)}</p>`).join("")}` : "<p class=\"note\">No Event Log records were confidently associated with this driver. Relevant unmatched events remain scan-level evidence.</p>"; $("#detailContent").innerHTML = `<p class="eyebrow">DRIVER DIAGNOSTIC</p><h2>${escapeHtml(driver.driver_name)}</h2>${predictionHtml}<div class="detail-grid">${[["Device", driver.device_name], ["Provider", driver.provider], ["Version", driver.version], ["Driver date", driver.driver_date], ["Path", driver.driver_path], ["Category", driver.device_category], ["Signature", driver.signature_status], ["Start status", driver.driver_start_status], ["Device status", driver.device_status]].map(([name, value]) => `<div><b>${name}</b><br>${escapeHtml(value)}</div>`).join("")}</div>${eventHtml}<p class="note">This is a diagnostic prediction, not proof that this driver caused a system problem.</p>`; $("#details").showModal(); } catch (error) { alert(`Driver details unavailable: ${error.message}`); }
}

$("#scan").addEventListener("click", startScan); $("#newScan").addEventListener("click", startScan); $("#export").addEventListener("click", () => { if (scanId) window.location = `/api/reports/${scanId}/export`; }); $("#exportPdf").addEventListener("click", () => { if (scanId) window.location = `/api/reports/${scanId}/export?format=pdf`; }); $("#closeDetails").addEventListener("click", () => $("#details").close());
document.addEventListener("click", (event) => { if (event.target.matches(".view-scan")) showResults(Number(event.target.dataset.id)); if (event.target.matches(".detail-driver")) detailsFor(Number(event.target.dataset.id)); if (event.target.matches(".filters button")) { document.querySelectorAll(".filters button").forEach((button) => button.classList.remove("active")); event.target.classList.add("active"); render(event.target.dataset.filter); } });
loadInfo(); loadHistory();
