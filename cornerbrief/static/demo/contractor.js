const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const link = (url, text) => (url && /^https?:\/\//.test(url) ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text || "Source")}</a>` : esc(url || "unknown"));
const tag = (s) => {
  const kind = { matched: "measured", "from records": "measured", unknown: "missing", conflict: "stoptag", recorded: "measured" }[s] || "assumed";
  return `<span class="tag ${kind}">${esc(s)}</span>`;
};
const table = (head, rows) => `<div class="wrap"><table><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
let request = 0, KINDS = {};
const kinds = (list) => (list || []).map((k) => `<span class="kind k-${esc(k)}">${esc(KINDS[k] || k)}</span>`).join("");
const chip = '<span class="demo-chip">DEMONSTRATION</span>';

function render(d) {
  KINDS = d.kinds;
  const seq = d.sequence;
  const dr = d.drafts;
  $("#notice").textContent = `${d.stamp}. ${d.notice}`;
  $("#persona").textContent = d.persona_note;
  $("#out").innerHTML = `
    <section class="panel"><h2>1. Opportunity brief${chip}</h2><p class="hint">Source labels: ${kinds(Object.keys(d.kinds))}</p><p class="hint">${esc(d.company.name)}. ${esc(d.company.note)}</p>
      ${table(["Item", "Value", "Source"], d.brief.map((b) => `<tr><td>${esc(b.item)}</td><td>${kinds(b.kinds)}<br>${esc(b.value)}${b.note ? `<br><span class="hint">${esc(b.note)}</span>` : ""}</td><td>${link(b.source, "Open")}</td></tr>`))}</section>
    <section class="panel"><h2>2. Capability and prequalification match${chip}</h2><p class="hint">Only verified company records count. Anything without one stays unknown.</p>
      ${table(["Need", "Status", "Record"], d.capabilities.map((c) => `<tr><td>${c.url ? link(c.url, c.step) : esc(c.step)}</td><td>${tag(c.status)}</td><td>${kinds(c.kinds)}<br>${esc(c.record || c.note || "")}</td></tr>`))}</section>
    <section class="panel"><h2>3. Draft logistics${chip}</h2>
      ${table(["Item", "What's known", "Status", "Source"], d.logistics.map((l) => `<tr><td>${esc(l.item)}</td><td>${kinds(l.kinds)}<br>${esc(l.value)}${l.note ? `<br><span class="hint">${esc(l.note)}</span>` : ""}</td><td>${tag(l.status)}</td><td>${link(l.source, "Open")}</td></tr>`))}</section>
    <section class="panel"><h2>4. Team and equipment sequence${chip}</h2><p class="hint">Built from fictional sample records and synthetic quantities (revision ${esc(d.revision)}). A step with no production record has an unknown duration, and every later date is unknown.</p>
      ${table(["Step", "Team", "Equipment", "Start", "Finish", "Duration basis"], seq.rows.map((r) => `<tr><td>${esc(r.step)}<br>${kinds([r.quantity_kind])}</td><td>${kinds([r.team_kind])}<br>${esc(r.team)}</td><td>${r.equipment.map((e) => `${kinds([e.kind])} ${esc(e.type)}: ${e.available ? "available" : "not available"}`).join("<br>") || "None listed"}</td><td>${esc(r.start || "unknown")}</td><td>${esc(r.finish || "unknown")}</td><td>${kinds([r.duration_kind])}<br>${esc(r.duration_days ? `${r.duration_days} day(s). ${r.duration_basis}` : r.duration_basis)}</td></tr>`))}
      ${seq.conflicts.length ? `<h3>Conflicts, not resolved</h3><ul class="plain">${seq.conflicts.map((c) => `<li class="stalenote">${kinds(c.kinds)} ${esc(c.text)}</li>`).join("")}</ul>` : "<p>No conflicts found in the sample records.</p>"}</section>
    <section class="panel"><h2>5. Labor rules for this job${chip}</h2><p>${kinds(d.labor_rules.kinds)} ${tag(d.labor_rules.status)} Job ${esc(d.labor_rules.job)}: ${esc(d.labor_rules.agreement || "no agreement recorded")}.</p><p>${esc(d.labor_rules.note)} ${link(d.labor_rules.source, "Project labor agreements")}</p></section>
    <section class="panel"><h2>6. Drafts for a person to review${chip}</h2><p class="hint">${esc(d.authorization)}</p>
      <h3>Requests for information</h3>${table(["Draft", "Question", "Why", "Status"], dr.rfis.map((r) => `<tr><td>${esc(r.number)}</td><td>${kinds(r.kinds)}<br>${esc(r.question)}</td><td>${esc(r.reason)}</td><td>${esc(r.status)}</td></tr>`))}
      <h3>Material request</h3>${table(["Material", "Quantity", "Supplier"], dr.material_request.items.map((m) => `<tr><td>${esc(m.material)}<br>${kinds(m.kinds)}</td><td>${esc(m.quantity)} ${esc(m.unit)}</td><td>${esc(m.supplier)}</td></tr>`))}<p class="hint">${esc(dr.material_request.status)}</p>
      <h3>Daily report, ${esc(dr.daily_report.date)}</h3>${kinds(dr.daily_report.kinds)}<p>${esc(dr.daily_report.location)}</p>${table(["Person", "Hours"], dr.daily_report.entries.map((e) => `<tr><td>${esc(e.person)}</td><td>${esc(e.hours)}</td></tr>`))}<p class="hint">${esc(dr.daily_report.status)}</p>
      <h3>Payroll discrepancy check, ${esc(dr.payroll_check.date)}</h3>${kinds(dr.payroll_check.kinds)}${dr.payroll_check.issues.length ? `<ul class="plain">${dr.payroll_check.issues.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "<p>No differences between the daily report and payroll.</p>"}<p class="hint">${esc(dr.payroll_check.status)}. ${link(dr.payroll_check.source, "Certified payroll")}</p>
    </section>`;
}

async function build() {
  const mine = ++request;
  $("#status").textContent = "Building…"; $("#status").className = "";
  try {
    const res = await fetch(`/api/demo/contractor?${new URLSearchParams({ corner: $("#corner").value, start: $("#start").value })}`);
    const out = await res.json();
    if (mine !== request) return;
    if (!res.ok) throw new Error(out.error || "The demonstration couldn't be built.");
    render(out);
    $("#status").textContent = "Built from the corner's records, synthetic dimensions and fictional company records.";
  } catch (err) {
    if (mine === request) { $("#status").textContent = err.message === "Failed to fetch" ? "The app's server can't be reached. Make sure it's still running." : err.message; $("#status").className = "error"; }
  }
}

async function start() {
  const corners = await (await fetch("/api/corners")).json();
  $("#corner").innerHTML = corners.map((c) => `<option value="${esc(c.key)}">${esc(c.label)}</option>`).join("");
  $("#build").addEventListener("click", build);
  build();
}
start();
