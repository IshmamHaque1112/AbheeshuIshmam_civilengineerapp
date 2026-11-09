const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const canvas = $("#scene"), ctx = canvas.getContext("2d");
const VIEW = { yaw: -0.7, pitch: 0.8, zoom: 1, panX: 0, panY: 0 };
const exported = window.CORNERBRIEF_PREVIEW_EXPORT; // Set only in the static copy, which has no backend
let draft = null; // The draft sequence as last built. It keeps its revision until someone recalculates it.
let view = { ...VIEW }, model = null, lastQuantities = null, lastRevision = null, stale = null, fields = [], requestNumber = 0, timer = null, drag = null;

function shade(hex, f) { const n = parseInt(hex.slice(1), 16); return `rgb(${[n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.round(v * f)).join(",")})`; }

// Nudge a label up or down until it no longer covers one already drawn, keeping it inside the canvas.
function placeLabel(placed, x, y, width, w, h) {
  const left = Math.max(4, Math.min(w - width - 4, x - width / 2));
  const at = (offset) => ({ x: left, y: Math.max(4, Math.min(h - 24, y - 10 + offset)), w: width, h: 20 });
  const clear = (box) => !placed.some((p) => box.x < p.x + p.w && p.x < box.x + box.w && box.y < p.y + p.h && p.y < box.y + box.h);
  const box = [0, 22, -22, 44, -44, 66, -66, 88, -88].map(at).find(clear) || at(0);
  placed.push(box);
  return box;
}

function draw() {
  const ratio = Math.min(devicePixelRatio || 1, 1.5), w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * ratio; canvas.height = h * ratio; ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, w, h);
  if (!model) return;
  const lift = $("#exaggerate").checked ? 3 : 1;
  const [cx, cy] = model.scene.center, scale = Math.min(w, h) / model.scene.radius * 0.82 * view.zoom;
  const project = ([x, y, z]) => {
    const dx = x - cx, dy = y - cy, zz = z * lift;
    const rx = dx * Math.cos(view.yaw) - dy * Math.sin(view.yaw), ry = dx * Math.sin(view.yaw) + dy * Math.cos(view.yaw);
    return { x: w / 2 + view.panX + rx * scale, y: h / 2 + view.panY - (ry * Math.sin(view.pitch) + zz * Math.cos(view.pitch)) * scale, d: ry * Math.cos(view.pitch) - zz * Math.sin(view.pitch) };
  };
  const faces = model.scene.faces.map((f, i) => { const pts = f.p.map(project); return { pts, c: f.c, i, d: pts.reduce((a, p) => a + p.d, 0) / pts.length }; });
  faces.sort((a, b) => (a.i < 2 || b.i < 2) ? a.i - b.i : b.d - a.d || a.i - b.i);
  for (const f of faces) {
    ctx.beginPath(); f.pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.closePath();
    ctx.fillStyle = shade(f.c, 1); ctx.fill(); ctx.strokeStyle = shade(f.c, 0.7); ctx.lineWidth = 1; ctx.stroke();
  }
  ctx.font = "600 13px Barlow, 'Segoe UI', Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const placed = [];
  for (const dim of model.dimensions) {
    const a = project(dim.a), b = project(dim.b), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    ctx.strokeStyle = "#0d5c9e"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    for (const end of [a, b]) { ctx.beginPath(); ctx.arc(end.x, end.y, 2.5, 0, 7); ctx.fillStyle = "#0d5c9e"; ctx.fill(); }
    const box = placeLabel(placed, mx, my, ctx.measureText(dim.label).width + 10, w, h);
    if (Math.abs(box.y + 10 - my) > 1 || Math.abs(box.x + box.w / 2 - mx) > 1) { // A leader line ties a moved label to its dimension
      ctx.strokeStyle = "rgba(13,92,158,.6)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(box.x + box.w / 2, box.y + 10); ctx.stroke();
    }
    ctx.fillStyle = "rgba(245,246,243,.94)"; ctx.fillRect(box.x, box.y, box.w, box.h);
    ctx.fillStyle = "#232b2f"; ctx.fillText(dim.label, box.x + box.w / 2, box.y + 10);
  }
  canvas.labelBoxes = placed; // Read by the browser tests to check labels don't overlap
  if (stale) { ctx.fillStyle = "rgba(245,246,243,.55)"; ctx.fillRect(0, 0, w, h); }
  ctx.font = "700 13px Barlow, 'Segoe UI', Arial, sans-serif"; ctx.textAlign = "left";
  const stamp = stale ? `NOT UPDATED · fix ${stale.join(", ")} · showing revision ${model.revision}` : `SYNTHETIC · revision ${model.revision}${lift > 1 ? " · height 3×" : ""}`;
  ctx.fillStyle = stale ? "rgba(168,38,29,.94)" : "rgba(32,39,43,.86)"; ctx.fillRect(10, 10, Math.min(w - 20, ctx.measureText(stamp).width + 16), 24);
  ctx.fillStyle = "#fff"; ctx.fillText(stamp, 18, 22, w - 36);
}

function describe() {
  const dims = model.dimensions.map((d) => d.label).join(", ");
  canvas.setAttribute("aria-label", stale ? `Not updated. Fix ${stale.join(", ")}. Still showing synthetic revision ${model.revision}: ${dims}.` : `Synthetic 3D model, revision ${model.revision}: ${dims}.`);
}

function showModel(next) {
  model = next; stale = null;
  const before = lastQuantities, previous = lastRevision;
  const format = (n) => `${+n.toFixed(2)}`;
  $("#quantities").innerHTML = next.quantities.map((q) => {
    const old = before && before[q.id], delta = old == null ? 0 : q.qty - old;
    return `<tr><td>${esc(q.label)}</td><td>${format(q.qty)} ${esc(q.unit === "count" ? "" : q.unit)}</td><td>${Math.abs(delta) < 0.005 ? "—" : `${delta > 0 ? "+" : "−"}${format(Math.abs(delta))}`}</td></tr>`;
  }).join("");
  lastQuantities = Object.fromEntries(next.quantities.map((q) => [q.id, q.qty]));
  lastRevision = next.revision;
  const changed = previous && previous !== next.revision
    ? ` Changed from revision ${previous}: quantities were recalculated, and any estimate or schedule built on ${previous} must be recalculated before use.`
    : ` ${next.review_note}`;
  $("#revision").textContent = `Revision ${next.revision}. Provisional, from synthetic inputs and sample assumptions. Rise ${next.rise_in} in.${changed}`;
  $("#stale").hidden = true; $("#quantity-section").classList.remove("isstale");
  const list = (items) => items.map((x) => `<li>${esc(x)}</li>`).join("");
  $("#basis-synthetic").innerHTML = list(next.input_basis.synthetic);
  $("#basis-assumed").innerHTML = list(next.input_basis.assumed);
  $("#basis-unknown").innerHTML = list(next.input_basis.unknown);
  $("#assumptions").innerHTML = next.assumptions.map((a) => `<li>${esc(a.id.replaceAll("_", " "))}: ${esc(a.value)}${a.unit ? ` ${esc(a.unit)}` : ""}${a.note ? `. ${esc(a.note)}` : ""}</li>`).join("");
  $("#exclusions").innerHTML = next.exclusions.map((x) => `<li>${esc(x)}</li>`).join("");
  if (!draft) draft = next.work_plan;
  showDraft();
  describe(); draw();
}

function showDraft() {
  if (!draft) return;
  const behind = model && draft.built_from_revision !== model.revision;
  $("#draft-status").textContent = `${draft.label} Built from revision ${draft.built_from_revision}.`;
  $("#draft-stale").textContent = behind ? `Needs recalculation: this draft was built from revision ${draft.built_from_revision}, and the model is now revision ${model.revision}. Its quantities are out of date until you recalculate it.` : "";
  $("#draft-stale").hidden = !behind;
  $("#draft-rebuild").hidden = !behind || Boolean(exported);
  $("#draft-section").classList.toggle("isstale", behind);
  $("#draft-steps").innerHTML = draft.steps.map((s) => `<tr><td>${s.number}. ${esc(s.name)}</td><td>${s.quantities.length ? s.quantities.map((q) => `${+q.qty.toFixed(2)} ${esc(q.unit === "count" ? "" : q.unit)} ${esc(q.label.toLowerCase())}`).join("; ") : esc(s.note || "None modeled")}</td><td>${esc(s.equipment_types.join(", ") || "None listed")}</td><td>Unknown, from ${esc(s.duration_source)}</td></tr>`).join("");
  $("#draft-missing").innerHTML = draft.missing_inputs.map((m) => `<li>${esc(m)}</li>`).join("");
}

function setStatus(text, isError) { const s = $("#status"); s.textContent = text; s.className = isError ? "error" : ""; }

function showProblems(problems) {
  for (const [id, text] of Object.entries(problems)) {
    const box = $(`#error-${CSS.escape(id)}`), input = $(`#${CSS.escape(id)}`);
    if (box) box.textContent = text;
    if (input) input.setAttribute("aria-invalid", "true");
  }
  setStatus("The model still shows the last valid dimensions, so nothing was guessed.", true);
  if (!model) return;
  stale = Object.keys(problems).map((id) => (fields.find((f) => f.id === id) || { label: id }).label);
  $("#stale").textContent = `Not updated: fix ${stale.join(", ")}. The model and quantities still show revision ${model.revision}, the last valid dimensions.`;
  $("#stale").hidden = false; $("#quantity-section").classList.add("isstale");
  describe(); draw();
}

// The server checks every value again. This only saves a round trip for blank or out-of-range typing.
function localProblems(values) {
  const problems = {};
  for (const f of fields) {
    const text = String(values[f.id]).trim(), number = Number(text);
    if (text === "" || !Number.isFinite(number) || number < f.low || number > f.high) problems[f.id] = `${f.label} must be a number from ${f.low} to ${f.high} ${f.unit}.`;
  }
  return problems;
}

async function update() {
  const mine = ++requestNumber, values = Object.fromEntries(fields.map((f) => [f.id, $(`#${f.id}`).value]));
  document.querySelectorAll(".fielderror").forEach((e) => { e.textContent = ""; });
  fields.forEach((f) => $(`#${f.id}`).removeAttribute("aria-invalid"));
  const local = localProblems(values);
  if (Object.keys(local).length) { showProblems(local); return; }
  try {
    const res = await fetch("/api/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    const out = await res.json();
    if (mine !== requestNumber) return;
    if (res.status === 400 && out.problems) { showProblems(out.problems); return; }
    if (!res.ok) throw new Error(out.error || "The preview couldn't update.");
    setStatus("Model and quantities are up to date.", false);
    showModel(out);
  } catch (err) {
    if (mine === requestNumber) setStatus(err.message === "Failed to fetch" ? "The app's server can't be reached. Make sure it's still running." : err.message, true);
  }
}
const schedule = () => { clearTimeout(timer); timer = setTimeout(update, 120); };

function resetValues() { for (const f of fields) { $(`#${f.id}`).value = f.default; $(`#${f.id}-range`).value = f.default; } }

$("#draft-rebuild").addEventListener("click", () => { if (model && !stale) { draft = model.work_plan; showDraft(); } });

async function start() {
  const info = exported ? exported.defaults : await (await fetch("/api/preview")).json();
  fields = info.fields;
  $("#notice").textContent = info.notice;
  $("#dims").innerHTML = fields.map((f) => `<div class="dim"><label for="${f.id}">${esc(f.label)} (${esc(f.unit)})</label><div class="dimrow"><input id="${f.id}-range" type="range" min="${f.low}" max="${f.high}" step="0.1" value="${f.default}" aria-label="${esc(f.label)} slider"><input id="${f.id}" type="number" step="any" min="${f.low}" max="${f.high}" value="${f.default}" aria-describedby="error-${f.id}"></div><p class="fielderror error" id="error-${f.id}"></p></div>`).join("");
  $("#dims").addEventListener("submit", (event) => event.preventDefault());
  if (exported) {
    document.querySelectorAll("#dims input, #reset").forEach((input) => { input.disabled = true; });
    document.querySelectorAll('a[href="/"]').forEach((a) => { a.href = "index.html"; });
    showModel(exported.model);
    setStatus("This static copy shows the default model built by the app's Python code. Editing dimensions needs the local CornerBrief app.", false);
    return;
  }
  for (const f of fields) {
    const number = $(`#${f.id}`), range = $(`#${f.id}-range`);
    number.addEventListener("input", () => { if (number.value !== "") range.value = number.value; schedule(); });
    range.addEventListener("input", () => { number.value = range.value; schedule(); });
  }
  $("#reset").addEventListener("click", () => { resetValues(); update(); });
  await update();
}

canvas.addEventListener("contextmenu", (e) => e.preventDefault());
canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, pan: e.shiftKey || e.button !== 0 }; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (drag.pan) { view.panX += dx; view.panY += dy; } else { view.yaw += dx * 0.01; view.pitch = Math.max(0.15, Math.min(1.5, view.pitch + dy * 0.01)); }
  drag.x = e.clientX; drag.y = e.clientY; draw();
});
canvas.addEventListener("pointerup", () => { drag = null; });
canvas.addEventListener("pointercancel", () => { drag = null; });
const zoomBy = (factor) => { view.zoom = Math.max(0.3, Math.min(6, view.zoom * factor)); draw(); };
canvas.addEventListener("wheel", (e) => { e.preventDefault(); zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12); }, { passive: false });
canvas.addEventListener("keydown", (e) => {
  const moves = { ArrowLeft: [-0.15, 0], ArrowRight: [0.15, 0], ArrowUp: [0, 0.1], ArrowDown: [0, -0.1] }[e.key];
  if (moves) { e.preventDefault(); view.yaw += moves[0]; view.pitch = Math.max(0.15, Math.min(1.5, view.pitch + moves[1])); draw(); }
  if (e.key === "+" || e.key === "=") zoomBy(1.2);
  if (e.key === "-") zoomBy(1 / 1.2);
});
$("#zoom-in").addEventListener("click", () => zoomBy(1.2));
$("#zoom-out").addEventListener("click", () => zoomBy(1 / 1.2));
$("#view-reset").addEventListener("click", () => { view = { ...VIEW }; draw(); });
$("#exaggerate").addEventListener("change", draw);
new ResizeObserver(draw).observe(canvas);
start().catch(() => setStatus("The preview couldn't load. Make sure the app is still running.", true));
