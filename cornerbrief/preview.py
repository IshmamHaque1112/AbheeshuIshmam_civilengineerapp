"""Synthetic 3D exploration. Nothing here is evidence, and nothing here reaches a packet, a label or a plan."""
import math
from .model_3d import build_scene
from .parts_kit import build_parts
from .revision import MODEL_VERSION, revision as make_revision
from .takeoff import build_takeoff

BASIS_VERSION = MODEL_VERSION
NOTICE ="Synthetic exploration: these dimensions were typed in, not measured. This isn't field evidence, a design or a rule check."
FIELDS = {
    "width_ft": dict(label="Ramp width", unit="ft", low=1, high=20, default=5),
    "length_ft": dict(label="Ramp length", unit="ft", low=1, high=30, default=6),
    "landing_width_ft": dict(label="Landing width", unit="ft", low=1, high=20, default=5),
    "landing_length_ft": dict(label="Landing length", unit="ft", low=1, high=20, default=5),
    "slope_pct": dict(label="Running slope", unit="%", low=0, high=15, default=6),
}
ASSUMED = {"slab_thickness_in": "Slab thickness {:g} in", "dws_depth_ft": "Warning surface depth {:g} ft",
           "curb_extra_length_ft": "Extra curb length {:g} ft", "removal_factor": "Removal area factor {:g}×"}
# Inputs a real corner needs that this sandbox doesn't model. They stay unknown, never filled in.
NOT_MODELED = ["Sidewalk width", "Ramp and landing cross slope", "Side flares", "Gutter and roadway slope",
               "Lip height at the gutter", "Legal grade", "Utilities, vaults and catch basins", "Road ownership"]


def defaults() -> dict:
    return dict(notice=NOTICE, fields=[dict(id=k, **v) for k, v in FIELDS.items()])


def check_inputs(raw) -> tuple[dict, dict]:
    """Return clean values and any problems by field. A bad value is reported, never replaced."""
    if not isinstance(raw, dict):
        return {}, {"inputs": "The dimensions must be a set of named values."}
    values, problems = {}, {}
    for key in set(raw) - set(FIELDS):
        problems[str(key)] = "This isn't a dimension the preview uses."
    for key, spec in FIELDS.items():
        text = f"{spec['label']} must be a number from {spec['low']} to {spec['high']} {spec['unit']}."
        value = raw.get(key)
        if isinstance(value, bool) or value in (None, ""):
            problems[key] = text
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            problems[key] = text
            continue
        if not math.isfinite(number) or not spec["low"] <= number <= spec["high"]:
            problems[key] = text
            continue
        values[key] = number
    return values, problems


def _dimensions(v: dict) -> list[dict]:
    """Place each dimension line beside the part it measures, in feet."""
    w, l, lw, ll = v["width_ft"], v["length_ft"], v["landing_width_ft"], v["landing_length_ft"]
    rise = l * v["slope_pct"] / 100
    lx0, lx1 = (w - lw) / 2, (w + lw) / 2
    right = max(w, lx1) + 1.2
    show = lambda number: f"{number:g}"
    return [
        dict(label=f"Ramp width {show(w)} ft", a=[0, -1.4, 0], b=[w, -1.4, 0]),
        dict(label=f"Ramp length {show(l)} ft", a=[right, 0, 0], b=[right, l, 0]),
        dict(label=f"Landing width {show(lw)} ft", a=[lx0, l + ll + 1.2, rise], b=[lx1, l + ll + 1.2, rise]),
        dict(label=f"Landing length {show(ll)} ft", a=[right, l, rise], b=[right, l + ll, rise]),
        dict(label=f"Rise {rise * 12:.1f} in", a=[min(0, lx0) - 1.2, l, 0], b=[min(0, lx0) - 1.2, l, rise]),
    ]


def build_preview(raw) -> dict:
    """Build the model and quantities from one set of inputs. Raises ValueError with problems by field."""
    values, problems = check_inputs(raw)
    if problems:
        error = ValueError("Some dimensions need fixing.")
        error.problems = problems
        raise error
    ramp = dict(ramp_id="synthetic", **values)
    takeoff = build_takeoff(build_parts([ramp]))
    used = {x["id"]: x["value"] for x in takeoff["assumptions"]}
    scene = build_scene([ramp], used["curb_extra_length_ft"])
    width = max(values["width_ft"], values["landing_width_ft"])
    depth = values["length_ft"] + values["landing_length_ft"]
    scene["center"], scene["radius"] = [values["width_ft"] / 2, depth / 2, 0], max(width, depth) + 8
    revision = make_revision(BASIS_VERSION, values, used)
    basis = dict(synthetic=[f"{FIELDS[k]['label']} {values[k]:g} {FIELDS[k]['unit']}" for k in FIELDS],
                 assumed=[ASSUMED.get(x["id"], x["id"].replace("_", " ") + " {:g}").format(x["value"]) for x in takeoff["assumptions"]],
                 unknown=list(NOT_MODELED))
    return dict(input_basis=basis, basis_version=BASIS_VERSION, kind="synthetic exploration", notice=NOTICE, revision=revision, scene=scene, dimensions=_dimensions(values),
                rise_in=round(values["length_ft"] * values["slope_pct"] / 100 * 12, 1),
                inputs=[dict(id=k, label=FIELDS[k]["label"], value=values[k], unit=FIELDS[k]["unit"], provenance="synthetic, typed in") for k in FIELDS],
                quantities=[dict(i, basis="provisional, from synthetic inputs and sample assumptions") for i in takeoff["items"]],
                assumptions=[dict(id=x["id"], value=x["value"], unit=x.get("unit"), note=x.get("basis", "")) for x in takeoff["assumptions"]],
                exclusions=takeoff["exclusions"], review_note=f"Any estimate or schedule based on an earlier revision needs review against revision {revision}.")
