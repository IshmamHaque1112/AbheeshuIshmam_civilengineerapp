"""Labor hours by trade and an ordered work sequence. Not a contract schedule."""
from datetime import date, timedelta
from .takeoff import qty

LINES = [("slab_area", "crew_cement_mason"), ("slab_area", "crew_laborer_slab"), ("curb_length", "crew_laborer_curb"), ("curb_length", "crew_mason_curb")]
SEQUENCE = ["Set up pedestrian and traffic control", "Remove the existing surface and curb", "Prepare the base and check utilities",
            "Set forms and curb", "Place the ramp and landing slabs", "Install the detectable warning surface", "Field-check the slopes and dimensions", "Restore the area and remove controls"]


SAMPLE_REASON = "Unknown. Hours need the company's own production history, and the crew rates here are placeholder samples, so no hours are calculated."


def build_crew(takeoff: dict, rates: dict, today: date | None = None, allow_sample: bool = False) -> dict:
    """Labor hours from crew rates. Placeholder sample rates give no hours unless a caller asks for them, as the
    rate tests do (roadmap M2.4: nothing is filled in from generic trade data)."""
    today = today or date.today()
    hours: dict[str, float] = {}
    unknown = []
    sample = False
    out_of_date = False
    for item_id, rate_id in LINES:
        rate = rates.get(rate_id)
        if rate is None:
            unknown.append(rate_id)
            continue
        sample = sample or rate["status"] == "sample"
        out_of_date = out_of_date or date.fromisoformat(str(rate["source_date"])) < today - timedelta(days=365)
        hours[rate["trade"]] = hours.get(rate["trade"], 0) + qty(takeoff, item_id) * rate["value"]
    blocked = bool(unknown) or (sample and not allow_sample)
    rows = [] if blocked else [{"trade": t, "hours": round(h, 1)} for t, h in sorted(hours.items())]
    reason = "Unknown, because a crew rate is missing." if unknown else SAMPLE_REASON if blocked else ""
    return dict(hours=rows, result="unknown" if blocked else "calculated", reason=reason, unknown_rates=unknown,
                contains_sample_rates=sample, rates_out_of_date=out_of_date, sequence=SEQUENCE)
