"""Quantities times dated rates. A missing rate returns unknown, never a number."""
from datetime import date, timedelta
from .takeoff import qty
import os

LINES = [("slab_area", "cost_ramp_concrete"), ("dws_area", "cost_dws"), ("curb_length", "cost_curb"), ("removal_area", "cost_removal")]
LABEL = "Class 5 concept estimate, not a bid"
RANGE_NOTE = "The range uses the widest published Class 5 range, -50% to +100%. It is not this tool's tested accuracy."


def build_cost(takeoff: dict, rates: dict, today: date | None = None) -> dict:
    today = today or date.today()
    lines, unknown = [], False
    for item_id, rate_id in LINES:
        rate, quantity = rates.get(rate_id), qty(takeoff, item_id)
        if rate is None:
            unknown = True
            lines.append(dict(item=item_id, quantity=quantity, rate_id=rate_id, amount=None, result="unknown", status="missing rate"))
            continue
        stale = date.fromisoformat(str(rate["source_date"])) < today - timedelta(days=365)
        lines.append(dict(item=rate["item"], quantity=quantity, unit=rate["unit"], rate=rate["value"], rate_id=rate_id,
                          amount=round(quantity * rate["value"]), status=rate["status"], source_date=str(rate["source_date"]), rate_out_of_date=stale))
    base = None if unknown else sum(l["amount"] for l in lines)
    return dict(label=LABEL, range_note=RANGE_NOTE, lines=lines, base=base, low=None if base is None else round(base * 0.5),
                high=None if base is None else round(base * 2), result="unknown" if unknown else "calculated",
                contains_sample_rates=any(l.get("status") == "sample" for l in lines))


def dollars_shown() -> bool:
    return os.environ.get("SHOW_DOLLARS", "false").lower() == "true"


def hide_dollars(cost: dict) -> dict:
    """The city demo shows quantities only, so a placeholder price can't be quoted."""
    lines = [dict(item=l["item"], quantity=l["quantity"], unit=l.get("unit", "")) for l in cost["lines"]]
    return dict(label=cost["label"], lines=lines, hidden=True, note="Dollar figures are hidden for this demo.")
