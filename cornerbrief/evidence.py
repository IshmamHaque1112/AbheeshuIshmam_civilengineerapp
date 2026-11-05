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
    ids = {r.get("cornerid") for r in corner.get("locations", [])}
    dates = [parse_date(r.get("construc_1")) for r in corner.get("progress", []) if r.get("cornerid") in ids]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def is_stale(survey, built) -> bool:
    survey_date, built_date = parse_date(survey), built if isinstance(built, date) else parse_date(built)
    return bool(survey_date and built_date and built_date > survey_date)


def currency_problem(corner: dict, row: dict) -> str:
    """Return why a measurement can't be confirmed as current. A blank result means the dates allow a comparison."""
    if not parse_date(row.get("geocyclora")):
        return "The survey date is missing or unreadable."
    matches = [r for r in corner.get("progress", []) if r.get("cornerid") == row.get("cornerid")]
    if not matches:
        return "No Program Progress record matches this corner."
    for r in matches:
        if not str(r.get("construc_2") or "").strip():
            return "The Program Progress record has no status."
        if "Constructed" in str(r.get("construc_2")) and not parse_date(r.get("construc_1")):
            return "The corner is listed as constructed, but its completion date is missing or unreadable."
        if str(r.get("construc_1") or "").strip() and not parse_date(r.get("construc_1")):
            return "The Program Progress completion date is unreadable."
    return ""


def join_report(corner: dict) -> list[str]:
    ids = {r.get("cornerid") for r in corner.get("locations", [])}
    notes = []
    if not ids:
        notes.append("No ramp measurements were found for this corner.")
    names = {str(r.get(f)).strip().upper() for r in corner.get("locations", []) for f in ("stname1", "stname2") if r.get(f)}
    program_names = {str(r.get(f)).strip().upper() for r in corner.get("progress", []) for f in ("street_nam", "street_n_1") if r.get(f)}
    if names and program_names and names != program_names:
        notes.append(f"Confirm these records describe the same corner. Ramp records name {', '.join(sorted(names))}; Program Progress names {', '.join(sorted(program_names))}.")
    if None in ids:
        notes.append("A ramp record has no corner ID, so it did not match a corner.")
        ids = ids - {None}
    if not corner.get("progress"):
        notes.append("No Program Progress record joined to this corner.")
    else:
        unmatched = {r.get("cornerid") for r in corner["progress"]} - ids
        if ids and unmatched:
            notes.append(f"Program Progress corner IDs did not match: {sorted(unmatched, key=str)}.")
    for row in corner.get("complaints", []):
        if ids and row.get("cmt_corner_id") not in ids:
            notes.append(f"Complaint {row.get('complaint_id')} did not match this corner.")
    return notes


FIELD_NAMES = {"ramp_running_slope_total": "running slope", "ramp_cross_slope": "ramp cross slope", "ramp_width": "ramp width", "ramp_length": "ramp length",
               "lnd_width": "landing width", "lnd_length": "landing length", "lnd_cross_slope": "landing cross slope", "curb_reveal": "lip height",
               "gutter_slope": "gutter slope", "counter_slope": "roadway slope", "ramp_right_flare": "right flare", "ramp_left_flare": "left flare", "ramp_rise": "ramp rise",
               "sidewalk_width": "sidewalk width", "legal_grade": "legal grade", "ramp_type": "ramp type", "sidewalk_transverse_slope": "sidewalk slope",
               "road_control": "road owner", "geocyclora": "survey date"}


def input_name(field: str, ramp_id=None) -> str:
    """Name an input the way an engineer would read it."""
    name = FIELD_NAMES.get(field, field)
    return f"Ramp {ramp_id} {name}" if ramp_id else name[0].upper() + name[1:]


def _on_site(item: EvidenceItem, entry: dict, built) -> EvidenceItem:
    """Replace a record with what a person measured. A measurement from before the latest construction is still stale."""
    stale = is_stale(entry["date"], built)
    return item.model_copy(update=dict(value=entry["value"], unit=entry["unit"], unit_documented=True, on_site=True, photo=entry.get("photo"),
                                       label="stale" if stale else "measured", source=f"Measured on site by {entry['by']}", date=entry["date"],
                                       reason=f"Measured on site {entry['date']}, but construction finished {built}." if stale else "Measured on site."))


def build_evidence(corner: dict, dictionary: dict, field: list[dict] | None = None) -> list[EvidenceItem]:
    entries = {e["key"]: e for e in field or []}
    placeholders = {float(x) for x in dictionary["placeholder_values"]}
    built = latest_construction(corner)
    items = []
    rows = corner.get("locations", [])
    for row in rows:
        ramp = str(row.get("rampid"))
        survey = str(row.get("geocyclora", ""))[:10] or None
        stale = is_stale(survey, built)
        uncertain = currency_problem(corner, row)
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
            elif uncertain:
                value, label, reason = number, "assumed", f"Unknown whether this is current. {uncertain}"
            elif stale:
                value, label, reason = number, "stale", f"Surveyed {survey}, but construction finished {built}."
            else:
                value = number
            item = EvidenceItem(key=f"{ramp}:{field}", ramp_id=ramp, field=field, value=value,
                                unit=spec["unit"], unit_documented=spec["unit_status"] == "documented",
                                label=label, source=f"Pedestrian Ramp Locations, ramp {ramp}", date=survey,
                                reason=reason)
            items.append(_on_site(item, entries[item.key], built) if item.key in entries else item)
    for row in rows:
        ramp = str(row.get("rampid"))
        fields = {e.field: e for e in items if e.ramp_id == ramp}
        length, slope = fields.get("ramp_length"), fields.get("ramp_running_slope_total")
        if length and slope and length.label == slope.label == "measured" and length.unit == "ft":
            rise = abs(float(length.value)) * 12 * abs(float(slope.value)) / 100
            items.append(EvidenceItem(key=f"{ramp}:ramp_rise", ramp_id=ramp, field="ramp_rise", value=round(rise, 2), unit="in",
                                      unit_documented=length.unit_documented and slope.unit_documented, label="measured",
                                      source=f"Calculated from ramp {ramp}'s length and running slope", date=length.date,
                                      reason="Calculated, not directly measured."))
    for field, why in NOT_IN_DATASETS.items():
        item = EvidenceItem(key=f"corner:{field}", field=field, label="missing", source="Not in the three NYC datasets", reason=why)
        items.append(_on_site(item, entries[item.key], built) if item.key in entries else item)
    if "corner:road_control" in entries or corner.get("context", {}).get("road_control") != "city":
        item = EvidenceItem(key="corner:road_control", field="road_control", label="missing",
                            source="Not in the three NYC datasets", reason="The road owner isn't confirmed.")
        items.append(_on_site(item, entries[item.key], built) if item.key in entries else item)
    return items


def record_conflicts(corner: dict) -> list[str]:
    """Find records that disagree. A person has to settle these, because the tool can't tell which record is right."""
    problems = []
    if len({r.get("cornerid") for r in corner.get("locations", [])} - {None}) > 1:
        problems.append("The ramp records come from more than one corner.")
    by_corner: dict = {}
    for row in corner.get("progress", []):
        by_corner.setdefault(row.get("cornerid"), []).append(row)
    for corner_id, rows in by_corner.items():
        if len({(r.get("construc_2"), r.get("construc_1")) for r in rows}) > 1:
            problems.append(f"Program Progress records disagree for corner {corner_id}.")
    by_ramp: dict = {}
    for row in corner.get("locations", []):
        by_ramp.setdefault(row.get("rampid"), []).append(row)
    for ramp, rows in by_ramp.items():
        differs = [f for f in CHECK_FIELDS + ["geocyclora"] if len({str(r.get(f)) for r in rows}) > 1]
        if differs:
            problems.append(f"Ramp {ramp} has records that disagree on: " + ", ".join(FIELD_NAMES.get(f, f) for f in differs) + ".")
    return problems


def data_sufficient(corner: dict, evidence: list[EvidenceItem]) -> tuple[bool, list[str]]:
    problems = []
    if not corner.get("locations"):
        problems.append("No ramp measurements were found.")
    for item in evidence:
        if item.field in REQUIRED_FIELDS and item.label != "measured":
            problems.append(f"{input_name(item.field, item.ramp_id)} is {item.label}. {item.reason}".strip())
    problems += [n for n in join_report(corner) if "did not match" in n] + record_conflicts(corner)
    undocumented = sorted({e.field for e in evidence if e.field in REQUIRED_FIELDS and e.label == "measured" and not e.unit_documented})
    if undocumented:
        problems.append("Measurement units aren't documented for: " + ", ".join(FIELD_NAMES.get(f, f) for f in undocumented) + ".")
    if corner.get("context", {}).get("road_control") != "city":
        problems.append("The road owner isn't confirmed, so the applicable rules are unknown.")
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
