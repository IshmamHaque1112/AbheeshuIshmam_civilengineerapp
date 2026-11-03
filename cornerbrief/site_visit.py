"""List what to measure or confirm. No AI here."""
from .evidence import NOT_IN_DATASETS
from .models import EvidenceItem

ACTIONS = {
    "ramp_running_slope_total": "Measure the ramp's running slope.",
    "ramp_cross_slope": "Measure the ramp's cross slope.",
    "ramp_width": "Measure the ramp's width.",
    "ramp_length": "Measure the ramp's length.",
    "lnd_width": "Measure the landing's width.",
    "lnd_length": "Measure the landing's length.",
    "lnd_cross_slope": "Measure the landing's cross slope.",
    "curb_reveal": "Measure the lip height at the dropped curb.",
    "gutter_slope": "Measure the gutter slope.",
    "counter_slope": "Measure the roadway slope at the ramp.",
    "ramp_right_flare": "Measure the right flare slope.",
    "ramp_left_flare": "Measure the left flare slope.",
}


def build_list(evidence: list[EvidenceItem], corner: dict) -> list[dict]:
    items, seen = [], set()
    for e in evidence:
        if e.label not in ("missing", "stale"):
            continue
        action = NOT_IN_DATASETS.get(e.field) or ACTIONS.get(e.field)
        if e.label == "stale":
            action = "Re-measure" + action[7:] if action.startswith("Measure ") else f"Re-check: {action}"
        where = f"Ramp {e.ramp_id}" if e.ramp_id else "Corner"
        id_ = (where, e.field)
        if id_ not in seen:
            seen.add(id_)
            items.append({"where": where, "action": action, "why": "This isn't in the three NYC datasets." if e.field in NOT_IN_DATASETS else e.reason})
    for row in corner.get("locations", []):
        for field in ("obstacles_ramp", "obstacles_landing"):
            value = row.get(field)
            if value and value != "None":
                items.append({"where": f"Ramp {row.get('rampid')}", "action": f"Locate and photograph: {value}.", "why": "A recorded obstacle may limit the ramp layout."})
        if row.get("ponding") == "Yes":
            items.append({"where": f"Ramp {row.get('rampid')}", "action": "Check drainage at the base of the ramp.", "why": "The record shows pooling water."})
    if corner.get("context", {}).get("road_control") == "not_recorded":
        items.append({"where": "Corner", "action": "Confirm whether the city or state controls the road.", "why": "State control would change which rules can be used."})
    return items
