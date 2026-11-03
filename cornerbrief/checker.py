"""Run limits in plain code. Results are limited to the four allowed values."""
from typing import Optional
from .models import Conflict, Decision, EvidenceItem, RuleOutcome

CONVERT = {("in", "ft"): 1 / 12, ("ft", "in"): 12, ("in", "in"): 1, ("ft", "ft"): 1, ("percent", "percent"): 1}


def rule_limits_percent(rule: dict) -> tuple[Optional[float], Optional[float]]:
    limit, op = rule["limit"], rule["operator"]
    factor = {"in_per_5ft": 100 / 60, "ft": 12}.get(rule["unit"], 1)  # 5 feet is 60 inches; lengths compare in inches
    if op == "max":
        return None, limit * factor
    if op == "min":
        return limit * factor, None
    if op == "range":
        return limit["min"] * factor, limit["max"] * factor
    return None, None


def limit_text(rule: dict) -> str:
    unit = {"percent": "%", "in_per_5ft": " in per 5 ft", "ft": " ft", "in": " in"}.get(rule.get("unit"), "")
    limit, op = rule["limit"], rule["operator"]
    if op == "max":
        return f"{limit}{unit} maximum"
    if op == "min":
        return f"{limit}{unit} minimum"
    if op == "range":
        return f"{limit['min']} to {limit['max']}{unit}"
    return "No numeric limit available"


def _base(rule: dict, ramp=None) -> dict:
    return dict(rule_id=rule["id"], title=rule["title"], ramp_id=ramp, parameter=rule.get("parameter"),
                limit_text=limit_text(rule), authority_type=rule["authority_type"], section=rule.get("section"),
                url=rule.get("url"), quote=rule.get("quote"))


def check_value(rule: dict, item: EvidenceItem) -> RuleOutcome:
    base = _base(rule, item.ramp_id)
    base.update(value=item.value, value_unit=item.unit)
    if item.label != "measured":
        return RuleOutcome(**base, result="unknown", reason=f"The value is {item.label}. {item.reason}".strip())
    if not item.unit_documented:
        return RuleOutcome(**base, result="unknown",
                           reason=f"The unit is not documented, so no limit was checked. Unconfirmed reading: {item.value} {item.unit}.")
    value = abs(float(item.value))
    if rule["unit"] == "in_per_5ft":
        if item.unit != "percent":
            return RuleOutcome(**base, result="unknown", reason="The units cannot be compared.")
        low, high = rule_limits_percent(rule)
        ok = low <= value <= high
        shown = f"{value:g}% against {low:.2f}% to {high:.2f}% (inches per 60 inches × 100)"
    else:
        factor = CONVERT.get((item.unit, rule["unit"]))
        if factor is None:
            return RuleOutcome(**base, result="unknown", reason="The units cannot be compared.")
        converted = value * factor
        limit = rule["limit"]
        symbol = {"percent": "%", "ft": " ft", "in": " in"}[rule["unit"]]
        conversion = "" if factor == 1 else f"{value:g} {item.unit} = "
        if rule["operator"] == "range":
            ok = limit["min"] <= converted <= limit["max"]
            shown = f"{conversion}{converted:.3g}{symbol} against {limit['min']} to {limit['max']}{symbol}"
        elif rule["operator"] == "max":
            ok = converted <= limit
            shown = f"{conversion}{converted:.3g}{symbol} {'≤' if ok else '>'} {limit}{symbol}"
        else:
            ok = converted >= limit
            shown = f"{conversion}{converted:.3g}{symbol} {'≥' if ok else '<'} {limit}{symbol}"
    return RuleOutcome(**base, result="no conflict found" if ok else "limit exceeded", math=shown)


def run_checks(rules: list[dict], decisions: list[Decision], evidence: list[EvidenceItem]) -> list[RuleOutcome]:
    by_decision = {d.rule_id: d for d in decisions}
    by_field: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        by_field.setdefault(item.field, []).append(item)
    outcomes = []
    for rule in rules:
        if rule["stage"] == "design":
            continue  # Surveyed ramps are compared with acceptance limits, not targets for new work
        decision = by_decision[rule["id"]]
        if not decision.applies:
            outcomes.append(RuleOutcome(**_base(rule), result="not applicable", reason=decision.reason))
        elif decision.forced_unknown:
            outcomes.append(RuleOutcome(**_base(rule), result="unknown", reason=decision.reason))
        elif rule["status"] != "verified":
            outcomes.append(RuleOutcome(**_base(rule), result="unknown", reason="The exact source text is still needed. No limit was checked."))
        elif rule["operator"] == "reference":
            outcomes.append(RuleOutcome(**_base(rule), result="unknown", reason=rule.get("notes") or "This rule has no numeric check."))
        else:
            items = by_field.get(rule["parameter"], [])
            if not items:
                outcomes.append(RuleOutcome(**_base(rule), result="unknown", reason="There is no value for this field."))
            outcomes.extend(check_value(rule, item) for item in items)
    return outcomes


def design_targets(rules: list[dict], decisions: list[Decision], evidence: list[EvidenceItem]) -> list[RuleOutcome]:
    """Compare surveyed values with limits for new design and field layout. This shows what a rebuild would need."""
    applying = {d.rule_id: d for d in decisions}
    out = []
    for rule in rules:
        if rule["stage"] != "design" or not applying[rule["id"]].applies:
            continue
        items = [e for e in evidence if e.field == rule["parameter"]]
        if not items:
            out.append(RuleOutcome(**_base(rule), result="unknown", reason="There is no value for this field."))
        for item in items:
            if applying[rule["id"]].forced_unknown:
                out.append(RuleOutcome(**_base(rule, item.ramp_id), result="unknown", reason=applying[rule["id"]].reason))
            else:
                out.append(check_value(rule, item))
    return out


def find_conflicts(rules: list[dict], decisions: list[Decision], evidence: list[EvidenceItem]) -> list[Conflict]:
    applying = {d.rule_id for d in decisions if d.applies}
    groups: dict[str, list[dict]] = {}
    for rule in rules:
        if rule["id"] in applying and rule["status"] == "verified" and rule["stage"] != "design" and rule["operator"] in ("max", "min", "range"):
            groups.setdefault(rule["parameter"], []).append(rule)
    conflicts = []
    for parameter, group in groups.items():
        if len(group) < 2:
            continue
        unit = "in" if group[0]["unit"] in ("in", "ft") else "percent"
        bounds = [rule_limits_percent(r) for r in group]
        if len({(round(a or -1, 3), round(b or -1, 3)) for a, b in bounds}) < 2:
            continue
        mins = [a for a, _ in bounds if a is not None]
        maxes = [b for _, b in bounds if b is not None]
        low, high = (max(mins) if mins else None), (min(maxes) if maxes else None)
        measured = [e for e in evidence if e.field == parameter and e.label == "measured" and e.unit_documented]
        outside = [e for e in measured if (low is not None and abs(e.value) * (1 if e.unit != "ft" else 12) < low) or (high is not None and abs(e.value) > high)]
        if not measured:
            warning = "These rules set different limits, and no measured value is available yet."
        elif outside:
            warning = "A measured value falls outside the stricter limit. An engineer should decide which rule controls."
        else:
            warning = "Measured values fall within the stricter limit, but an engineer should still decide which rule controls."
        conflicts.append(Conflict(parameter=parameter, stricter_min=low, stricter_max=high, unit=unit, warning=warning,
                                  rules=[{"rule_id": r["id"], "section": r["section"], "limit": limit_text(r), "url": r["url"]} for r in group]))
    return conflicts
