const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const canvas = $("#scene"), ctx = canvas.getContext("2d");
const VIEW = { yaw: -0.7, pitch: 0.8, zoom: 1, panX: 0, panY: 0 };
let view = { ...VIEW }, model = null, lastQuantities = null, fields = [], requestNumber = 0, timer = null, drag = null;

function shade(hex, f) { const n = parseInt(hex.slice(1), 16); return `rgb(${[n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.round(v * f)).join(",")})`; }

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
  for (const dim of model.dimensions) {
    const a = project(dim.a), b = project(dim.b), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    ctx.strokeStyle = "#0d5c9e"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    for (const end of [a, b]) { ctx.beginPath(); ctx.arc(end.x, end.y, 2.5, 0, 7); ctx.fillStyle = "#0d5c9e"; ctx.fill(); }
    const width = ctx.measureText(dim.label).width + 10;
    ctx.fillStyle = "rgba(245,246,243,.94)"; ctx.fillRect(mx - width / 2, my - 10, width, 20);
    ctx.fillStyle = "#232b2f"; ctx.fillText(dim.label, mx, my);
  }
  ctx.font = "700 13px Barlow, 'Segoe UI', Arial, sans-serif"; ctx.textAlign = "left"; ctx.fillStyle = "#fff";
  const stamp = `SYNTHETIC · revision ${model.revision}${lift > 1 ? " · height 3×" : ""}`;
  ctx.fillStyle = "rgba(32,39,43,.86)"; ctx.fillRect(10, 10, ctx.measureText(stamp).width + 16, 24);
  ctx.fillStyle = "#fff"; ctx.fillText(stamp, 18, 22);
}

function showModel(next) {
  model = next;
  const before = lastQuantities;
  const format = (n) => `${+n.toFixed(2)}`;
  $("#quantities").innerHTML = next.quantities.map((q) => {
    const old = before && before[q.id], delta = old == null ? 0 : q.qty - old;
    return `<tr><td>${esc(q.label)}</td><td>${format(q.qty)} ${esc(q.unit === "count" ? "" : q.unit)}</td><td>${Math.abs(delta) < 0.005 ? "—" : `${delta > 0 ? "+" : "−"}${format(Math.abs(delta))}`}</td></tr>`;
  }).join("");
  lastQuantities = Object.fromEntries(next.quantities.map((q) => [q.id, q.qty]));
  $("#revision").textContent = `Revision ${next.revision}. Provisional, from synthetic inputs and sample assumptions. Rise ${next.rise_in} in. ${next.review_note}`;
  canvas.setAttribute("aria-label", `Synthetic 3D model, revision ${next.revision}: ${next.dimensions.map((d) => d.label).join(", ")}.`);
  $("#assumptions").innerHTML = next.assumptions.map((a) => `<li>${esc(a.id.replaceAll("_", " "))}: ${esc(a.value)}${a.unit ? ` ${esc(a.unit)}` : ""}${a.note ? `. ${esc(a.note)}` : ""}</li>`).join("");
  $("#exclusions").innerHTML = next.exclusions.map((x) => `<li>${esc(x)}</li>`).join("");
  draw();
}

function setStatus(text, isError) { const s = $("#status"); s.textContent = text; s.className = isError ? "error" : ""; }

async function update() {
  const mine = ++requestNumber, values = Object.fromEntries(fields.map((f) => [f.id, $(`#${f.id}`).value]));
  document.querySelectorAll(".fielderror").forEach((e) => { e.textContent = ""; });
  fields.forEach((f) => $(`#${f.id}`).removeAttribute("aria-invalid"));
  try {
    const res = await fetch("/api/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    const out = await res.json();
    if (mine !== requestNumber) return;
    if (res.status === 400 && out.problems) {
      for (const [id, text] of Object.entries(out.problems)) {
        const box = $(`#error-${CSS.escape(id)}`), input = $(`#${CSS.escape(id)}`);
        if (box) box.textContent = text;
        if (input) input.setAttribute("aria-invalid", "true");
      }
      setStatus("The model still shows the last valid dimensions, so nothing was guessed.", true);
      return;
    }
    if (!res.ok) throw new Error(out.error || "The preview couldn't update.");
    setStatus("Model and quantities are up to date.", false);
    showModel(out);
  } catch (err) {
    if (mine === requestNumber) setStatus(err.message === "Failed to fetch" ? "The app's server can't be reached. Make sure it's still running." : err.message, true);
  }
}
const schedule = () => { clearTimeout(timer); timer = setTimeout(update, 120); };

function resetValues() { for (const f of fields) { $(`#${f.id}`).value = f.default; $(`#${f.id}-range`).value = f.default; } }

async function start() {
  const res = await fetch("/api/preview");
  const info = await res.json();
  fields = info.fields;
  $("#notice").textContent = info.notice;
  $("#dims").innerHTML = fields.map((f) => `<div class="dim"><label for="${f.id}">${esc(f.label)} (${esc(f.unit)})</label><div class="dimrow"><input id="${f.id}-range" type="range" min="${f.low}" max="${f.high}" step="0.1" value="${f.default}" aria-label="${esc(f.label)} slider"><input id="${f.id}" type="number" step="any" min="${f.low}" max="${f.high}" value="${f.default}" aria-describedby="error-${f.id}"></div><p class="fielderror error" id="error-${f.id}"></p></div>`).join("");
  for (const f of fields) {
    const number = $(`#${f.id}`), range = $(`#${f.id}-range`);
    number.addEventListener("input", () => { if (number.value !== "") range.value = number.value; schedule(); });
    range.addEventListener("input", () => { number.value = range.value; schedule(); });
  }
  $("#dims").addEventListener("submit", (event) => event.preventDefault());
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
