"""Convert NYC permit locations to longitude and latitude. Permits use New York Long Island State Plane, in US feet (EPSG:2263)."""
import math
import re

_A, _F = 6378137.0, 1 / 298.257222101
_E = math.sqrt(_F * (2 - _F))
_LAT1, _LAT2, _LAT0, _LON0 = map(math.radians, (40 + 2 / 3, 41 + 1 / 30, 40 + 1 / 6, -74.0))
_FEET = 1200 / 3937
_EAST = 300000.0


def _m(lat):
    return math.cos(lat) / math.sqrt(1 - (_E * math.sin(lat)) ** 2)


def _t(lat):
    s = _E * math.sin(lat)
    return math.tan(math.pi / 4 - lat / 2) / ((1 - s) / (1 + s)) ** (_E / 2)


_N = (math.log(_m(_LAT1)) - math.log(_m(_LAT2))) / (math.log(_t(_LAT1)) - math.log(_t(_LAT2)))
_C = _m(_LAT1) / (_N * _t(_LAT1) ** _N)
_R0 = _A * _C * _t(_LAT0) ** _N


def state_plane_to_lonlat(x_ft: float, y_ft: float) -> tuple[float, float]:
    x, y = x_ft * _FEET - _EAST, _R0 - y_ft * _FEET
    r = math.copysign(math.hypot(x, y), _N)
    t = (r / (_A * _C)) ** (1 / _N)
    lat = math.pi / 2 - 2 * math.atan(t)
    for _ in range(8):
        s = _E * math.sin(lat)
        lat = math.pi / 2 - 2 * math.atan(t * ((1 - s) / (1 + s)) ** (_E / 2))
    return math.degrees(math.atan2(x, y) / _N + _LON0), math.degrees(lat)


def permit_point(permit: dict):
    """Return a permit's longitude and latitude, or None when it has no readable point."""
    found = re.fullmatch(r"\s*POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)\s*", str(permit.get("wkt") or ""))
    return state_plane_to_lonlat(float(found.group(1)), float(found.group(2))) if found else None


def offset_m(lon: float, lat: float, from_lon: float, from_lat: float) -> tuple[float, float]:
    """Return meters east and north of the second point."""
    return (lon - from_lon) * math.cos(math.radians(from_lat)) * 111320, (lat - from_lat) * 110540
