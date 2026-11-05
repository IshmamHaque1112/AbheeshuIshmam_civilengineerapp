"""Simple concept parts built from checked dimensions. Not a structural design."""
import yaml
from .models import EvidenceItem
from .paths import DATA


def assumptions() -> dict:
    return yaml.safe_load((DATA / "kit_assumptions.yaml").read_text(encoding="utf-8"))


def _feet(item: EvidenceItem) -> float:
    return float(item.value) / 12 if item.unit == "in" else float(item.value)


def checked_ramps(evidence: list[EvidenceItem]) -> list[dict]:
    """Return ramp dimensions only if each one is measured, current and has a documented unit."""
    ramps: dict[str, dict] = {}
    for e in evidence:
        if e.ramp_id:
            ramps.setdefault(e.ramp_id, {})[e.field] = e
    out = []
    for ramp_id, f in ramps.items():
        needed = ["ramp_width", "ramp_length", "lnd_width", "lnd_length", "ramp_running_slope_total"]
        if not all(k in f and f[k].label == "measured" and f[k].unit_documented for k in needed):
            return []
        out.append(dict(ramp_id=ramp_id, width_ft=_feet(f["ramp_width"]), length_ft=_feet(f["ramp_length"]),
                        landing_width_ft=_feet(f["lnd_width"]), landing_length_ft=_feet(f["lnd_length"]),
                        slope_pct=abs(float(f["ramp_running_slope_total"].value))))
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
