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


def run_planning(evidence, rates=None) -> dict | None:
    ramps = checked_ramps(evidence)
    if not ramps:
        return None
    rates = load_rates() if rates is None else rates
    takeoff = build_takeoff(build_parts(ramps))
    basis = planning_basis(evidence, ramps, takeoff)
    return dict(concept_label="Concept only, built from surveyed dimensions, with height exaggerated", scene=build_scene(ramps, assumptions()["curb_extra_length_ft"]["value"]), takeoff=takeoff,
                cost=build_cost(takeoff, rates), crew=build_crew(takeoff, rates), equipment=build_equipment(takeoff),
                safety_questions=build_questions(), basis=basis, revision=basis["revision"])
