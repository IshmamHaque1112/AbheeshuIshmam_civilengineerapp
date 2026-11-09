"""A draft small-concrete work sequence for review (roadmap M2.2 to M2.4). No AI here.

The steps and their quantities come from the takeoff. Every duration and every resource stays unknown,
because those come from company records, the concrete specification and the agreements that apply,
none of which this tool has. Nothing is filled in from generic trade data.
"""
from .takeoff import qty

LABEL = "Proposed draft sequence for review. Every duration and resource is unknown until it comes from company records or the specification. This isn't a schedule."

STEPS = [
    dict(id="sawcut", name="Sawcut the existing surface and curb", quantities=["removal_area", "curb_length"], equipment=["Concrete saw"]),
    dict(id="demolition", name="Remove and haul the existing surface and curb", quantities=["removal_area"], equipment=["Compact excavator or skid steer", "Dump truck"]),
    dict(id="forming", name="Prepare the base and set forms", quantities=["slab_area", "curb_length"], equipment=["Plate compactor"]),
    dict(id="pour", name="Place the ramp, landing and curb concrete", quantities=["concrete_volume", "slab_area"], equipment=["Concrete delivery truck"]),
    dict(id="cure", name="Cure the concrete", quantities=[], equipment=[], duration_source="the concrete mix design and specification"),
    dict(id="warning_surface", name="Install the detectable warning surface", quantities=["dws_area"], equipment=[]),
    dict(id="restoration", name="Restore the surrounding area and reopen the path", quantities=[], equipment=[], note="The surrounding restoration isn't modeled, so it has no quantity."),
]

# What a real sequence needs and this tool doesn't have. Listed, never filled in.
MISSING_INPUTS = [
    "People available and their trade qualifications, from company records",
    "Equipment available, from company records",
    "Production rates for each step, from the company's own history",
    "Concrete mix and cure time, from the specification",
    "Delivery lead times for concrete and the warning surface",
    "The union or project agreement and work rules that apply to this job",
    "Permitted work hours and street closure windows",
    "Utility markouts and any utility coordination",
]


def build_work_plan(takeoff: dict, revision: str) -> dict:
    """Build the draft from one takeoff and record the revision it came from."""
    items = {i["id"]: i for i in takeoff["items"]}
    steps = []
    for number, spec in enumerate(STEPS, 1):
        quantities = [dict(label=items[q]["label"], qty=qty(takeoff, q), unit=items[q]["unit"]) for q in spec["quantities"] if q in items]
        steps.append(dict(number=number, id=spec["id"], name=spec["name"], after=STEPS[number - 2]["id"] if number > 1 else None, quantities=quantities,
                          equipment_types=list(spec["equipment"]), people="unknown", equipment_availability="unknown", duration="unknown",
                          duration_source=spec.get("duration_source", "company production history"), note=spec.get("note", "")))
    return dict(status="draft", label=LABEL, built_from_revision=revision, steps=steps, missing_inputs=list(MISSING_INPUTS))


def plan_status(plan: dict | None, current_revision: str | None) -> dict:
    """Say whether a saved draft still matches the current geometry and quantities."""
    if not plan:
        return dict(state="none", message="No draft has been built.")
    if plan.get("built_from_revision") == current_revision:
        return dict(state="current", message=f"Built from the current revision, {current_revision}.")
    return dict(state="needs recalculation",
                message=f"Needs recalculation: this draft was built from revision {plan.get('built_from_revision')}, and the current revision is {current_revision}. Rebuild it before use.")
