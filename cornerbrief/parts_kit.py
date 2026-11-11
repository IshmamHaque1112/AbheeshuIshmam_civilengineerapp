"""Simple concept parts built from checked dimensions. Not a structural design."""
import math
import yaml
from .models import EvidenceItem
from .paths import DATA


def assumptions() -> dict:
    return yaml.safe_load((DATA / "kit_assumptions.yaml").read_text(encoding="utf-8"))


def model_dimension(item: EvidenceItem, slope: bool = False) -> float | None:
    """Accept only usable measured values with documented, supported units."""
    units = {"percent": 1.0} if slope else {"in": 1 / 12, "ft": 1.0}
    if item.label != "measured" or not item.unit_documented or item.unit not in units or isinstance(item.value, bool):
        return None
    try:
        value = float(item.value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or abs(value) in (999, 9999) or (not slope and value <= 0):
        return None
    return abs(value) if slope else value * units[item.unit]


def checked_ramps(evidence: list[EvidenceItem]) -> list[dict]:
    """Return ramp dimensions only if each one is measured, current and has a documented unit."""
    ramps: dict[str, dict] = {}
    for e in evidence:
        if e.ramp_id:
            ramps.setdefault(e.ramp_id, {})[e.field] = e
    out = []
    for ramp_id, f in ramps.items():
        needed = ["ramp_width", "ramp_length", "lnd_width", "lnd_length", "ramp_running_slope_total"]
        values = {k: model_dimension(f[k], slope=k == "ramp_running_slope_total") if k in f else None for k in needed}
        if any(value is None for value in values.values()):
            return []
        out.append(dict(ramp_id=ramp_id, width_ft=values["ramp_width"], length_ft=values["ramp_length"],
                        landing_width_ft=values["lnd_width"], landing_length_ft=values["lnd_length"],
                        slope_pct=values["ramp_running_slope_total"]))
    return out


def build_parts(ramps: list[dict]) -> list[dict]:
    a = assumptions()
    thick = a["slab_thickness_in"]["value"] / 12
    dws = a["dws_depth_ft"]["value"]
    extra = a["curb_extra_length_ft"]["value"]
    parts = []
    for r in ramps:
        rid = r["ramp_id"]
        parts += [
            dict(name="Ramp slab", kind="ramp", ramp_id=rid, length_ft=r["length_ft"], width_ft=r["width_ft"], thickness_ft=thick),
            dict(name="Landing slab", kind="landing", ramp_id=rid, length_ft=r["landing_length_ft"], width_ft=r["landing_width_ft"], thickness_ft=thick),
            # A ramp shorter than the assumed depth can only hold that much warning surface, as the 3D model draws it
            dict(name="Detectable warning surface", kind="dws", ramp_id=rid, length_ft=min(dws, r["length_ft"]), width_ft=r["width_ft"], thickness_ft=0),
            dict(name="Curb", kind="curb", ramp_id=rid, length_ft=r["width_ft"] + extra, width_ft=0.5, thickness_ft=0),
        ]
    return parts
