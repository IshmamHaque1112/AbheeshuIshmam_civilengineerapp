import copy
import pytest
from cornerbrief.applicability import resolve
from cornerbrief.checker import check_value, find_conflicts, run_checks
from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.evidence import build_evidence, data_sufficient, validate_labels
from cornerbrief.models import EvidenceItem, RecordLabel, RecordsOutput
from cornerbrief.rules import RuleError, load_precedence, load_rules, validate_rule
from cornerbrief.site_visit import build_list

RULES, PREC = load_rules(), load_precedence()
BY_ID = {r["id"]: r for r in RULES}
CTX = {"inside_nyc": True, "work_type": "corner_ramp_row", "road_control": "city"}


def item(field="f", value=1.0, unit="percent", documented=True, label="measured", reason=""):
    return EvidenceItem(key=f"1:{field}", ramp_id="1", field=field, value=value, unit=unit, unit_documented=documented,
                        label=label, source="test", reason=reason)


def evidence(key):
    c = load_corner(key)
    return c, build_evidence(c, load_dictionary(c))


# Rule math, using hand-calculated values
@pytest.mark.parametrize("value,expected", [(8.0, "no conflict found"), (8.01, "limit exceeded"), (6.4, "no conflict found"), (-9.0, "limit exceeded")])
def test_slope_limit(value, expected):
    assert check_value(BY_ID["NYC-ADMIN-19-112-SLOPE"], item(value=value)).result == expected


@pytest.mark.parametrize("inches,expected", [(48, "no conflict found"), (47.9, "limit exceeded"), (60, "no conflict found")])
def test_width_converts_inches_to_feet(inches, expected):
    assert check_value(BY_ID["NYC-ADMIN-19-112-WIDTH"], item(value=inches, unit="in")).result == expected


def test_lip_limit():
    rule = BY_ID["NYC-ADMIN-19-112-LIP"]
    assert check_value(rule, item(value=0.625, unit="in")).result == "no conflict found"
    assert check_value(rule, item(value=0.75, unit="in")).result == "limit exceeded"


def test_transverse_rule_converts_inches_per_five_feet():
    rule = BY_ID["RCNY-34-2-09-TRANSVERSE"]  # 1 in / 60 in = 1.67%, 3 in / 60 in = 5%
    assert check_value(rule, item(value=1.6)).result == "limit exceeded"
    assert check_value(rule, item(value=1.7)).result == "no conflict found"
    assert check_value(rule, item(value=5.1)).result == "limit exceeded"


# Rule files
def test_verified_rule_without_section_fails():
    bad = copy.deepcopy(BY_ID["NYC-ADMIN-19-112-SLOPE"])
    bad["section"] = None
    with pytest.raises(RuleError):
        validate_rule(bad)


@pytest.mark.parametrize("field", ["url", "quote", "edition"])
def test_verified_rule_needs_each_source_field(field):
    bad = copy.deepcopy(BY_ID["NYC-ADMIN-19-112-WIDTH"])
    bad[field] = ""
    with pytest.raises(RuleError):
        validate_rule(bad)


def test_needs_source_rule_cannot_hold_limit():
    bad = copy.deepcopy(BY_ID["NYS-BCNYS-2025"])
    bad["limit"] = 9.5
    with pytest.raises(RuleError):
        validate_rule(bad)


def test_needs_source_rule_returns_unknown():
    out = run_checks(RULES, resolve({**CTX, "inside_nyc": False}, RULES, PREC), [])
    for rule_id in ("NYS-BCNYS-2025",):
        assert [o.result for o in out if o.rule_id == rule_id] == ["unknown"]


# Unknown values and placeholders
def test_undocumented_unit_returns_unknown():
    out = check_value(BY_ID["NYC-ADMIN-19-112-SLOPE"], item(value=20, documented=False))
    assert out.result == "unknown" and "not documented" in out.reason


def test_missing_value_returns_unknown_not_pass():
    assert check_value(BY_ID["NYC-ADMIN-19-112-SLOPE"], item(value=None, label="missing")).result == "unknown"


def test_placeholder_is_missing():
    _, ev = evidence("missing_or_stale")
    reveal = next(e for e in ev if e.field == "curb_reveal")
    assert reveal.label == "missing" and reveal.value is None and "placeholder" in reveal.reason


def test_live_units_are_documented_but_unreviewed_limits_stay_unknown():
    corner = copy.deepcopy(load_corner("standard"))
    corner["data_kind"] = "live"
    assert {f["unit_status"] for f in load_dictionary(corner)["fields"].values()} == {"documented"}
    ev = build_evidence(corner, load_dictionary(corner))
    outcomes = run_checks(RULES, resolve(CTX, RULES, PREC), ev)
    assert all(o.result in ("unknown", "not applicable") for o in outcomes)


# Stale data
def test_stale_measurements_are_rejected_as_current():
    corner, ev = evidence("missing_or_stale")
    assert next(e for e in ev if e.field == "ramp_width").label == "stale"
    ok, problems = data_sufficient(corner, ev)
    assert not ok and any("stale" in p for p in problems)
    assert check_value(BY_ID["NYC-ADMIN-19-112-SLOPE"], next(e for e in ev if e.field == "ramp_running_slope_total")).result == "unknown"


def test_construction_before_survey_is_not_stale():
    corner, ev = evidence("standard")
    assert data_sufficient(corner, ev)[0]


# Labels
def test_false_measured_label_is_rejected():
    _, ev = evidence("missing_or_stale")
    claim = RecordsOutput(summary="x", labels=[RecordLabel(key="8300001:curb_reveal", label="measured")])
    assert "shows missing" in validate_labels(claim, ev)[0]


# Applicability
def decision(ctx, rule_id):
    return next(d for d in resolve(ctx, RULES, PREC) if d.rule_id == rule_id)


def test_nyc_rejects_uniform_code_with_reason_and_source():
    d = decision(CTX, "NYS-BCNYS-2025")
    assert not d.applies and d.precedence_id == "PREC-NYC-VS-NYS"
    assert "except New York City" in d.reason and "dos.ny.gov" in d.url


def test_non_nyc_selects_nys_rules():
    ctx = {**CTX, "inside_nyc": False}
    assert decision(ctx, "NYS-BCNYS-2025").applies
    assert not decision(ctx, "NYC-ADMIN-19-112-SLOPE").applies


def test_non_nyc_nys_rules_return_unknown_until_sourced():
    out = run_checks(RULES, resolve({**CTX, "inside_nyc": False}, RULES, PREC), [])
    assert next(o for o in out if o.rule_id == "NYS-BCNYS-2025").result == "unknown"


def test_corner_ramp_does_not_use_building_code_limit():
    d = decision(CTX, "NYC-BC-1104-SITE-ROUTE")
    assert not d.applies


def test_building_route_flags_section_1104():
    ctx = {**CTX, "work_type": "building_route"}
    assert decision(ctx, "NYC-BC-1104-SITE-ROUTE").applies
    assert not decision(ctx, "NYC-ADMIN-19-112-SLOPE").applies
    out = run_checks(RULES, resolve(ctx, RULES, PREC), [])
    assert next(o for o in out if o.rule_id == "NYC-BC-1104-SITE-ROUTE").result == "unknown"


def test_state_road_returns_unknown():
    _, ev = evidence("standard")
    ctx = {**CTX, "road_control": "state"}
    out = [o for o in run_checks(RULES, resolve(ctx, RULES, PREC), ev) if o.rule_id == "NYC-ADMIN-19-112-SLOPE"]
    assert out and all(o.result == "unknown" for o in out)


# Conflicts
def test_conflicting_tiers_show_both_and_use_stricter():
    conflicts = find_conflicts(RULES, resolve(CTX, RULES, PREC), [])
    c = next(x for x in conflicts if x.parameter == "sidewalk_transverse_slope")
    assert len(c.rules) == 3 and c.decision == "Engineer decides"
    assert c.stricter_max == 2.0
    assert round(c.stricter_min, 2) == 1.67


def test_unrecorded_road_owner_returns_unknown():
    _, ev = evidence("standard")
    ctx = {**CTX, "road_control": "not_recorded"}
    out = [o for o in run_checks(RULES, resolve(ctx, RULES, PREC), ev) if o.rule_id == "NYC-ADMIN-19-112-SLOPE"]
    assert out and all(o.result == "unknown" and o.preview is None for o in out)
    assert "road owner" in " ".join(data_sufficient({"context": ctx, "locations": [{}]}, [])[1])


def test_conflict_warning_uses_stricter_limit():
    e = item(field="sidewalk_transverse_slope", value=3.0)  # Within 5%, outside 2.1%
    c = next(x for x in find_conflicts(RULES, resolve(CTX, RULES, PREC), [e]) if x.parameter == "sidewalk_transverse_slope")
    assert "outside the stricter" in c.warning


# Site visit
def test_site_visit_lists_missing_and_stale_items():
    corner, ev = evidence("missing_or_stale")
    actions = " ".join(i["action"] for i in build_list(ev, corner))
    assert "lip height" in actions and "Re-measure" in actions and "sidewalk width" in actions


def test_city_ada_and_dot_slope_limits_conflict_and_stricter_wins():
    c = next(x for x in find_conflicts(RULES, resolve(CTX, RULES, PREC), []) if x.parameter == "ramp_running_slope_total")
    assert c.stricter_max == 8 and len(c.rules) == 4
    e = item(field="ramp_running_slope_total", value=8.2)
    c = next(x for x in find_conflicts(RULES, resolve(CTX, RULES, PREC), [e]) if x.parameter == "ramp_running_slope_total")
    assert "outside the stricter" in c.warning


def test_width_conflict_compares_feet_and_inches():
    c = next(x for x in find_conflicts(RULES, resolve(CTX, RULES, PREC), []) if x.parameter == "ramp_width")
    assert len(c.rules) == 4 and c.stricter_min == 48 and c.unit == "in"


def test_ada_limits_use_hand_checked_values():
    assert check_value(BY_ID["ADA-2010-405-3-CROSS"], item(value=2.0)).result == "no conflict found"
    assert check_value(BY_ID["ADA-2010-405-3-CROSS"], item(value=2.1)).result == "limit exceeded"
    assert check_value(BY_ID["ADA-2010-406-3-FLARE-LEFT"], item(value=10.5)).result == "limit exceeded"
    assert check_value(BY_ID["ADA-2010-406-4-LANDING"], item(value=35, unit="in")).result == "limit exceeded"
    assert check_value(BY_ID["DOT-BROCHURE-COUNTER"], item(value=5.2)).result == "limit exceeded"


# H-1011 Table 1, hand-checked against the drawing
@pytest.mark.parametrize("rule_id,value,expected", [
    ("H1011-T1-RAMP-RUNNING-ACCEPT", 8.3, "no conflict found"), ("H1011-T1-RAMP-RUNNING-ACCEPT", 8.4, "limit exceeded"),
    ("H1011-T1-RAMP-RUNNING-DESIGN", 4.9, "limit exceeded"), ("H1011-T1-RAMP-RUNNING-DESIGN", 7.5, "no conflict found"), ("H1011-T1-RAMP-RUNNING-DESIGN", 7.6, "limit exceeded"),
    ("H1011-T1-RAMP-CROSS-ACCEPT", 2.0, "no conflict found"), ("H1011-T1-RAMP-CROSS-DESIGN", 1.6, "limit exceeded"),
    ("H1011-T1-COUNTER-ACCEPT", 5.1, "limit exceeded"), ("H1011-T1-COUNTER-DESIGN", 4.5, "no conflict found"),
    ("H1011-T1-FLARE-LEFT-ACCEPT", 10.0, "no conflict found"), ("H1011-T1-FLARE-LEFT-DESIGN", 9.6, "limit exceeded"),
])
def test_h1011_table_1(rule_id, value, expected):
    assert check_value(BY_ID[rule_id], item(value=value)).result == expected


def test_h1011_dimensions():
    assert check_value(BY_ID["H1011-N17-WIDTH-MIN"], item(value=47, unit="in")).result == "limit exceeded"
    assert check_value(BY_ID["H1011-N17-WIDTH-TARGET"], item(value=59, unit="in")).result == "limit exceeded"
    assert check_value(BY_ID["H1011-N12-6-LANDING-LENGTH"], item(value=48, unit="in")).result == "no conflict found"
    assert check_value(BY_ID["H1011-N9-LEVEL-CHANGE"], item(value=0.3, unit="in")).result == "limit exceeded"


def test_ramp_rise_is_calculated_and_checked():
    _, ev = evidence("standard")
    rise = next(e for e in ev if e.key == "8100001:ramp_rise")
    assert rise.value == round(6.5 * 12 * 6.4 / 100, 2)  # 4.99 inches
    assert check_value(BY_ID["H1011-N18-RISE"], rise).result == "no conflict found"
    assert check_value(BY_ID["H1011-N18-RISE"], item(field="ramp_rise", value=31, unit="in")).result == "limit exceeded"


def test_existing_ramps_are_not_failed_on_design_targets():
    _, ev = evidence("standard")
    decisions = resolve(CTX, RULES, PREC)
    assert not [o for o in run_checks(RULES, decisions, ev) if BY_ID[o.rule_id]["stage"] == "design"]
    from cornerbrief.checker import design_targets
    over = [o for o in design_targets(RULES, decisions, ev) if o.preview == "limit exceeded"]
    assert {o.rule_id for o in over} >= {"H1011-T1-RAMP-CROSS-DESIGN", "H1011-N17-WIDTH-TARGET"}


def test_design_targets_are_not_conflicts():
    conflicts = find_conflicts(RULES, resolve(CTX, RULES, PREC), [])
    assert not [r for c in conflicts for r in c.rules if r["rule_id"].endswith("DESIGN") or r["rule_id"].endswith("TARGET")]


def test_stage_is_required():
    bad = copy.deepcopy(BY_ID["NYC-ADMIN-19-112-WIDTH"])
    del bad["stage"]
    with pytest.raises(RuleError):
        validate_rule(bad)


# Named-reviewer gate
def test_sourced_rule_without_reviewer_returns_unknown_with_math():
    _, ev = evidence("standard")
    out = [o for o in run_checks(RULES, resolve(CTX, RULES, PREC), ev) if o.rule_id == "NYC-ADMIN-19-112-SLOPE"]
    assert all(o.result == "unknown" and o.preview == "no conflict found" and o.math.startswith("Unreviewed calculation") for o in out)


def test_reviewed_rule_returns_a_limit_result():
    _, ev = evidence("standard")
    reviewed = [dict(r, status="verified", reviewed_by="Pat Example", reviewed_on="2026-11-03") if r["id"] == "NYC-ADMIN-19-112-SLOPE" else r for r in RULES]
    out = [o for o in run_checks(reviewed, resolve(CTX, reviewed, PREC), ev) if o.rule_id == "NYC-ADMIN-19-112-SLOPE"]
    assert all(o.result == "no conflict found" and o.preview is None for o in out)


def test_verified_status_needs_a_named_reviewer():
    bad = dict(BY_ID["NYC-ADMIN-19-112-SLOPE"], status="verified", reviewed_by=None)
    with pytest.raises(RuleError):
        validate_rule(bad)


def test_no_rule_is_verified_until_someone_reviews_it():
    assert not [r["id"] for r in RULES if r["status"] == "verified"]


def test_review_script_records_a_named_reviewer(tmp_path):
    import importlib.util, shutil
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("review_rule", Path(__file__).parent.parent / "scripts" / "review_rule.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    root = tmp_path / "rules"
    shutil.copytree(Path(__file__).parent.parent / "rules", root)
    with pytest.raises(ValueError):
        mod.review("NYC-ADMIN-19-112-SLOPE", "Pat", root=root)
    with pytest.raises(ValueError):
        mod.review("NYS-BCNYS-2025", "Pat Example", root=root)
    mod.review("NYC-ADMIN-19-112-SLOPE", "Pat Example", root=root)
    assert next(r for r in load_rules(root) if r["id"] == "NYC-ADMIN-19-112-SLOPE")["status"] == "verified"


# Unknown currency
@pytest.mark.parametrize("change,progress", [
    ({"geocyclora": None}, None),
    ({}, []),
    ({}, [{"cornerid": 123, "construc_2": "Constructed", "construc_1": "2020/01/01"}]),
    ({}, [{"cornerid": 9000001, "construc_2": "Constructed", "construc_1": None}]),
])
def test_missing_date_or_unmatched_record_is_unknown(change, progress):
    corner = copy.deepcopy(load_corner("standard"))
    corner["locations"][0].update(change)
    if progress is not None:
        corner["progress"] = progress
    ev = build_evidence(corner, load_dictionary(corner))
    ok, problems = data_sufficient(corner, ev)
    assert not ok and any("Unknown whether" in p for p in problems)
    width = next(e for e in ev if e.field == "ramp_width" and e.ramp_id == "8100001")
    assert width.label == "assumed"
    assert check_value(BY_ID["NYC-ADMIN-19-112-WIDTH"], width).result == "unknown"


def test_undocumented_units_stop_the_design_path():
    corner = copy.deepcopy(load_corner("standard"))
    corner["data_kind"] = "NYC Open Data"
    dictionary = copy.deepcopy(load_dictionary(corner))
    for field in dictionary["fields"].values():
        field["unit_status"] = "assumed"
    ok, problems = data_sufficient(corner, build_evidence(corner, dictionary))
    assert not ok and any("units" in p for p in problems)


def test_problems_use_plain_field_names():
    corner = copy.deepcopy(load_corner("standard"))
    corner["data_kind"] = "NYC Open Data"
    corner["locations"][0].update(curb_reveal=None, lnd_width=None)
    _, problems = data_sufficient(corner, build_evidence(corner, load_dictionary(corner)))
    text = " ".join(problems)
    assert "lip height" in text and "landing width" in text
    for raw in ("curb_reveal", "lnd_width", ":", "ramp_running_slope_total"):
        assert raw not in text.replace("units aren't documented for:", "")
