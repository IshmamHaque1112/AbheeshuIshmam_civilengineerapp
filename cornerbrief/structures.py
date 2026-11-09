"""Roadmap M4 as an illustrative geometry sandbox. No AI here.

Procedural geometry from named parameters, for exploring shape and interaction only. Nothing here sizes a
member, applies a load, checks a code or says anything about strength, stability or safety. These aren't
supported engineering domains, and nothing here reaches a corner packet, a label, a plan or a rule check.
"""
import math

NOTICE = ("Illustrative geometry only. There are no loads, member sizes, materials, connections or structural checks, "
          "and nothing here says whether a structure would stand or work. A qualified engineer and real design work would be needed.")

MODELS = {
    "truss": dict(name="Pratt truss bridge", fields={
        "span_ft": dict(label="Span", unit="ft", low=20, high=300, default=120),
        "panels": dict(label="Panels", unit="count", low=4, high=20, default=8, integer=True, even=True),
        "height_ft": dict(label="Truss height", unit="ft", low=4, high=40, default=16),
        "width_ft": dict(label="Deck width", unit="ft", low=6, high=60, default=24)}),
    "tower": dict(name="Lattice tower", fields={
        "height_ft": dict(label="Height", unit="ft", low=10, high=200, default=90),
        "base_ft": dict(label="Base width", unit="ft", low=4, high=60, default=24),
        "top_ft": dict(label="Top width", unit="ft", low=1, high=60, default=6),
        "sections": dict(label="Sections", unit="count", low=2, high=30, default=9, integer=True)}),
    "dome": dict(name="Geodesic dome", fields={
        "radius_ft": dict(label="Radius", unit="ft", low=5, high=100, default=20),
        "frequency": dict(label="Frequency", unit="count", low=1, high=4, default=2, integer=True)}),
    "gears": dict(name="Gear train", fields={
        "teeth_1": dict(label="Gear 1 teeth", unit="count", low=8, high=60, default=20, integer=True),
        "teeth_2": dict(label="Gear 2 teeth", unit="count", low=8, high=60, default=36, integer=True),
        "teeth_3": dict(label="Gear 3 teeth", unit="count", low=8, high=60, default=14, integer=True),
        "module_in": dict(label="Module (pitch diameter per tooth)", unit="in", low=0.05, high=1, default=0.25)}),
}


def catalog() -> dict:
    return dict(notice=NOTICE, models=[dict(id=k, name=v["name"], fields=[dict(id=f, **spec) for f, spec in v["fields"].items()]) for k, v in MODELS.items()])


def check(raw) -> tuple[str, dict]:
    """Return the model id and clean values. A bad value is reported by field, never replaced."""
    if not isinstance(raw, dict) or raw.get("model") not in MODELS:
        error = ValueError("Choose a model: " + ", ".join(MODELS) + ".")
        error.problems = {"model": "Choose one of the listed models."}
        raise error
    model, values, problems = raw["model"], {}, {}
    for key, spec in MODELS[model]["fields"].items():
        text = f"{spec['label']} must be a {'whole ' if spec.get('integer') else ''}number from {spec['low']:g} to {spec['high']:g}{' ' + spec['unit'] if spec['unit'] != 'count' else ''}{', and even' if spec.get('even') else ''}."
        value = raw.get(key)
        try:
            number = float(value) if not isinstance(value, bool) and value not in (None, "") else math.nan
        except (TypeError, ValueError):
            number = math.nan
        if not math.isfinite(number) or not spec["low"] <= number <= spec["high"] or (spec.get("integer") and number != int(number)) or (spec.get("even") and int(number) % 2):
            problems[key] = text
            continue
        values[key] = int(number) if spec.get("integer") else number
    if model == "tower" and "top_ft" in values and "base_ft" in values and values["top_ft"] > values["base_ft"]:
        problems["top_ft"] = "Top width can't be more than the base width."
    if problems:
        error = ValueError("Some parameters need fixing.")
        error.problems = problems
        raise error
    return model, values


def _round(p):
    return [round(c, 4) for c in p]


def truss(span_ft, panels, height_ft, width_ft) -> dict:
    """Two Pratt trusses: verticals at every interior node, and diagonals that slope down toward midspan."""
    n, step, lines, groups = panels, span_ft / panels, [], {}

    def add(group, a, b):
        lines.append(dict(a=_round(a), b=_round(b), group=group))
        groups[group] = groups.get(group, 0) + 1

    for y in (0.0, width_ft):
        bottom = [(i * step, y, 0.0) for i in range(n + 1)]
        top = {i: (i * step, y, height_ft) for i in range(1, n)}
        for i in range(n):
            add("bottom chord", bottom[i], bottom[i + 1])
        for i in range(1, n - 1):
            add("top chord", top[i], top[i + 1])
        for i in range(1, n):
            add("vertical", bottom[i], top[i])
        add("end post", bottom[0], top[1])
        add("end post", bottom[n], top[n - 1])
        for i in range(1, n - 1):  # Panel i sits between nodes i and i+1. Each diagonal runs down toward midspan.
            add("diagonal", top[i], bottom[i + 1]) if i + 1 <= n // 2 else add("diagonal", top[i + 1], bottom[i])
    for i in range(n + 1):
        add("floor beam", (i * step, 0.0, 0.0), (i * step, width_ft, 0.0))
    for i in range(1, n):
        add("top strut", (i * step, 0.0, height_ft), (i * step, width_ft, height_ft))
    return dict(lines=lines, groups=groups, center=[span_ft / 2, width_ft / 2, height_ft / 2], radius=max(span_ft, width_ft, height_ft) * 0.75)


def tower(height_ft, base_ft, top_ft, sections) -> dict:
    """Four legs that taper from base to top, a ring at every level and X bracing on every face of every section."""
    lines, groups = [], {}

    def add(group, a, b):
        lines.append(dict(a=_round(a), b=_round(b), group=group))
        groups[group] = groups.get(group, 0) + 1

    def ring(k):
        h = height_ft * k / sections
        half = (base_ft + (top_ft - base_ft) * k / sections) / 2
        return [(-half, -half, h), (half, -half, h), (half, half, h), (-half, half, h)]

    levels = [ring(k) for k in range(sections + 1)]
    for k, level in enumerate(levels):
        for c in range(4):
            add("horizontal", level[c], level[(c + 1) % 4])
        if k:
            below = levels[k - 1]
            for c in range(4):
                add("leg", below[c], level[c])
                add("brace", below[c], level[(c + 1) % 4])
                add("brace", below[(c + 1) % 4], level[c])
    return dict(lines=lines, groups=groups, center=[0, 0, height_ft / 2], radius=max(height_ft, base_ft) * 0.7)


def _icosahedron():
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    # Turn it so a vertex points straight up, which gives a level base ring at the equator for even frequencies
    norm = math.hypot(*v[0])
    up = [c / norm for c in v[0]]
    axis = (up[1], -up[0], 0.0)
    angle = math.acos(up[2])
    s = math.hypot(*axis)
    kx, ky = axis[0] / s, axis[1] / s

    def rotate(p):
        x, y, z = p
        c, sn = math.cos(angle), math.sin(angle)
        dot = kx * x + ky * y
        cross = (ky * z, -kx * z, kx * y - ky * x)
        return tuple(p[i] * c + cross[i] * sn + (kx, ky, 0)[i] * dot * (1 - c) for i in range(3))
    return [rotate(p) for p in v], f


def dome(radius_ft, frequency) -> dict:
    """Subdivide each icosahedron face into frequency² triangles, push the points onto the sphere and keep the upper half."""
    verts, faces = _icosahedron()
    points, edges = {}, set()

    def point(p):
        n = math.hypot(*p)
        q = tuple(round(c / n * radius_ft, 6) for c in p)
        return points.setdefault(q, q)

    for a, b, c in faces:
        A, B, C = verts[a], verts[b], verts[c]
        grid = {}
        for i in range(frequency + 1):
            for j in range(frequency + 1 - i):
                k = frequency - i - j
                grid[(i, j)] = point(tuple((A[d] * i + B[d] * j + C[d] * k) / frequency for d in range(3)))
        for i in range(frequency + 1):
            for j in range(frequency + 1 - i):
                for di, dj in ((1, 0), (0, 1), (-1, 1)):
                    q = (i + di, j + dj)
                    if q in grid:
                        edges.add(tuple(sorted((grid[(i, j)], grid[q]))))
    floor = -1e-6 * radius_ft
    kept = [e for e in edges if e[0][2] >= floor and e[1][2] >= floor]
    lengths = sorted({round(math.dist(*e), 2) for e in kept})
    lift = min(min(a[2], b[2]) for a, b in kept)  # Odd frequencies have no ring at the equator, so the dome is set down on its lowest nodes
    lines = [dict(a=_round((a[0], a[1], a[2] - lift)), b=_round((b[0], b[1], b[2] - lift)), group="strut") for a, b in kept]
    note = "" if lift < 1e-6 * radius_ft else f"At odd frequencies the base isn't level, so the dome is set down {lift:.2f} ft onto its lowest nodes."
    return dict(lines=lines, groups={"strut": len(lines)}, strut_lengths_ft=lengths, base_note=note, center=[0, 0, radius_ft / 3], radius=radius_ft * 1.3)


def gear_outline(teeth: int, module: float) -> list[list[float]]:
    """A simplified tooth outline around the origin: straight-sided teeth, not an involute profile."""
    r_pitch = teeth * module / 2
    r_out, r_root = r_pitch + module, r_pitch - 1.25 * module
    pitch = 2 * math.pi / teeth
    pts = []
    for k in range(teeth):
        c = k * pitch
        for angle, r in ((c - pitch * 0.5, r_root), (c - pitch * 0.3, r_root), (c - pitch * 0.17, r_out), (c + pitch * 0.17, r_out), (c + pitch * 0.3, r_root)):
            pts.append([round(r * math.cos(angle), 4), round(r * math.sin(angle), 4)])
    return pts


def gears(teeth_1, teeth_2, teeth_3, module_in) -> dict:
    """Three meshing spur gears in a row. Each gear's start angle puts a tooth into its neighbor's gap, and
    each one turns opposite its neighbor at the inverse of their tooth ratio."""
    counts = [teeth_1, teeth_2, teeth_3]
    out, x, phase, speed = [], 0.0, 0.0, 1.0
    for i, n in enumerate(counts):
        r = n * module_in / 2
        if i:
            prev_n, prev_r, prev_phase = counts[i - 1], counts[i - 1] * module_in / 2, out[-1]["phase"]
            x += prev_r + r
            prev_pitch, pitch = 2 * math.pi / prev_n, 2 * math.pi / n
            s_prev = prev_r * (prev_phase % prev_pitch)  # Arc from the contact point to the nearest tooth of the previous gear
            phase = math.pi - s_prev / r - pitch / 2
            speed = -speed * prev_n / n
        out.append(dict(teeth=n, center=[round(x, 4), 0.0], pitch_radius=round(r, 4), phase=phase, speed=speed, outline=gear_outline(n, module_in)))
    ratio = counts[0] / counts[-1]
    return dict(gears=out, lines=[], groups={"gear": 3}, ratio=f"Gear 3 turns {abs(ratio):.3g} times for each turn of gear 1, in the same direction as gear 1.",
                profile_note="Teeth are simplified straight-sided shapes, not involute profiles, so this shows meshing and ratios only.",
                center=[x / 2, 0, 0], radius=(x / 2 + max(counts) * module_in / 2 + 2 * module_in) * 1.15)


BUILDERS = {"truss": truss, "tower": tower, "dome": dome, "gears": gears}


def build(raw) -> dict:
    model, values = check(raw)
    geometry = BUILDERS[model](**values)
    members = sum(geometry["groups"].values())
    return dict(model=model, name=MODELS[model]["name"], notice=NOTICE, values=values, members=members, **geometry)
