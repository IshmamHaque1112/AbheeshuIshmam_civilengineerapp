const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const canvas = $("#scene"), ctx = canvas.getContext("2d");
const VIEW = { yaw: -0.6, pitch: 0.55, zoom: 1, panX: 0, panY: 0 };
const COLORS = { "bottom chord": "#20272b", "top chord": "#20272b", "end post": "#20272b", vertical: "#0d5c9e", diagonal: "#b8560f", "floor beam": "#7f8785", "top strut": "#7f8785",
  leg: "#20272b", horizontal: "#7f8785", brace: "#0d5c9e", strut: "#0d5c9e" };
let catalog = null, model = null, view = { ...VIEW }, drag = null, request = 0, timer = null, playing = true, t0 = performance.now(), paused = 0;

function project([x, y, z], w, h) {
  const [cx, cy, cz] = model.center, scale = Math.min(w, h) / model.radius * 0.8 * view.zoom;
  const dx = x - cx, dy = y - cy, dz = z - (cz || 0);
  const rx = dx * Math.cos(view.yaw) - dy * Math.sin(view.yaw), ry = dx * Math.sin(view.yaw) + dy * Math.cos(view.yaw);
  return { x: w / 2 + view.panX + rx * scale, y: h / 2 + view.panY - (ry * Math.sin(view.pitch) + dz * Math.cos(view.pitch)) * scale };
}

function gearAngle(g, time) { return g.phase + g.speed * time; }

function draw() {
  const ratio = Math.min(devicePixelRatio || 1, 1.5), w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * ratio; canvas.height = h * ratio; ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, w, h);
  if (!model) return;
  ctx.lineCap = "round";
  for (const l of model.lines) {
    const a = project(l.a, w, h), b = project(l.b, w, h);
    ctx.strokeStyle = COLORS[l.group] || "#20272b"; ctx.lineWidth = l.group === "diagonal" || l.group === "brace" ? 1.6 : 2.2;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }
  if (model.gears) {
    const time = ((playing ? performance.now() : paused) - t0) / 1000 * 0.6;
    model.gears.forEach((g, i) => {
      const angle = gearAngle(g, time), c = Math.cos(angle), s = Math.sin(angle);
      ctx.beginPath();
      g.outline.forEach(([x, y], k) => { const p = project([g.center[0] + x * c - y * s, g.center[1] + x * s + y * c, 0], w, h); k ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y); });
      ctx.closePath(); ctx.fillStyle = ["#c7cac5", "#d9c7a8", "#b9c9d6"][i % 3]; ctx.fill(); ctx.strokeStyle = "#20272b"; ctx.lineWidth = 1; ctx.stroke();
      const hub = project([g.center[0], g.center[1], 0], w, h), mark = project([g.center[0] + g.pitch_radius * 0.8 * c, g.center[1] + g.pitch_radius * 0.8 * s, 0], w, h);
      ctx.strokeStyle = "#a8261d"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(hub.x, hub.y); ctx.lineTo(mark.x, mark.y); ctx.stroke();
    });
  }
  ctx.font = "700 13px Barlow, 'Segoe UI', Arial, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
  const stamp = "ILLUSTRATIVE GEOMETRY · NO STRUCTURAL CHECKS";
  ctx.fillStyle = "rgba(32,39,43,.86)"; ctx.fillRect(10, 10, ctx.measureText(stamp).width + 16, 24); ctx.fillStyle = "#fff"; ctx.fillText(stamp, 18, 22);
}

function loop() { if (model && model.gears && playing) draw(); requestAnimationFrame(loop); }

function facts(m) {
  const items = [`${m.name}: ${m.members} ${m.gears ? "gears" : "members drawn"}`];
  if (!m.gears) items.push(...Object.entries(m.groups).map(([k, v]) => `${v} ${k}${v === 1 ? "" : "s"}`));
  if (m.strut_lengths_ft) items.push(`${m.strut_lengths_ft.length} distinct strut lengths: ${m.strut_lengths_ft.join(", ")} ft`);
  if (m.base_note) items.push(m.base_note);
  if (m.ratio) items.push(m.ratio, m.profile_note);
  $("#fact-list").innerHTML = items.map((x) => `<li>${esc(x)}</li>`).join("");
  canvas.setAttribute("aria-label", `Illustrative ${m.name}. ${items.join(". ")}`);
}

function fieldsFor(id) { return catalog.models.find((m) => m.id === id).fields; }

function showForm(id) {
  $("#params").innerHTML = fieldsFor(id).map((f) => `<div class="dim"><label for="${f.id}">${esc(f.label)}${f.unit !== "count" ? ` (${esc(f.unit)})` : ""}</label>
    <input id="${f.id}" type="number" inputmode="decimal" min="${f.low}" max="${f.high}" step="${f.integer ? (f.even ? 2 : 1) : "any"}" value="${f.default}" aria-describedby="${f.id}-error">
    <p class="fielderror" id="${f.id}-error" aria-live="polite"></p></div>`).join("");
  fieldsFor(id).forEach((f) => $(`#${f.id}`).addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(update, 150); }));
  $("#play").hidden = id !== "gears";
}

async function update() {
  const mine = ++request, id = $("#model-choice").value;
  const body = { model: id, ...Object.fromEntries(fieldsFor(id).map((f) => [f.id, $(`#${f.id}`).value])) };
  document.querySelectorAll(".fielderror").forEach((e) => { e.textContent = ""; });
  try {
    const res = await fetch("/api/demo/structures", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const out = await res.json();
    if (mine !== request) return;
    if (res.status === 400 && out.problems) {
      for (const [k, v] of Object.entries(out.problems)) { const e = $(`#${k}-error`); if (e) e.textContent = v; }
      $("#status").textContent = "Not updated. Fix the fields marked above. The last valid model is still shown."; $("#status").className = "error";
      return;
    }
    if (!res.ok) throw new Error(out.error || "The model couldn't be built.");
    const changed = !model || model.model !== out.model;
    model = out; if (changed) view = { ...VIEW, pitch: out.gears ? 1.35 : VIEW.pitch };
    facts(out); draw();
    $("#status").textContent = "Model updated."; $("#status").className = "";
  } catch (err) {
    if (mine === request) { $("#status").textContent = err.message === "Failed to fetch" ? "The app's server can't be reached. Make sure it's still running." : err.message; $("#status").className = "error"; }
  }
}

canvas.addEventListener("contextmenu", (e) => e.preventDefault());
canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, pan: e.shiftKey || e.button !== 0 }; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (drag.pan) { view.panX += dx; view.panY += dy; } else { view.yaw += dx * 0.01; view.pitch = Math.max(0.05, Math.min(1.5, view.pitch + dy * 0.01)); }
  drag.x = e.clientX; drag.y = e.clientY; draw();
});
canvas.addEventListener("pointerup", () => { drag = null; });
canvas.addEventListener("wheel", (e) => { e.preventDefault(); view.zoom = Math.max(0.3, Math.min(6, view.zoom * (e.deltaY < 0 ? 1.12 : 1 / 1.12))); draw(); }, { passive: false });
canvas.addEventListener("keydown", (e) => {
  const turn = { ArrowLeft: [-0.12, 0], ArrowRight: [0.12, 0], ArrowUp: [0, 0.08], ArrowDown: [0, -0.08] }[e.key];
  if (turn) { e.preventDefault(); view.yaw += turn[0]; view.pitch = Math.max(0.05, Math.min(1.5, view.pitch + turn[1])); draw(); }
  if (e.key === "+" || e.key === "=") { view.zoom = Math.min(6, view.zoom * 1.12); draw(); }
  if (e.key === "-") { view.zoom = Math.max(0.3, view.zoom / 1.12); draw(); }
});
$("#zoom-in").addEventListener("click", () => { view.zoom = Math.min(6, view.zoom * 1.12); draw(); });
$("#zoom-out").addEventListener("click", () => { view.zoom = Math.max(0.3, view.zoom / 1.12); draw(); });
$("#view-reset").addEventListener("click", () => { view = { ...VIEW, pitch: model && model.gears ? 1.35 : VIEW.pitch }; draw(); });
$("#play").addEventListener("click", () => {
  if (playing) { paused = performance.now(); playing = false; $("#play").textContent = "Play"; }
  else { t0 += performance.now() - paused; playing = true; $("#play").textContent = "Pause"; }
});
new ResizeObserver(draw).observe(canvas);

async function start() {
  catalog = await (await fetch("/api/demo/structures")).json();
  $("#notice").textContent = catalog.notice;
  $("#model-choice").innerHTML = catalog.models.map((m) => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join("");
  $("#model-choice").addEventListener("change", () => { showForm($("#model-choice").value); update(); });
  showForm(catalog.models[0].id);
  await update();
  requestAnimationFrame(loop);
}
start();
