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
CTX = {"inside_nyc": True, "work_type": "corner_ramp_row", "road_control": "not_recorded"}


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
    bad = copy.deepcopy(BY_ID["H1011-FLARE"])
    bad["limit"] = 9.5
    with pytest.raises(RuleError):
        validate_rule(bad)


def test_needs_source_rule_returns_unknown():
    _, ev = evidence("standard")
    out = run_checks(RULES, resolve(CTX, RULES, PREC), ev)
    for rule_id in ("H1011-FLARE", "H1011-RAMP-SLOPES", "ADA-2010-CURB-RAMP"):
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


def test_live_dictionary_units_are_not_documented():
    corner = copy.deepcopy(load_corner("standard"))
    corner["data_kind"] = "live"
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
    assert len(c.rules) == 2 and c.decision == "Engineer decides"
    assert c.stricter_max_percent == 2.1
    assert round(c.stricter_min_percent, 2) == 1.67


def test_conflict_warning_uses_stricter_limit():
    e = item(field="sidewalk_transverse_slope", value=3.0)  # Within 5%, outside 2.1%
    c = find_conflicts(RULES, resolve(CTX, RULES, PREC), [e])[0]
    assert "outside the stricter" in c.warning


# Site visit
def test_site_visit_lists_missing_and_stale_items():
    corner, ev = evidence("missing_or_stale")
    actions = " ".join(i["action"] for i in build_list(ev, corner))
    assert "lip height" in actions and "Re-measure" in actions and "sidewalk width" in actions
