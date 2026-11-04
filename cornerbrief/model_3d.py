"""Turn parts into simple colored surfaces for the browser's lightweight renderer."""
COLORS = {"ramp": "#b9bdb9", "landing": "#d2d4cf", "dws": "#f2c200", "curb": "#7f8785", "side": "#9aa09c", "road": "#4a5154", "walk": "#c7cac5"}


def _box(x0, x1, y0, y1, z0, z1, top, side):
    return [
        {"p": [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], "c": top},
        {"p": [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], "c": side},
        {"p": [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]], "c": side},
        {"p": [[x0, y0, z0], [x0, y1, z0], [x0, y1, z1], [x0, y0, z1]], "c": side},
    ]


def build_scene(ramps: list[dict], curb_extra_ft: float = 4) -> dict:
    faces, cursor, depth = [], 0.0, 0.0
    side = curb_extra_ft / 2
    for r in ramps:
        w, l, lw, ll = r["width_ft"], r["length_ft"], r["landing_width_ft"], r["landing_length_ft"]
        rise = l * r["slope_pct"] / 100
        curb_h = max(rise, 0.1)
        x0, x1 = cursor, cursor + w
        lx0 = cursor + (w - lw) / 2
        lx1 = lx0 + lw
        faces.append({"p": [[x0, 0, 0], [x1, 0, 0], [x1, l, rise], [x0, l, rise]], "c": COLORS["ramp"]})
        dws = min(2, l)
        faces.append({"p": [[x0, 0, 0], [x1, 0, 0], [x1, dws, rise * dws / l], [x0, dws, rise * dws / l]], "c": COLORS["dws"]})
        faces += _box(lx0, lx1, l, l + ll, 0, rise, COLORS["landing"], COLORS["side"])
        faces += _box(x0 - side, x0, -0.5, 0, 0, curb_h, COLORS["curb"], COLORS["curb"])
        faces += _box(x1, x1 + side, -0.5, 0, 0, curb_h, COLORS["curb"], COLORS["curb"])
        depth = max(depth, l + ll)
        cursor = x1 + 6
    span = max(cursor - 6, 1)
    road = {"p": [[-6, -8, -0.01], [span + 6, -8, -0.01], [span + 6, 0, -0.01], [-6, 0, -0.01]], "c": COLORS["road"]}
    walk = {"p": [[-6, 0, -0.005], [span + 6, 0, -0.005], [span + 6, depth + 4, -0.005], [-6, depth + 4, -0.005]], "c": COLORS["walk"]}
    return {"faces": [road, walk] + faces, "center": [span / 2, depth / 3, 0], "radius": max(span, depth) + 8}
