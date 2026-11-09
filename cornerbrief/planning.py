"""Run all planning modules from one takeoff."""
from .cost import build_cost
from .crew_sequence import build_crew
from .equipment_types import build_equipment
from .model_3d import build_scene
from .parts_kit import assumptions, build_parts, checked_ramps
from .readiness import DIMENSIONS, dimension_rows
from .revision import MODEL_VERSION, revision
from .rules import load_rates
from .safety_questions import build_questions
from .takeoff import build_takeoff
from .work_plan import build_work_plan


def planning_basis(evidence, ramps: list[dict], takeoff: dict) -> dict:
    """Record what the geometry and quantities were built from, and give that basis one revision.

    The inputs are the values the geometry actually used, each with its record, and the assumptions are
    the ones the takeoff actually used. A changed dimension, assumption or model version gives a new revision.
    """
    rows = {(r["ramp_id"], r["input"]): r for r in dimension_rows(evidence)}
    inputs = []
    for ramp in ramps:
        for spec in DIMENSIONS:
            row = rows[(ramp["ramp_id"], spec["input"])]
            inputs.append(dict(ramp_id=ramp["ramp_id"], input=spec["input"], name=row["name"], value=ramp[spec["input"]], unit=row["model_unit"],
                               status=row["status"], recorded_value=row["value"], recorded_unit=row["unit"], source=row["source"], date=row["date"], reason=row["reason"]))
    used = {x["id"]: x["value"] for x in takeoff["assumptions"]}
    return dict(model_version=MODEL_VERSION, revision=revision(MODEL_VERSION, ramps, used), inputs=inputs,
                assumptions=[dict(id=x["id"], value=x["value"], unit=x.get("unit"), status="assumed", reason=x.get("basis", "")) for x in takeoff["assumptions"]])


def cited_dimensions(basis: dict) -> list[dict]:
    """Label each dimension the model used with the record it came from (roadmap M2.1)."""
    out = []
    for x in basis["inputs"]:
        recorded = f"{x['recorded_value']:g} {x['recorded_unit']}" if isinstance(x["recorded_value"], (int, float)) else str(x["recorded_value"])
        shown = f"{round(x['value'], 2):g} {x['unit']}"
        source = x["source"] or "no record"
        out.append(dict(ramp_id=x["ramp_id"], input=x["input"], label=f"{x['name']}: {shown}", recorded=recorded, citation=f"{recorded} from {source}{', ' + str(x['date']) if x['date'] else ''}"))
    return out


SHORT = {spec["input"]: spec["name"] for spec in DIMENSIONS}


def scene_labels(scene: dict, dimensions: list[dict]) -> list[dict]:
    """Put each dimension's value and its record on the model, beside the part it measures (M2.1)."""
    cited = {(d["ramp_id"], d["input"]): d for d in dimensions}
    out = []
    for a in scene.get("anchors", []):
        d = cited.get((a["ramp_id"], a["input"]))
        if d:
            value = d["label"].split(": ", 1)[1]
            out.append(dict(at=a["at"], text=f"{SHORT[a['input']]} {value} · record {d['recorded']}", short=f"{SHORT[a['input']]} {value}",
                            citation=d["citation"]))
    return out


def run_planning(evidence, rates=None) -> dict | None:
    ramps = checked_ramps(evidence)
    if not ramps:
        return None
    rates = load_rates() if rates is None else rates
    takeoff = build_takeoff(build_parts(ramps))
    basis = planning_basis(evidence, ramps, takeoff)
    dimensions = cited_dimensions(basis)
    scene = build_scene(ramps, assumptions()["curb_extra_length_ft"]["value"])
    scene["labels"] = scene_labels(scene, dimensions)
    return dict(concept_label="Concept only, built from surveyed dimensions, with height exaggerated", scene=scene, takeoff=takeoff,
                cost=build_cost(takeoff, rates), crew=build_crew(takeoff, rates), equipment=build_equipment(takeoff),
                safety_questions=build_questions(), basis=basis, revision=basis["revision"],
                dimensions=dimensions, work_plan=build_work_plan(takeoff, basis["revision"]))
