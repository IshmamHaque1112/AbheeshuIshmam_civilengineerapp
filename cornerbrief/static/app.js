const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const link = (text, url) => url ? `<a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(text || "Source")}</a>` : esc(text);
const money = (n) => "$" + Number(n).toLocaleString("en-US");
let current = null;
let requestId = 0; // Only the newest corner request may change the page
const today = () => { const d = new Date(); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };

const previewTag = (o) => o.preview === "limit exceeded" ? ` <span class="tag preview-over">Above limit if confirmed</span>` : o.preview ? ` <span class="tag preview-in">Within limit if confirmed</span>` : "";
const resultTag = (r) => ({ "limit exceeded": `<span class="tag exceeded">Limit exceeded</span>`, "no conflict found": `<span class="tag clear">No conflict found</span>`, "unknown": `<span class="tag">Unknown</span>`, "not applicable": `<span class="tag na">Not applicable</span>` }[r]);
const stateTitle = (s) => s[0].toUpperCase() + s.slice(1);
const fieldNames = { ramp_running_slope_total: "Running slope", ramp_cross_slope: "Ramp cross slope", ramp_width: "Ramp width", ramp_length: "Ramp length", lnd_width: "Landing width", lnd_length: "Landing length", lnd_cross_slope: "Landing cross slope", curb_reveal: "Lip height", gutter_slope: "Gutter slope", counter_slope: "Roadway slope", sidewalk_width: "Sidewalk width", legal_grade: "Legal grade", ramp_type: "Ramp type", sidewalk_transverse_slope: "Sidewalk slope", road_control: "Road control", ramp_rise: "Ramp rise", ramp_right_flare: "Right flare", ramp_left_flare: "Left flare", counter_slope: "Roadway slope" };

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "The request failed.");
  return data;
}
const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

async function start() {
  const corners = await api("/api/corners");
  $("#picker").innerHTML = corners.map((c) => `<button data-key="${esc(c.key)}"><span>${esc(c.label)}</span><small>${c.data_kind === "SAMPLE DATA" ? "Sample data" : "Real test, NYC Open Data"}</small></button>`).join("");
  document.querySelectorAll("#picker button").forEach((b) => b.addEventListener("click", () => run(b.dataset.key)));
  run(corners[0].key);
}

async function run(key) {
  const mine = ++requestId;
  document.querySelectorAll("#picker button").forEach((b) => b.setAttribute("aria-current", b.dataset.key === key));
  current = null;
  $("#main").innerHTML = `<p class="empty">Preparing the packet.</p>`;
  try { const out = await post(`/api/corners/${key}/run`); if (mine === requestId) { current = out; render(); } }
  catch (err) { if (mine === requestId) $("#main").innerHTML = `<p class="empty error">${esc(err.message)}</p>`; }
}

function rulesTable(rows) {
  return `<div class="wrap"><table><thead><tr><th>Rule</th><th>Ramp</th><th>Limit</th><th>Result</th><th>Math or reason</th><th>Source</th></tr></thead><tbody>${rows.map((o) => `<tr><td>${esc(o.title)}</td><td>${esc(o.ramp_id || "")}</td><td>${esc(o.limit_text)}</td><td>${resultTag(o.result)}${previewTag(o)}</td><td>${esc(o.math || o.reason)}</td><td>${link(o.section || "Source", o.url)}${o.quote ? `<blockquote>${esc(o.quote)}</blockquote>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
}

function plan(p) {
  const c = p.cost;
  return `<section><h2>Concept plan</h2>
    <p class="lead">${esc(c.label)}</p>
    ${c.hidden ? `<p>${esc(c.note)}</p><div class="wrap"><table><thead><tr><th>Item</th><th>Quantity</th></tr></thead><tbody>${p.takeoff.items.map((i) => `<tr><td>${esc(i.label)}</td><td>${i.qty} ${esc(i.unit === "count" ? "" : i.unit)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="money">${c.result === "unknown" ? "Unknown" : `${money(c.low)} to ${money(c.high)}`}</p>
    <p>${c.contains_sample_rates ? "<strong>These numbers use placeholder sample rates, not market prices.</strong> " : ""}${esc(c.range_note)}</p>
    <div class="wrap"><table><thead><tr><th>Item</th><th>Quantity</th><th>Rate</th><th>Amount</th><th>Rate status</th></tr></thead><tbody>${c.lines.map((l) => `<tr><td>${esc(l.item)}</td><td>${l.quantity} ${esc(l.unit || "")}</td><td>${l.rate == null ? "Unknown" : `${money(l.rate)} per ${esc(l.unit)}`}</td><td>${l.amount == null ? "Unknown" : money(l.amount)}</td><td>${esc(l.status)}${l.rate_out_of_date ? ", out of date" : ""}</td></tr>`).join("")}</tbody></table></div>`}
    <h3>Labor hours</h3>${p.crew.result === "unknown" ? "<p>Unknown, because a crew rate is missing.</p>" : `<ul class="plain">${p.crew.hours.map((h) => `<li>${esc(h.trade)}: ${h.hours} hours${p.crew.contains_sample_rates ? ", from sample rates" : ""}${p.crew.rates_out_of_date ? ", from an out-of-date rate" : ""}</li>`).join("")}</ul>`}
    <h3>Work sequence</h3><ol>${p.crew.sequence.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>
    <h3>Likely equipment types</h3><ul class="plain">${p.equipment.map((e) => `<li>${esc(e.type)}: ${esc(e.use)}</li>`).join("")}</ul>
    <h3>Not included</h3><p>${p.takeoff.exclusions.map(esc).join(". ")}.</p>
    <h3>Assumptions</h3><ul class="plain">${p.takeoff.assumptions.map((a) => `<li>${esc(a.basis)}</li>`).join("")}</ul>
    <h3>Questions for a safety professional</h3><p>This isn't a safety plan or a final PPE list.</p><ul class="plain">${p.safety_questions.map((q) => `<li>${esc(q.question)} ${q.url ? link("Source", q.url) : ""}</li>`).join("")}</ul>
  </section>`;
}

function releasePanel(r) {
  if (r.approval) return `<div class="panel" id="release"><h2>Released</h2><p>Released by ${esc(r.approval.reviewer)}. Releasing is not approval.</p>
    <a class="button" href="/api/runs/${esc(r.id)}/download">Download packet</a>
    ${r.features.email ? `<label for="to">Email to a test address</label><input id="to" type="email" autocomplete="off"><button class="button alt" id="send">Email packet</button>` : ""}<p id="msg" role="status"></p></div>`;
  return `<div class="panel" id="release"><h2>Release this packet</h2><p>Download stays off until a person enters their name. Releasing is not approval.</p>
    <label for="reviewer">Your name</label><input id="reviewer" autocomplete="name"><button class="button" id="approve">Release packet</button><p id="msg" role="status"></p></div>`;
}

const showValue = (v, unit) => v == null ? "none" : `${esc(v)}${unit ? ` ${esc(unit === "percent" ? "%" : unit)}` : ""}`;

function changesSection(c) {
  return `<section class="changes"><h2>What changed</h2><p><strong>State:</strong> ${c.state_before === c.state_after ? `still ${esc(c.state_after)}` : `${esc(c.state_before)} → ${esc(c.state_after)}`}.</p>
    ${c.inputs.length ? `<h3>Inputs</h3><div class="wrap"><table><thead><tr><th>Input</th><th>Ramp</th><th>Before</th><th>Now</th></tr></thead><tbody>${c.inputs.map((i) => `<tr><td>${esc(fieldNames[i.field] || i.field)}</td><td>${esc(i.ramp_id || "")}</td><td>${esc(i.before_label)}: ${showValue(i.before_value, i.unit)}</td><td>${i.on_site && i.after_label === "measured" ? "measured on site" : esc(i.after_label)}: ${showValue(i.after_value, i.unit)}</td></tr>`).join("")}</tbody></table></div>` : ""}
    ${c.results.length ? `<h3>Results</h3><div class="wrap"><table><thead><tr><th>Rule</th><th>Ramp</th><th>Before</th><th>Now</th><th>Math or reason</th></tr></thead><tbody>${c.results.map((x) => `<tr><td>${esc(x.title)}</td><td>${esc(x.ramp_id || "")}</td><td>${esc(x.before)}</td><td>${esc(x.after)}${x.unreviewed ? ", unreviewed" : ""}</td><td>${esc(x.math)}</td></tr>`).join("")}</tbody></table></div>` : ""}
    ${c.site_visit_done.length ? `<h3>Site visit items no longer needed</h3><ul class="plain">${c.site_visit_done.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</section>`;
}

function fieldForm(r) {
  if (!r.field_inputs.length) return "";
  return `<section id="field"><h2>Add site measurements</h2><p>Enter what you measured, then rerun the check. Each value is labeled as measured on site, with its date.</p>
    <div class="fieldhead"><div><label for="by">Measured by</label><input id="by" autocomplete="name"></div><div><label for="on">Date measured</label><input id="on" type="date" value="${today()}" max="${today()}"></div></div>
    <div class="wrap"><table><thead><tr><th>Input</th><th>Ramp</th><th>Now</th><th>Value</th><th>Photo</th></tr></thead><tbody>${r.field_inputs.map((f, i) => `<tr><td><label class="cell" for="v${i}">${esc(fieldNames[f.field] || f.field)}</label></td><td>${esc(f.ramp_id || "")}</td><td><span class="tag ${esc(f.label)}">${f.on_site && f.label === "measured" ? "on site" : esc(f.label)}</span></td><td class="entry">${f.choices ? `<select id="v${i}" data-key="${esc(f.key)}"><option value=""></option>${f.choices.map((c) => `<option ${c === f.value ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>` : `<input id="v${i}" data-key="${esc(f.key)}" type="number" step="any" value="${f.value ?? ""}" aria-label="${esc(fieldNames[f.field] || f.field)} in ${esc(f.unit)}"><span>${esc(f.unit === "percent" ? "%" : f.unit)}</span>`}</td><td><input data-photo="${esc(f.key)}" type="file" accept="image/jpeg,image/png,image/webp" aria-label="Photo for ${esc(fieldNames[f.field] || f.field)}"></td></tr>`).join("")}</tbody></table></div>
    <button class="button" id="rerun">Rerun the check</button><p id="fieldmsg" role="status"></p></section>`;
}

const readFile = (file) => new Promise((ok, no) => { const fr = new FileReader(); fr.onload = () => ok({ name: file.name, data: fr.result }); fr.onerror = () => no(new Error("A photo couldn't be read.")); fr.readAsDataURL(file); });

function wireField() {
  const button = $("#rerun");
  if (!button) return;
  button.addEventListener("click", async () => {
    const mine = requestId, msg = $("#fieldmsg");
    msg.textContent = ""; msg.className = "";
    button.disabled = true;
    try {
      const entries = [];
      for (const input of document.querySelectorAll("#field [data-key]")) {
        if (input.value === "") continue;
        const file = document.querySelector(`#field [data-photo="${CSS.escape(input.dataset.key)}"]`).files[0];
        entries.push({ key: input.dataset.key, value: input.value, photo: file ? await readFile(file) : null });
      }
      const out = await post(`/api/runs/${current.id}/field`, { entries, date: $("#on").value, by: $("#by").value });
      if (mine !== requestId) return;
      current = out; render(); window.scrollTo(0, 0);
    } catch (err) {
      if (mine !== requestId) return;
      msg.textContent = err.message; msg.className = "error"; button.disabled = false;
    }
  });
}

function render() {
  const r = current;
  const shown = r.rule_results.filter((o) => o.preview || o.result === "limit exceeded" || o.result === "no conflict found");
  const open = r.rule_results.filter((o) => o.result === "unknown" && !o.preview);
  const na = r.rule_results.filter((o) => o.result === "not applicable");
  const nyDecision = r.applicability.find((d) => d.rule_id === "NYS-BCNYS-2025");
  $("#main").innerHTML = `
    <div class="status ${r.state.startsWith("stop") ? "stop" : ""}"><strong>${esc(stateTitle(r.state))}</strong><p>${esc(r.state_reason)}</p>${r.label ? `<p class="label">${esc(r.label_reason)}</p>` : ""}</div>
    <div class="alert">${esc(r.notice)}${r.corner.data_kind === "SAMPLE DATA" ? ` <span>SAMPLE DATA: this corner is made up for the demo.</span>` : ` <span>Real test corner from NYC Open Data.</span>`}</div>
    <div class="sheet">
    <div class="brief">
      <section><h2>Summary</h2><p class="lead">${esc(r.brief.summary)}</p><p>${esc(r.brief.findings_narrative)}</p><p>${esc(r.brief.engineer_note)}</p>
      ${r.review_status === "incomplete" ? `<p class="error">The agent review didn't finish. Treat this packet as incomplete.</p>` : ""}
      ${r.mode === "offline, no agents" ? `<p class="hint">No agents ran for this version of the packet, so it used 0 tokens. A fresh Skeptic review needs an API key.</p>` : r.mode === "demo replay" ? `<p class="hint">Agent text comes from saved demo responses, so this run made no API calls and used 0 tokens.</p>` : `<p class="hint">Agent tokens used: ${r.tokens.input + r.tokens.output}.</p>`}</section>
      ${r.changes ? changesSection(r.changes) : ""}
      ${r.problems.length ? `<section><h2>Evidence still needed</h2><ul class="plain">${r.problems.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></section>` : ""}
      <section><h2>Corner records</h2>
        ${r.dataset_note ? `<p><strong>${esc(r.dataset_note)}</strong></p>` : ""}
        ${r.records.program.map((p) => `<p><strong>Program status:</strong> ${esc(p.status)}${p.construction_type ? `, ${esc(p.construction_type)}` : ""}${p.completed ? `, completed ${esc(p.completed)}` : ""}.</p>`).join("")}
        <div class="wrap"><table><thead><tr><th>Ramp</th><th>Surveyed</th><th>Warning surface</th><th>Ponding</th><th>Obstacles</th></tr></thead><tbody>${r.records.ramps.map((x) => `<tr><td>${esc(x.ramp_id)}</td><td>${esc(x.surveyed)}</td><td>${esc(x.warning_surface)}</td><td>${esc(x.ponding)}</td><td>Ramp: ${esc(x.obstacles_ramp)}. Landing: ${esc(x.obstacles_landing)}.</td></tr>`).join("")}</tbody></table></div>
        ${r.records.complaints.map((c) => `<p><strong>Complaint ${esc(c.id)}:</strong> ${esc(c.date)}. Temporary repair feasible: ${esc(c.repair_feasible)}.</p>`).join("")}
        ${r.join_notes.map((n) => `<p>${esc(n)}</p>`).join("")}
      </section>
      <section><h2>Which rules apply</h2><p><strong>City or state:</strong> ${esc(nyDecision.reason)} ${link(nyDecision.source_section, nyDecision.url)}</p>
      <details><summary>All ${r.applicability.length} rule decisions</summary><div class="wrap"><table><thead><tr><th>Rule</th><th>Applies</th><th>Why</th><th>Basis</th></tr></thead><tbody>${r.applicability.map((d) => `<tr><td>${esc(d.title)}</td><td>${d.applies ? "Yes" : "No"}</td><td>${esc(d.reason)}</td><td>${link(d.source_section, d.url)}</td></tr>`).join("")}</tbody></table></div></details>
      <p class="hint">${r.rule_review.verified} of ${r.rule_review.verified + r.rule_review.awaiting_human_review.length} sourced rules have a named reviewer, so limit results stay unknown until then. ${r.rules_needing_sources.length} rules still need sources, and ${r.rule_review.precedence_awaiting_review.length} which-rule-applies decisions still need review.${r.rule_review.source_check_overdue.length ? ` ${r.rule_review.source_check_overdue.length} source checks are over a year old.` : ""}</p></section>
      ${r.options.length || r.constraints.length || r.challenges.length ? `<section><h2>${r.options.length ? "Likely options" : "Constraints and Skeptic notes"}</h2>${r.options.map((o) => `<h3>${esc(o.ramp_type)}</h3><p>${esc(o.rationale)}</p>`).join("")}${r.constraints.length ? `<h3>Constraints</h3><ul class="plain">${r.constraints.map((c) => `<li>${esc(c.text)}</li>`).join("")}</ul>` : ""}${r.challenges.length ? `<h3>Skeptic notes</h3><ul class="plain">${r.challenges.map((c) => `<li><strong>${esc(c.claim)}:</strong> ${esc(c.issue)}</li>`).join("")}</ul>` : ""}${r.retries ? `<p class="hint">The Skeptic sent this back ${r.retries === 1 ? "once" : `${r.retries} times`} before it was accepted.</p>` : ""}</section>` : ""}
      <section><h2>Site visit list</h2><div class="wrap"><table><thead><tr><th>Where</th><th>What to do</th><th>Why</th></tr></thead><tbody>${r.site_visit.map((v) => `<tr><td>${esc(v.where)}</td><td>${esc(v.action)}</td><td>${esc(v.why)}</td></tr>`).join("")}</tbody></table></div></section>
      ${fieldForm(r)}
      <section><h2>Rule results</h2>${shown.length ? `<p>Math marked "unreviewed calculation" comes from rule files no named person has checked yet.</p>${rulesTable(shown)}` : "<p>Limit checks were skipped for this corner.</p>"}
        ${open.length ? `<details><summary>${open.length} rules are unknown</summary>${rulesTable(open)}</details>` : ""}
        ${na.length ? `<details><summary>${na.length} rules don't apply</summary>${rulesTable(na)}</details>` : ""}</section>
      ${r.design_targets.length ? `<section><h2>If this corner is rebuilt</h2><p>H-1011 sets stricter targets for new design and field layout than for accepting finished work. These don't apply to the existing ramp.</p><details><summary>${r.design_targets.filter((o) => (o.preview || o.result) === "limit exceeded").length} of ${r.design_targets.length} design target calculations are outside the target</summary>${rulesTable(r.design_targets)}</details></section>` : ""}
      ${r.conflicts.length ? `<section><h2>Rule conflicts for engineer review</h2>${r.conflicts.map((c) => `<p><strong>${esc(fieldNames[c.parameter] || c.parameter)}:</strong> ${esc(c.warning)}</p><ul class="plain">${c.rules.map((x) => `<li>${link(x.section, x.url)}: ${esc(x.limit)}</li>`).join("")}</ul><p class="hint">Warning uses the stricter value${c.stricter_min != null ? `: minimum ${+c.stricter_min.toFixed(2)}${c.unit === "percent" ? "%" : " in"}` : ""}${c.stricter_max != null ? `${c.stricter_min != null ? " and" : ":"} maximum ${+c.stricter_max.toFixed(2)}${c.unit === "percent" ? "%" : " in"}` : ""}. An engineer decides which rule controls.</p>`).join("")}</section>` : ""}
      <section><h2>Evidence</h2><details ${r.sufficient ? "" : "open"}><summary>${r.evidence.length} inputs and their labels</summary><div class="wrap"><table><thead><tr><th>Input</th><th>Ramp</th><th>Value</th><th>Label</th><th>Source and date</th><th>Note</th></tr></thead><tbody>${r.evidence.map((e) => `<tr><td>${esc(fieldNames[e.field] || e.field)}</td><td>${esc(e.ramp_id || "")}</td><td>${e.value == null ? "" : `${esc(e.value)} ${esc(e.unit === "percent" ? "%" : e.unit)}`}</td><td><span class="tag ${esc(e.label)}">${e.on_site && e.label === "measured" ? "measured on site" : esc(e.label)}</span></td><td>${esc(e.source)}${e.date ? `, ${esc(e.date)}` : ""}${e.photo ? ` ${link("Photo", `/api/photos/${e.photo}`)}` : ""}</td><td>${esc(e.reason)}</td></tr>`).join("")}</tbody></table></div></details></section>
      ${r.planning ? plan(r.planning) : ""}
      ${r.background.items.length ? `<section><h2>Background reading</h2><p>${esc(r.background.note)}</p><ul class="plain">${r.background.items.map((b) => `<li>${link(b.title, b.url)}${b.year ? `, ${esc(b.year)}` : ""}</li>`).join("")}</ul></section>` : ""}
      ${r.rejections.length ? `<section><h2>Rejected agent output</h2><ul class="plain">${r.rejections.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></section>` : ""}
    </div>
    <aside class="side">
      ${r.features.labels_and_plans ? `<div class="panel"><h2>Concept model</h2>${r.planning ? `<canvas id="model" tabindex="0" role="img" aria-label="Concept 3D model of the corner's ramps. Drag or use the arrow keys to rotate."></canvas><p class="hint">${esc(r.planning.concept_label)}. Yellow marks the detectable warning surface. Drag or use the arrow keys to rotate.</p>` : `<p>${esc(r.planning_note)}</p>`}</div>` : ""}
      ${releasePanel(r)}
    </aside></div>`;
  wireRelease();
  wireField();
  if (r.planning) drawModel(r.planning.scene);
}

function wireRelease() {
  const msg = $("#msg");
  const approve = $("#approve");
  if (approve) approve.addEventListener("click", async () => {
    const mine = requestId;
    try { const out = await post(`/api/runs/${current.id}/approve`, { reviewer: $("#reviewer").value }); if (mine !== requestId) return; current = out; $("#release").outerHTML = releasePanel(current); wireRelease(); $("#msg").textContent = "Released. You can now download it."; $("#msg").className = "ok"; }
    catch (err) { if (mine === requestId) { msg.textContent = err.message; msg.className = "error"; } }
  });
  const send = $("#send");
  if (send) send.addEventListener("click", async () => {
    const mine = requestId;
    try { const out = await post(`/api/runs/${current.id}/email`, { to: $("#to").value }); if (mine === requestId) { msg.textContent = out.message; msg.className = "ok"; } }
    catch (err) { if (mine === requestId) { msg.textContent = err.message; msg.className = "error"; } }
  });
}

function drawModel(scene) {
  const canvas = $("#model"), ctx = canvas.getContext("2d");
  let yaw = -0.7, pitch = 0.75, drag = null;
  function shade(hex, f) { const n = parseInt(hex.slice(1), 16); return `rgb(${[n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.round(v * f)).join(",")})`; }
  function draw() {
    const ratio = Math.min(devicePixelRatio || 1, 1.5), w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = w * ratio; canvas.height = h * ratio; ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, w, h);
    const [cx, cy] = scene.center, scale = Math.min(w, h) / scene.radius * 1.05;
    const project = ([x, y, z]) => {
      const dx = x - cx, dy = y - cy, zz = z * 2.2;
      const rx = dx * Math.cos(yaw) - dy * Math.sin(yaw), ry = dx * Math.sin(yaw) + dy * Math.cos(yaw);
      return { x: w / 2 + rx * scale, y: h * 0.55 - (ry * Math.sin(pitch) + zz * Math.cos(pitch)) * scale, d: ry * Math.cos(pitch) - zz * Math.sin(pitch) };
    };
    const faces = scene.faces.map((f, i) => { const pts = f.p.map(project); return { pts, c: f.c, i, d: pts.reduce((a, p) => a + p.d, 0) / pts.length }; });
    faces.sort((a, b) => (a.i < 2 || b.i < 2) ? a.i - b.i : b.d - a.d || a.i - b.i);
    for (const f of faces) {
      ctx.beginPath(); f.pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.closePath();
      ctx.fillStyle = shade(f.c, 1); ctx.fill(); ctx.strokeStyle = shade(f.c, 0.72); ctx.lineWidth = 1; ctx.stroke();
    }
  }
  canvas.addEventListener("pointerdown", (e) => { drag = [e.clientX, e.clientY]; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => { if (!drag) return; yaw += (e.clientX - drag[0]) * 0.01; pitch = Math.max(0.2, Math.min(1.35, pitch + (e.clientY - drag[1]) * 0.01)); drag = [e.clientX, e.clientY]; draw(); });
  canvas.addEventListener("pointerup", () => { drag = null; });
  canvas.addEventListener("keydown", (e) => {
    const moves = { ArrowLeft: [-0.15, 0], ArrowRight: [0.15, 0], ArrowUp: [0, 0.1], ArrowDown: [0, -0.1] }[e.key];
    if (moves) { e.preventDefault(); yaw += moves[0]; pitch = Math.max(0.2, Math.min(1.35, pitch + moves[1])); draw(); }
  });
  new ResizeObserver(draw).observe(canvas);
  draw();
}
start().catch((err) => { $("#main").innerHTML = `<p class="empty error">${esc(err.message)}</p>`; });
