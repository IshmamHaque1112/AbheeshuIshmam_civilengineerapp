"""Clean data, join datasets, detect stale measurements and validate evidence labels. No AI here."""
from datetime import date
from typing import Optional
from .models import EvidenceItem, RecordsOutput

REQUIRED_FIELDS = ["ramp_running_slope_total", "ramp_cross_slope", "ramp_width", "ramp_length",
                   "lnd_width", "lnd_length", "lnd_cross_slope", "curb_reveal"]
CHECK_FIELDS = REQUIRED_FIELDS + ["gutter_slope", "counter_slope", "ramp_right_flare", "ramp_left_flare"]
NOT_IN_DATASETS = {
    "sidewalk_width": "Measure the sidewalk width at the corner.",
    "legal_grade": "Find the legal grade on the Borough President's section map.",
    "ramp_type": "Record the existing ramp type.",
    "sidewalk_transverse_slope": "Measure the sidewalk's slope toward the curb.",
}


def parse_date(value) -> Optional[date]:
    if not value:
        return None
    text = str(value)[:10].replace("/", "-")
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def latest_construction(corner: dict) -> Optional[date]:
    dates = [parse_date(r.get("construc_1")) for r in corner.get("progress", [])]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def is_stale(survey, built) -> bool:
    survey_date, built_date = parse_date(survey), built if isinstance(built, date) else parse_date(built)
    return bool(survey_date and built_date and built_date > survey_date)


def join_report(corner: dict) -> list[str]:
    ids = {r.get("cornerid") for r in corner.get("locations", [])}
    notes = []
    if not ids:
        notes.append("No ramp measurements were found for this corner.")
    if not corner.get("progress"):
        notes.append("No Program Progress record joined to this corner.")
    else:
        unmatched = {r.get("cornerid") for r in corner["progress"]} - ids
        if ids and unmatched:
            notes.append(f"Program Progress corner IDs did not match: {sorted(unmatched)}.")
    for row in corner.get("complaints", []):
        if ids and row.get("cmt_corner_id") not in ids:
            notes.append(f"Complaint {row.get('complaint_id')} did not match this corner.")
    return notes


def build_evidence(corner: dict, dictionary: dict) -> list[EvidenceItem]:
    placeholders = {float(x) for x in dictionary["placeholder_values"]}
    built = latest_construction(corner)
    items = []
    rows = corner.get("locations", [])
    for row in rows:
        ramp = str(row.get("rampid"))
        survey = str(row.get("geocyclora", ""))[:10] or None
        stale = is_stale(survey, built)
        for field in CHECK_FIELDS:
            spec = dictionary["fields"][field]
            raw = row.get(field)
            value, label, reason = raw, "measured", ""
            number = None
            try:
                number = float(raw)
            except (TypeError, ValueError):
                pass
            low, high = spec["plausible"]
            if number is None:
                value, label, reason = None, "missing", "No value in the record."
            elif number in placeholders:
                value, label, reason = None, "missing", f"{raw} is a placeholder value."
            elif not low <= abs(number) <= high:
                value, label, reason = None, "missing", f"{raw} is outside the plausible range."
            elif stale:
                value, label, reason = number, "stale", f"Surveyed {survey}, but construction finished {built}."
            else:
                value = number
            items.append(EvidenceItem(key=f"{ramp}:{field}", ramp_id=ramp, field=field, value=value,
                                      unit=spec["unit"], unit_documented=spec["unit_status"] == "documented",
                                      label=label, source=f"Pedestrian Ramp Locations, ramp {ramp}", date=survey,
                                      reason=reason))
    for row in rows:
        ramp = str(row.get("rampid"))
        fields = {e.field: e for e in items if e.ramp_id == ramp}
        length, slope = fields.get("ramp_length"), fields.get("ramp_running_slope_total")
        if length and slope and length.label == slope.label == "measured" and length.unit == "ft":
            rise = abs(float(length.value)) * 12 * abs(float(slope.value)) / 100
            items.append(EvidenceItem(key=f"{ramp}:ramp_rise", ramp_id=ramp, field="ramp_rise", value=round(rise, 2), unit="in",
                                      unit_documented=length.unit_documented and slope.unit_documented, label="measured",
                                      source=f"Calculated from ramp {ramp}'s surveyed length and running slope", date=length.date))
    for field, why in NOT_IN_DATASETS.items():
        items.append(EvidenceItem(key=f"corner:{field}", field=field, label="missing",
                                  source="Not in the three NYC datasets", reason=why))
    if corner.get("context", {}).get("road_control") == "not_recorded":
        items.append(EvidenceItem(key="corner:road_control", field="road_control", value="city", label="assumed",
                                  source="Not in the three NYC datasets",
                                  reason="Assumed to be a city street until ownership is confirmed."))
    return items


def data_sufficient(corner: dict, evidence: list[EvidenceItem]) -> tuple[bool, list[str]]:
    problems = []
    if not corner.get("locations"):
        problems.append("No ramp measurements were found.")
    for item in evidence:
        if item.field in REQUIRED_FIELDS and item.label != "measured":
            problems.append(f"{item.key} is {item.label}. {item.reason}".strip())
    return (not problems, problems)


def validate_labels(output: RecordsOutput, evidence: list[EvidenceItem]) -> list[str]:
    """Python's labels win. Returns rejections when the agent's label disagrees."""
    truth = {e.key: e for e in evidence}
    rejected = []
    for item in output.labels:
        if item.key not in truth:
            rejected.append(f"{item.key}: this evidence does not exist.")
        elif item.label != truth[item.key].label:
            rejected.append(f"{item.key}: the agent said {item.label}, but the record shows {truth[item.key].label}.")
    return rejected
