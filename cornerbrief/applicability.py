"""Decide in code which rules apply, why, and on what source."""
from .models import Decision


def resolve(context: dict, rules: list[dict], precedence: dict) -> list[Decision]:
    inside = context.get("inside_nyc", True)
    work = context.get("work_type", "corner_ramp_row")
    road = context.get("road_control", "not_recorded")
    decisions = []
    for rule in rules:
        jur = rule["jurisdiction"]
        applies, forced, prec = True, False, None
        if inside and jur == "nys":
            applies, prec = False, "PREC-NYC-VS-NYS"
        elif not inside and jur == "nyc":
            applies, prec = False, "PREC-OUTSIDE-NYC"
        elif work not in rule["applies_to"]:
            applies = False
            prec = "PREC-BUILDING-ROUTE" if rule["id"] == "NYC-BC-1104-SITE-ROUTE" or work == "building_route" else "PREC-CORNER-RAMP"
        elif not inside:
            prec = "PREC-OUTSIDE-NYC"
        elif work == "building_route":
            prec = "PREC-BUILDING-ROUTE"
        else:
            prec = "PREC-CORNER-RAMP"
        if applies and inside and road != "city":
            forced, prec = True, "PREC-STATE-ROAD"
        p = precedence[prec]
        reason = p["reason"] if applies or prec != "PREC-CORNER-RAMP" else "This rule is for a different type of work, so it is not a corner ramp limit."
        decisions.append(Decision(rule_id=rule["id"], title=rule["title"], jurisdiction=jur, applies=applies,
                                  forced_unknown=forced, reason=reason, precedence_id=prec,
                                  source_section=p["source_section"], url=p["url"], status=rule["status"]))
    return decisions
