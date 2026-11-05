"""Clean data, join datasets, detect stale measurements and validate evidence labels. No AI here."""
import math
import re
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


def permits_after(corner: dict, survey) -> list[dict]:
    """Return permits whose work window ends after the survey. A permit shows work was allowed, not that it happened."""
    surveyed = parse_date(survey)
    if not surveyed:
        return []
    return [p for p in corner.get("permits") or [] if (parse_date(p.get("issuedworkenddate")) or date.min) > surveyed]


def ramp_permits_after(corner: dict, survey) -> list[dict]:
    return [p for p in permits_after(corner, survey) if RAMP_PERMIT.search(str(p.get("permittypedesc") or "").upper())]


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def _plain_street(name) -> str:
    words = [SUFFIXES.get(w, w) for w in str(name or "").upper().split()]
    return " ".join(words)


def _road_records(corner: dict) -> tuple[set, list]:
    streets = {_plain_street(r.get(f)) for r in corner.get("locations", []) for f in ("stname1", "stname2") if r.get(f)}
    found = [r for r in corner.get("road_inventory") or [] if _plain_street(r.get("Roadway_Name")) in streets]
    return streets, found


def road_owner(corner: dict):
    """Read the owner from NYSDOT's inventory. A street it doesn't list is assumed city-owned, as the team chose."""
    if corner.get("road_inventory") is None:
        return None
    streets, found = _road_records(corner)
    codes = [str(r.get(f) or "") for r in found for f in ("Owning_Jurisdiction", "Maintenance_Jurisdiction")]
    if any(c.startswith("01-") for c in codes):
        return "state"
    return "city" if streets and all(c.startswith("04-") for c in codes) else None


def road_owner_assumed(corner: dict) -> bool:
    streets, found = _road_records(corner)
    return road_owner(corner) == "city" and streets != {_plain_street(r.get("Roadway_Name")) for r in found}


def approach_width_in(corner: dict):
    """Return DOT's narrowest believable sidewalk approach width. 999 is a placeholder, and values outside 2 to 50 ft are ignored."""
    widths = [float(w) for d in corner.get("dot_survey") or [] for w in (d.get("SDW_APP_WIDTH1"), d.get("SDW_APP_WIDTH2")) if isinstance(w, (int, float)) and 24 <= w <= 600]
    return min(widths) if widths else None


def _sidewalk_item(corner: dict):
    width = approach_width_in(corner)
    if width is None:
        return None
    estimate = (corner.get("sidewalk_map") or {}).get("max_width_ft")
    check = f" NYC's Planimetric map shows up to about {estimate} ft of paved sidewalk nearby." if estimate else ""
    return EvidenceItem(key="corner:sidewalk_width", field="sidewalk_width", value=round(width / 12, 2), unit="ft", label="assumed", source="NYC DOT survey map",
                        reason=f"DOT's record gives {width:g} with no documented unit. It's read as inches because DOT's other lengths use inches.{check} Confirm this on site.")


def _inventory_notes(corner: dict) -> list[str]:
    rows = corner.get("road_inventory")
    if rows is None:
        return []
    names = {(str(r.get("Roadway_Name") or "Unnamed").strip(), str(r.get("Owning_Jurisdiction") or "not listed").split("-", 1)[-1], str(r.get("Maintenance_Jurisdiction") or "not listed").split("-", 1)[-1]) for r in rows}
    shown = "; ".join(f"{n}, owned by {o} and maintained by {m}" for n, o, m in sorted(names)) or "no road"
    listed = {_plain_street(r.get("Roadway_Name")) for r in rows}
    absent = sorted({str(r.get(f)).strip() for r in corner.get("locations", []) for f in ("stname1", "stname2") if r.get(f) and _plain_street(r.get(f)) not in listed})
    notes = [f"NYSDOT's Roadway Inventory shows within 100 m: {shown}."]
    if absent and road_owner_assumed(corner):
        notes.append(f"It doesn't list {', '.join(absent)}, so those streets are assumed city-owned by default. Confirm this.")
    elif absent:
        notes.append(f"It doesn't list {', '.join(absent)}.")
    return notes


def _distance_note(corner: dict) -> list[str]:
    def point(rows):
        for row in rows:
            geom = row.get("the_geom")
            if isinstance(geom, dict) and len(geom.get("coordinates") or []) == 2:
                return geom["coordinates"]
        return None
    ramp, program = point(corner.get("locations", [])), point(corner.get("progress", []))
    if not ramp or not program:
        return []
    meters = math.hypot((ramp[0] - program[0]) * math.cos(math.radians(ramp[1])) * 111320, (ramp[1] - program[1]) * 110540)
    return [f"The Program Progress point for this corner is {meters:.0f} m from the first ramp."]


def _column_notes(corner: dict) -> list[str]:
    rows = {str(r.get("rampid")): r for r in corner.get("locations", [])}
    notes = []
    for dot in corner.get("dot_survey") or []:
        row = rows.get(str(dot.get("RAMPID")))
        try:
            different = row and abs(float(row["ramp_left_flare"]) - float(dot["RAMP_LENGTH"])) > 0.051
        except (KeyError, TypeError, ValueError):
            different = False
        if different:
            notes.append(f"Check ramp {dot.get('RAMPID')}'s length. NYC DOT's survey map gives {dot.get('RAMP_LENGTH')} in, and the corrected dataset column gives {row.get('ramp_left_flare')} in.")
    return notes


def survey_lines(corner: dict) -> list[str]:
    """Quote NYC DOT's own survey record. It stays out of the agents' inputs and is never this tool's result."""
    lines = []
    for dot in corner.get("dot_survey") or []:
        widths = [str(w) for w in (dot.get("SDW_APP_WIDTH1"), dot.get("SDW_APP_WIDTH2")) if w not in (None, 999, 999.0)]
        parts = [f"status {dot.get('COMPLIANCY_STATUS') or 'not listed'}", f"type {dot.get('RAMP_TYPE') or 'not listed'}", f"defective curb: {dot.get('DEFECTIVE_CURB') or 'not listed'}",
                 f"defective sidewalk: {dot.get('DEFECTIVE_SIDEWALK') or 'not listed'}", f"other obstacles: {dot.get('OBSTACLES_OTHER') or 'none listed'}"]
        if widths:
            parts.append(f"sidewalk approach width {', '.join(widths)}, no unit documented")
        lines.append(f"Ramp {dot.get('RAMPID')}: " + "; ".join(parts) + ".")
    return lines


def nearby_notes(corner: dict) -> list[str]:
    """Report what the street and permit records add. They add context only, and neither one names a road owner."""
    notes = []
    segments = corner.get("street_segments")
    if segments:
        widths: dict = {}
        for s in segments:
            widths.setdefault(str(s.get("full_street_name") or "Unnamed").strip(), set()).add(s.get("streetwidth"))
        shown = "; ".join(f"{name} ({'/'.join(str(w) for w in sorted({x for x in found if x is not None}, key=float)) or 'width not listed'} ft paved)" for name, found in sorted(widths.items()))
        notes.append(f"NYC Street Centerline shows these streets within 100 m of the ramp: {shown}.")
        near = {_plain_street(n) for n in widths}
        named = {str(r.get(f)).strip() for r in corner.get("locations", []) + corner.get("progress", []) for f in ("stname1", "stname2", "street_nam", "street_n_1") if r.get(f)}
        absent = sorted(n for n in named if _plain_street(n) not in near)
        if absent:
            notes.append(f"Confirm the corner's location. No street within 100 m has this recorded name: {', '.join(absent)}.")
        notes.append("Centerline doesn't settle the road owner, because its documentation doesn't explain its jurisdiction field.")
    elif segments == []:
        notes.append("NYC Street Centerline shows no street within 100 m of the ramp. Confirm the ramp's location.")
    if corner.get("street_segments_more"):
        notes.append("More street segments are nearby than the 30 shown.")
    surveys = sorted(str(r.get("geocyclora"))[:10] for r in corner.get("locations", []) if parse_date(r.get("geocyclora")))
    if "permits" in corner and surveys:
        later = permits_after(corner, surveys[0])
        ramps = [p for p in later if RAMP_PERMIT.search(str(p.get("permittypedesc") or "").upper())]
        if later:
            more = " at least" if corner.get("permits_more") else ""
            notes.append(f"Street Construction Permits lists{more} {_count(len(later), 'permit')} for this block with work ending after the {surveys[0]} survey, including {len(ramps)} for pedestrian ramps. A permit shows work was allowed, not that it happened or touched this corner.")
        else:
            notes.append(f"Street Construction Permits lists no permit for this block with work ending after the {surveys[0]} survey. Permits that name other streets or use different spellings wouldn't appear.")
    notes += _inventory_notes(corner) + _distance_note(corner) + _column_notes(corner)
    for name in corner.get("nearby_not_checked") or []:
        notes.append(f"{name} wasn't checked for this corner, so its records may add something.")
    return notes


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
    return notes + nearby_notes(corner)


RAMP_PERMIT = re.compile(r"\bPED(ESTRIAN)?\s+RAMP")
SUFFIXES = {"STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "PLACE": "PL", "ROAD": "RD", "DRIVE": "DR", "COURT": "CT", "LANE": "LN", "PARKWAY": "PKWY", "HIGHWAY": "HWY", "EXPRESSWAY": "EXPY", "TERRACE": "TER"}

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
        ramp_work = ramp_permits_after(corner, survey)
        for field in CHECK_FIELDS:
            spec = dictionary["fields"][field]
            raw = row.get(spec.get("column", field))
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
            elif field == "ramp_length" and number < 0:
                value, label, reason = number, "assumed", "A length can't be negative, so confirm this value."
            elif uncertain:
                value, label, reason = number, "assumed", f"Unknown whether this is current. {uncertain}"
            elif stale:
                value, label, reason = number, "stale", f"Surveyed {survey}, but construction finished {built}."
            elif ramp_work:
                value, label, reason = number, "assumed", (f"Unknown whether this is current. {_count(len(ramp_work), 'pedestrian ramp permit')} for this block {'has' if len(ramp_work) == 1 else 'have'} work ending after the {survey} survey. "
                                                           "A permit shows work was allowed, not that it happened or touched this corner.")
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
        if length and slope and length.label == slope.label == "measured" and length.unit in ("ft", "in"):
            rise = abs(float(length.value)) * (12 if length.unit == "ft" else 1) * abs(float(slope.value)) / 100
            items.append(EvidenceItem(key=f"{ramp}:ramp_rise", ramp_id=ramp, field="ramp_rise", value=round(rise, 2), unit="in",
                                      unit_documented=length.unit_documented and slope.unit_documented, label="measured",
                                      source=f"Calculated from ramp {ramp}'s length and running slope", date=length.date,
                                      reason="Calculated, not directly measured."))
    for field, why in NOT_IN_DATASETS.items():
        item = EvidenceItem(key=f"corner:{field}", field=field, label="missing", source="Not in the NYC datasets used here", reason=why)
        item = (field == "sidewalk_width" and _sidewalk_item(corner)) or item
        items.append(_on_site(item, entries[item.key], built) if item.key in entries else item)
    if corner.get("context", {}).get("road_control_basis") == "assumed" and "corner:road_control" not in entries:
        items.append(EvidenceItem(key="corner:road_control", field="road_control", value="city", label="assumed", source="Default for a street NYSDOT's inventory doesn't list",
                                  reason="Assumed city-owned by default. No record confirms this."))
    elif "corner:road_control" in entries or corner.get("context", {}).get("road_control") != "city":
        item = EvidenceItem(key="corner:road_control", field="road_control", label="missing",
                            source="Not in the NYC datasets used here", reason="The road owner isn't confirmed.")
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
