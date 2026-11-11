"""Explain, one dimension at a time, why a ramp's geometry can or can't be built. No AI here.

This explains the gate in parts_kit.checked_ramps. It never loosens it: a row marked documented
doesn't make a plan, and nothing here fills in, converts or promotes a value that isn't documented.
"""
import math
from .evidence import input_name
from .models import EvidenceItem
from .parts_kit import checked_ramps, model_dimension

# Each record field the concept geometry needs, the model input it feeds and the unit that input uses
DIMENSIONS = [
    dict(field="ramp_width", input="width_ft", name="Ramp width", kind="length"),
    dict(field="ramp_length", input="length_ft", name="Ramp length", kind="length"),
    dict(field="lnd_width", input="landing_width_ft", name="Landing width", kind="length"),
    dict(field="lnd_length", input="landing_length_ft", name="Landing length", kind="length"),
    dict(field="ramp_running_slope_total", input="slope_pct", name="Running slope", kind="slope"),
]
# Only documented units with a known conversion. A slope stays a percentage; it's never a length.
TO_MODEL = {"length": {"in": 1 / 12, "ft": 1.0}, "slope": {"percent": 1.0}}
MODEL_UNIT = {"length": "ft", "slope": "%"}
PLACEHOLDERS = {999.0, -999.0, 9999.0, -9999.0}
STATUS = {"measured": "documented", "assumed": "assumed", "stale": "stale", "missing": "unresolved"}


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _row(spec: dict, ramp_id: str, item: EvidenceItem | None) -> dict:
    row = dict(key=f"{ramp_id}:{spec['field']}", ramp_id=ramp_id, field=spec["field"], input=spec["input"],
               name=input_name(spec["field"], ramp_id), dimension=spec["name"], model_unit=MODEL_UNIT[spec["kind"]], model_value=None)
    if item is None:
        return dict(row, status="unresolved", value=None, unit=None, unit_documented=False, source=None, date=None, on_site=False,
                    reason="No record gives this dimension.")
    row.update(value=item.value, unit=item.unit, unit_documented=item.unit_documented, source=item.source, date=item.date,
               on_site=item.on_site, status=STATUS[item.label], reason=item.reason)
    if row["status"] != "documented":
        return row
    # A measured label alone isn't enough: the value, the unit and its documentation must all hold up
    number, factor = _number(item.value), TO_MODEL[spec["kind"]].get(item.unit)
    problem = ""
    if number is None:
        problem = "The record has no usable number."
    elif number in PLACEHOLDERS:
        problem = f"{number:g} is a placeholder value."
    elif not item.unit:
        problem = "The record has no unit, so the value can't be read."
    elif not item.unit_documented:
        problem = f"The unit {item.unit} isn't documented, so the value can't be read."
    elif factor is None:
        problem = f"{item.unit} isn't a unit this model can use for a {spec['kind']}."
    elif spec["kind"] == "length" and number <= 0:
        problem = "A model length must be greater than zero."
    if problem:
        return dict(row, status="unresolved", reason=" ".join(x for x in (problem, item.reason) if x))
    model = model_dimension(item, slope=spec["kind"] == "slope")
    return dict(row, model_value=model)


def dimension_rows(evidence: list[EvidenceItem]) -> list[dict]:
    """One row per ramp and dimension, in record order. Every row keeps its own source, date, unit and reason."""
    by_ramp: dict[str, dict] = {}
    for e in evidence:
        if e.ramp_id:
            by_ramp.setdefault(e.ramp_id, {})[e.field] = e
    return [_row(spec, ramp_id, fields.get(spec["field"])) for ramp_id, fields in by_ramp.items() for spec in DIMENSIONS]


def blocker(row: dict) -> str:
    return f"{row['name']} is {row['status']}. {row['reason']}".strip()


def readiness(evidence: list[EvidenceItem]) -> dict:
    """Say which dimensions are documented and which block the concept geometry.

    `geometry_permitted` is parts_kit.checked_ramps' own answer, unchanged. It stays all or nothing:
    one blocked dimension on any ramp leaves every ramp without geometry, while the other rows stay inspectable.
    """
    rows = dimension_rows(evidence)
    blocked = [r for r in rows if r["status"] != "documented"]
    permitted = bool(checked_ramps(evidence))
    note = ""
    if permitted and blocked:
        # The existing gate accepts these rows. Changing that gate needs a reviewed decision, so it's reported, not changed.
        note = "The geometry gate allows these inputs, but some of their units can't be confirmed here. Review them before using the quantities."
    return dict(rows=rows, blockers=[blocker(r) for r in blocked], geometry_permitted=permitted, gate_note=note,
                counts={s: sum(r["status"] == s for r in rows) for s in ("documented", "assumed", "unresolved", "stale")})
