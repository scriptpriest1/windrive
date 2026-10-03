let scanId = null,
  results = [];
function esc(s) {
  return $("<div>")
    .text(s || "—")
    .html();
}
function loadInfo() {
  $.getJSON("/api/system-info", (d) =>
    $("#system").html(
      `<b>${esc(d.computer_name)}</b><br>${esc(d.operating_system)}<br>Last scan: ${d.last_scan ? new Date(d.last_scan).toLocaleString() : "Not available"}`,
    ),
  );
  $.getJSON("/api/permissions", (d) => $("#permission").text(d.message));
}
function loadHistory() {
  $.getJSON("/api/scans", (scans) =>
    $("#history").html(
      scans.length
        ? scans
            .map(
              (s) =>
                `<div class="scan-history"><span>${new Date(s.date).toLocaleString()} · ${esc(s.computer)}<br>${s.drivers} drivers · ${s.counts.NORMAL} normal · ${s.counts.SUSPICIOUS} suspicious · ${s.counts.FAULTY} faulty</span><span>${esc(s.status)} ${s.status === "completed" ? `<button class="link" onclick="showResults(${s.id})">View</button>` : ""}</span></div>`,
            )
            .join("")
        : "No stored scans yet.",
    ),
  );
}
function poll() {
  $.getJSON(`/api/scan/${scanId}/progress`, (d) => {
    $("#stage").text(d.stage);
    $("#percent").text(d.progress + "%");
    $("#bar").css("width", d.progress + "%");
    $("#scanMeta").text(
      `${d.drivers_found || 0} drivers · ${d.events_processed || 0} events · ${d.crash_records || 0} crash records`,
    );
    if (["completed", "failed", "cancelled"].includes(d.status)) {
      if (d.status === "completed") showResults(scanId);
      else $("#scanMeta").text(d.message || `Scan ${d.status}.`);
      loadHistory();
      return;
    }
    setTimeout(poll, 1000);
  });
}
$("#scan,#newScan").click(() => {
  $("#resultsCard").addClass("hidden");
  $("#progressCard").removeClass("hidden");
  $.post("/api/scans/start", (d) => {
    scanId = d.id;
    poll();
  }).fail((x) =>
    alert(
      x.responseJSON?.error ||
        "Unable to start scan. Ensure MySQL/XAMPP is running.",
    ),
  );
});
function showResults(id) {
  scanId = id;
  $("#progressCard").addClass("hidden");
  $.getJSON(`/api/scan/${id}/results`, (d) => {
    results = d.results;
    $("#resultsCard").removeClass("hidden");
    $("#notice").text(
      d.scan.warning ||
        "Classifications are probability-based ML predictions and require verification.",
    );
    render("ALL");
  });
}
function render(filter) {
  let r =
    filter === "ALL"
      ? results
      : results.filter((x) => x.classification === filter);
  $("#rows").html(
    r
      .map(
        (x) =>
          `<tr><td><b>${esc(x.driver)}</b></td><td>${esc(x.device)}</td><td><span class="tag ${x.classification}">${x.classification}</span></td><td>${(x.confidence * 100).toFixed(1)}%</td><td class="evidence">${esc(x.evidence)}</td><td><button class="link" onclick="detailsFor(${x.id})">Details</button></td></tr>`,
      )
      .join("") || '<tr><td colspan="6">No matching drivers.</td></tr>',
  );
}
$(".filters button").click(function () {
  $(".filters button").removeClass("active");
  $(this).addClass("active");
  render($(this).data("filter"));
});
function detailsFor(driverId) {
  $.getJSON(`/api/scan/${scanId}/driver/${driverId}`, (d) => {
    let x = d.driver,
      p = d.prediction;
    $("#detailContent").html(
      `<p class="eyebrow">DRIVER DIAGNOSTIC</p><h2>${esc(x.driver_name)}</h2><p><span class="tag ${p.classification}">${p.classification}</span> ${(p.confidence * 100).toFixed(1)}% confidence</p><div class="detail-grid">${[
        ["Device", x.device_name],
        ["Provider", x.provider],
        ["Version", x.version],
        ["Driver date", x.driver_date],
        ["Path", x.driver_path],
        ["Category", x.device_category],
        ["Signature", x.signature_status],
        ["Device status", x.device_status],
      ]
        .map((v) => `<div><b>${v[0]}</b><br>${esc(v[1])}</div>`)
        .join(
          "",
        )}</div><h3>Evidence</h3><p>${esc(p.evidence)}</p><h3>Recommendation</h3><p>${esc(p.recommendation)}</p><p class="note">This is a diagnostic prediction, not absolute proof that this driver caused a problem.</p>`,
    );
    details.showModal();
  });
}
$("#export").click(() => (window.location = `/api/reports/${scanId}/export`));
loadInfo();
loadHistory();
