"""Labor hours by trade and an ordered work sequence. Not a contract schedule."""
from .takeoff import qty

LINES = [("slab_area", "crew_cement_mason"), ("slab_area", "crew_laborer_slab"), ("curb_length", "crew_laborer_curb"), ("curb_length", "crew_mason_curb")]
SEQUENCE = ["Set up pedestrian and traffic control", "Remove the existing surface and curb", "Prepare the base and check utilities",
            "Set forms and curb", "Place the ramp and landing slabs", "Install the detectable warning surface", "Field-check the slopes and dimensions", "Restore the area and remove controls"]


def build_crew(takeoff: dict, rates: dict) -> dict:
    hours: dict[str, float] = {}
    unknown = []
    sample = False
    for item_id, rate_id in LINES:
        rate = rates.get(rate_id)
        if rate is None:
            unknown.append(rate_id)
            continue
        sample = sample or rate["status"] == "sample"
        hours[rate["trade"]] = hours.get(rate["trade"], 0) + qty(takeoff, item_id) * rate["value"]
    return dict(hours=[{"trade": t, "hours": round(h, 1)} for t, h in sorted(hours.items())], unknown_rates=unknown,
                contains_sample_rates=sample, sequence=SEQUENCE)
