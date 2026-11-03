"""Run all planning modules from one takeoff."""
from .cost import build_cost
from .crew_sequence import build_crew
from .equipment_types import build_equipment
from .model_3d import build_scene
from .parts_kit import build_parts, checked_ramps
from .rules import load_rates
from .safety_questions import build_questions
from .takeoff import build_takeoff


def run_planning(evidence, rates=None) -> dict | None:
    ramps = checked_ramps(evidence)
    if not ramps:
        return None
    rates = load_rates() if rates is None else rates
    takeoff = build_takeoff(build_parts(ramps))
    return dict(concept_label="Concept only, built from surveyed dimensions", scene=build_scene(ramps), takeoff=takeoff,
                cost=build_cost(takeoff, rates), crew=build_crew(takeoff, rates), equipment=build_equipment(takeoff),
                safety_questions=build_questions())
