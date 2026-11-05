"""List what to measure or confirm. No AI here."""
from .evidence import NOT_IN_DATASETS, parse_date, permits_after
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


WHY = {"sidewalk_width": "H-1011 General Notes 27 and 28 use the pedestrian path width to choose the ramp case."}


def build_list(evidence: list[EvidenceItem], corner: dict) -> list[dict]:
    items, seen = [], set()
    for e in evidence:
        if e.label not in ("missing", "stale", "assumed") or e.field == "road_control":
            continue
        action = NOT_IN_DATASETS.get(e.field) or ACTIONS.get(e.field)
        if e.label == "assumed":
            action = "Confirm this is current. " + action
        elif e.label == "stale":
            action = "Re-measure" + action[7:] if action.startswith("Measure ") else f"Re-check: {action}"
        where = f"Ramp {e.ramp_id}" if e.ramp_id else "Corner"
        id_ = (where, e.field)
        if id_ not in seen:
            seen.add(id_)
            items.append({"where": where, "action": action, "why": WHY.get(e.field, "This isn't in the NYC datasets used here.") if e.field in NOT_IN_DATASETS and e.label != "assumed" else e.reason})
    for row in corner.get("locations", []):
        for field in ("obstacles_ramp", "obstacles_landing"):
            value = row.get(field)
            if value and value != "None":
                items.append({"where": f"Ramp {row.get('rampid')}", "action": f"Locate and photograph: {value}.", "why": "A recorded obstacle may limit the ramp layout."})
        if row.get("ponding") == "Yes":
            items.append({"where": f"Ramp {row.get('rampid')}", "action": "Check drainage at the base of the ramp.", "why": "The record shows pooling water."})
    surveys = sorted(str(r.get("geocyclora"))[:10] for r in corner.get("locations", []) if parse_date(r.get("geocyclora")))
    later = permits_after(corner, surveys[0]) if surveys else []
    if later:
        kinds = ", ".join(sorted({str(p.get("permittypedesc") or "unlisted type").strip().lower() for p in later})[:6])
        items.append({"where": "Corner", "action": "Look for work done under the block's street permits since the survey.",
                      "why": f"{len(later)} permit{'' if len(later) == 1 else 's'} {'has' if len(later) == 1 else 'have'} work ending after the survey, including: {kinds}."})
    if any(e.unit is not None and e.label == "measured" and not e.unit_documented for e in evidence):
        items.append({"where": "Dataset", "action": "Confirm the measurement units in the ramp dataset's documentation.", "why": "Limit checks stay unknown until the units are documented."})
    if corner.get("context", {}).get("road_control_basis") == "assumed":
        items.append({"where": "Corner", "action": "Confirm that the city controls the road.", "why": "It's assumed by default, and state control would change which rules can be used."})
    elif corner.get("context", {}).get("road_control") != "city":
        items.append({"where": "Corner", "action": "Confirm whether the city or state controls the road.", "why": "State control would change which rules can be used."})
    return items
