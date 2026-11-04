"""Check and store what an engineer measured on site. No AI here."""
import base64, math, uuid
from datetime import date
from .evidence import NOT_IN_DATASETS, parse_date
from .paths import RUNS

# These units are fixed for entries made on site, so they don't depend on the dataset's undocumented units.
UNITS = {"ramp_running_slope_total": "percent", "ramp_cross_slope": "percent", "gutter_slope": "percent", "counter_slope": "percent",
         "lnd_cross_slope": "percent", "ramp_right_flare": "percent", "ramp_left_flare": "percent", "ramp_width": "in", "lnd_width": "in",
         "lnd_length": "in", "ramp_length": "ft", "curb_reveal": "in", "sidewalk_width": "ft", "legal_grade": "percent", "sidewalk_transverse_slope": "percent"}
# Slopes may be recorded with either sign. Lengths can't be negative.
SLOPE_RANGE = (0, 40)
LENGTH_RANGES = {"ramp_width": (1, 400), "lnd_width": (1, 400), "lnd_length": (1, 400), "ramp_length": (0.1, 400), "curb_reveal": (0, 12), "sidewalk_width": (0.1, 400)}
CHOICES = {"ramp_type": ["C1 perpendicular", "C2 directional", "C3 parallel", "C4 shared parallel", "C5 blended transition"],
           "road_control": ["city", "state"]}
PLACEHOLDERS = {999.0, -999.0, 9999.0}
PHOTO_TYPES = {b"\xff\xd8\xff": ".jpg", b"\x89PNG\r\n\x1a\n": ".png", b"RIFF": ".webp"}
PHOTO_LIMIT = 5 * 1024 * 1024
PHOTOS = RUNS / "photos"


def field_inputs(evidence: list[dict]) -> list[dict]:
    """List the inputs a person can add on site: anything not current, plus anything already entered on site."""
    out = []
    for e in evidence:
        if e["field"] == "ramp_rise" or not (e["label"] in ("missing", "stale", "assumed") or e.get("on_site")):
            continue
        unit = UNITS.get(e["field"])
        out.append(dict(key=e["key"], field=e["field"], ramp_id=e["ramp_id"], label=e["label"], unit=unit, choices=CHOICES.get(e["field"]),
                        value=e["value"] if e.get("on_site") else None, on_site=bool(e.get("on_site"))))
    return out


def save_photo(photo: dict) -> str:
    try:
        data = base64.b64decode(str(photo.get("data", "")).split(",")[-1], validate=True)
    except ValueError as exc:
        raise ValueError("A photo couldn't be read.") from exc
    if len(data) > PHOTO_LIMIT:
        raise ValueError("Each photo must be 5 MB or smaller.")
    suffix = next((s for magic, s in PHOTO_TYPES.items() if data.startswith(magic) and (magic != b"RIFF" or data[8:12] == b"WEBP")), None)
    if not suffix:
        raise ValueError("Photos must be JPEG, PNG or WebP files.")
    PHOTOS.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex + suffix
    (PHOTOS / name).write_bytes(data)
    return name


def _value(field: str, raw):
    if field in CHOICES:
        if raw not in CHOICES[field]:
            raise ValueError(f"{raw} isn't one of the choices for {field}.")
        return raw
    if isinstance(raw, bool):
        raise ValueError(f"The value for {field} must be a number.")
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"The value for {field} must be a number.") from exc
    if not math.isfinite(number) or number in PLACEHOLDERS:
        raise ValueError(f"{raw} is outside the plausible range for {field}.")
    low, high = LENGTH_RANGES.get(field, SLOPE_RANGE)
    if not low <= (number if field in LENGTH_RANGES else abs(number)) <= high:
        raise ValueError(f"{raw} is outside the plausible range for {field}.")
    return number


def validate_entries(raw: list[dict], allowed: list[dict], measured_on: str, by: str, today: date | None = None) -> list[dict]:
    """Return clean entries, or raise ValueError with a message the person can act on."""
    if not isinstance(by, str) or not by.strip():
        raise ValueError("Enter the name of the person who measured.")
    by = " ".join(by.split())
    measured = parse_date(measured_on) if isinstance(measured_on, str) else None
    if not measured or len(measured_on) != 10:
        raise ValueError("Enter the measurement date as YYYY-MM-DD.")
    if measured > (today or date.today()):
        raise ValueError("The measurement date can't be in the future.")
    if raw is not None and not isinstance(raw, list):
        raise ValueError("The measurements must be a list.")
    fields = {a["key"]: a for a in allowed}
    entries = []
    for item in raw or []:
        if not isinstance(item, dict):
            raise ValueError("Each measurement must have a key and a value.")
        if item.get("photo") is not None and not isinstance(item["photo"], dict):
            raise ValueError("A photo couldn't be read.")
        spec = fields.get(item.get("key")) if isinstance(item.get("key"), str) else None
        if not spec:
            raise ValueError(f"{item.get('key')} isn't an input this corner needs.")
        entries.append(dict(key=spec["key"], field=spec["field"], value=_value(spec["field"], item.get("value")), unit=spec["unit"],
                            date=str(measured), by=by, photo=item.get("photo")))
    if not entries:
        raise ValueError("Enter at least one measurement.")
    for entry in entries:
        if entry["photo"]:
            entry["photo"] = save_photo(entry["photo"])
    return entries


def merge_entries(old: list[dict], new: list[dict]) -> list[dict]:
    merged = {e["key"]: e for e in old}
    for e in new:
        merged[e["key"]] = {**e, "photo": e["photo"] or merged.get(e["key"], {}).get("photo")}
    return list(merged.values())


def _shown(o: dict) -> str:
    return o.get("preview") or o["result"]


def compare_runs(before: dict, after: dict) -> dict:
    """Describe what a rerun changed, so the engineer doesn't have to compare two packets."""
    old_inputs = {e["key"]: e for e in before["evidence"]}
    inputs = []
    for e in after["evidence"]:
        old = old_inputs.get(e["key"])
        fingerprint = lambda x: (x["label"], x["value"], x.get("on_site"), x.get("date"), x["source"], x.get("photo"))
        if old and fingerprint(old) != fingerprint(e):
            inputs.append(dict(key=e["key"], field=e["field"], ramp_id=e["ramp_id"], unit=e["unit"], before_label=old["label"], before_value=old["value"], after_label=e["label"], after_value=e["value"], on_site=e.get("on_site", False), after_date=e.get("date"), after_source=e["source"]))
    key = lambda o: (o["rule_id"], o["ramp_id"])
    old_results = {key(o): o for o in before["rule_results"]}
    results = []
    for o in after["rule_results"]:
        old = old_results.get(key(o))
        if old is None or _shown(old) != _shown(o) or old["result"] != o["result"] or old["math"] != o["math"]:
            results.append(dict(title=o["title"], ramp_id=o["ramp_id"], before=_shown(old) if old else "not checked", after=_shown(o), math=o["math"] or o["reason"], unreviewed=bool(o["preview"])))
    visit = lambda r: {(v["where"], v["action"]) for v in r["site_visit"]}
    return dict(state_before=before["state"], state_after=after["state"], inputs=inputs, results=results,
                site_visit_done=sorted(f"{w}: {a}" for w, a in visit(before) - visit(after)), site_visit_added=sorted(f"{w}: {a}" for w, a in visit(after) - visit(before)))
