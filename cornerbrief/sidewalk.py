"""Estimate paved sidewalk width near a ramp from map shapes. This cross-checks other records and never replaces a measurement."""
import math

RADIUS_M, STEP_M = 15, 1


def max_width_ft(rows: list[dict], lon: float, lat: float):
    """Return the widest circle that fits in the sidewalk shapes within 15 m of the point, in feet."""
    scale = math.cos(math.radians(lat)) * 111320
    rings = []
    for row in rows:
        geometry = row.get("the_geom") if isinstance(row.get("the_geom"), dict) else {}
        for polygon in geometry.get("coordinates") or []:
            rings += [[((x - lon) * scale, (y - lat) * 110540) for x, y in ring] for ring in polygon]
    edges = [(ring[i], ring[i + 1]) for ring in rings for i in range(len(ring) - 1)]
    if not edges:
        return None
    widest = 0.0
    for x in range(-RADIUS_M, RADIUS_M + 1, STEP_M):
        for y in range(-RADIUS_M, RADIUS_M + 1, STEP_M):
            if math.hypot(x, y) <= RADIUS_M and _inside(x, y, edges):
                widest = max(widest, 2 * min(_distance(x, y, a, b) for a, b in edges))
    return round(widest / 0.3048, 1) if widest else None


def _inside(x, y, edges) -> bool:
    crossings = sum(1 for a, b in edges if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0])
    return crossings % 2 == 1


def _distance(x, y, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / length)) if length else 0
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)
