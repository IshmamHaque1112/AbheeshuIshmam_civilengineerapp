"""M2a: each ramp dimension says where it came from, and the geometry and quantities carry one revision."""
import copy
import pytest
from cornerbrief import planning, preview, revision
from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.evidence import build_evidence
from cornerbrief.parts_kit import checked_ramps
from cornerbrief.planning import run_planning
from cornerbrief.readiness import dimension_rows, readiness
from test_preview import GOOD, _with_assumption

FIELDS = ["ramp_width", "ramp_length", "lnd_width", "lnd_length", "ramp_running_slope_total"]


def evidence_for(key, change=None, dictionary_change=None):
    corner = load_corner(key)
    dictionary = copy.deepcopy(load_dictionary(corner))
    for column, value in (change or {}).items():
        corner["locations"][0][column] = value
    for field, spec in (dictionary_change or {}).items():
        dictionary["fields"][field].update(spec)
    return build_evidence(corner, dictionary)


def row(rows, key):
    return next(r for r in rows if r["key"] == key)


def with_item(evidence, key, **update):
    return [e.model_copy(update=update) if e.key == key else e for e in evidence]


# Per-dimension readiness
def test_every_ramp_gets_one_row_per_dimension_with_its_record():
    rows = dimension_rows(evidence_for("standard"))
    assert [(r["ramp_id"], r["field"]) for r in rows] == [(ramp, f) for ramp in ("8100001", "8100002") for f in FIELDS]
    width = row(rows, "8100001:ramp_width")
    assert width["status"] == "documented" and width["value"] == 60.0 and width["unit"] == "in" and width["unit_documented"]
    assert width["source"] == "Pedestrian Ramp Locations, ramp 8100001" and width["date"] == "2023-06-14"
    assert width["model_value"] == 5.0 and width["model_unit"] == "ft"
    assert row(rows, "8100001:ramp_length")["model_value"] == 6.5  # Already in feet, not divided again


def test_slope_stays_a_percentage():
    slope = row(dimension_rows(evidence_for("standard")), "8100001:ramp_running_slope_total")
    assert slope["status"] == "documented" and slope["unit"] == "percent"
    assert slope["model_value"] == 6.4 and slope["model_unit"] == "%"
    # A slope recorded in inches is not a slope this model can read, and it's never turned into feet
    rows = dimension_rows(with_item(evidence_for("standard"), "8100001:ramp_running_slope_total", unit="in"))
    slope = row(rows, "8100001:ramp_running_slope_total")
    assert slope["status"] == "unresolved" and slope["model_value"] is None and "in isn't a unit" in slope["reason"]


def test_one_stale_dimension_leaves_the_others_inspectable():
    evidence = with_item(evidence_for("standard"), "8100002:lnd_length", label="stale", reason="Surveyed 2023-06-14, but construction finished 2024-01-02.")
    result = readiness(evidence)
    stale = row(result["rows"], "8100002:lnd_length")
    assert stale["status"] == "stale" and stale["value"] == 54.0 and stale["model_value"] is None
    assert stale["reason"] == "Surveyed 2023-06-14, but construction finished 2024-01-02." and stale["date"] == "2023-06-14"
    others = [r for r in result["rows"] if r["key"] != "8100002:lnd_length"]
    assert len(others) == 9 and all(r["status"] == "documented" and r["model_value"] is not None for r in others)
    assert result["blockers"] == ["Ramp 8100002 landing length is stale. Surveyed 2023-06-14, but construction finished 2024-01-02."]
    # The existing gate stays all or nothing, and readiness reports its answer instead of loosening it
    assert checked_ramps(evidence) == [] and result["geometry_permitted"] is False and run_planning(evidence) is None


def test_stale_corner_keeps_every_record_and_stays_stale():
    result = readiness(evidence_for("missing_or_stale"))
    assert result["counts"] == dict(documented=0, assumed=0, unresolved=0, stale=5)
    width = row(result["rows"], "8300001:ramp_width")
    assert width["value"] == 60.0 and width["unit"] == "in" and width["date"] == "2019-10-19"
    assert width["reason"] == "Surveyed 2019-10-19, but construction finished 2025-05-20."


def test_saved_real_corner_keeps_its_assumptions_and_their_reasons():
    result = readiness(evidence_for("real_test"))
    assert result["counts"]["assumed"] == 10 and result["geometry_permitted"] is False
    width = row(result["rows"], "116256:ramp_width")
    assert width["status"] == "assumed" and width["value"] == 45.5 and width["unit"] == "in" and width["date"] == "2018-08-08"
    assert width["source"] == "Pedestrian Ramp Locations, ramp 116256" and width["model_value"] is None
    assert width["reason"].startswith("Unknown whether this is current. 1 pedestrian ramp permit located at this ramp")
    assert all(b.split(" is ")[1].startswith("assumed.") for b in result["blockers"])
    assert run_planning(evidence_for("real_test")) is None


@pytest.mark.parametrize("value,reason", [(None, "No value in the record."), ("", "No value in the record."), (999, "999 is a placeholder value."), (9999, "9999 is a placeholder value.")])
def test_missing_and_placeholder_values_are_unresolved_and_never_filled_in(value, reason):
    rows = dimension_rows(evidence_for("real_test", change={"ramp_width": value}))
    width = row(rows, "116256:ramp_width")
    assert width["status"] == "unresolved" and width["value"] is None and width["model_value"] is None
    assert width["reason"] == reason and width["source"] == "Pedestrian Ramp Locations, ramp 116256"


def test_a_measured_placeholder_is_still_unresolved():
    rows = dimension_rows(with_item(evidence_for("standard"), "8100001:ramp_width", value=999.0))
    assert row(rows, "8100001:ramp_width")["status"] == "unresolved" and "999 is a placeholder value." in row(rows, "8100001:ramp_width")["reason"]


def test_undocumented_unit_is_unresolved_and_blocks_like_before():
    evidence = evidence_for("standard", dictionary_change={"lnd_width": {"unit_status": "undocumented"}})
    result = readiness(evidence)
    width = row(result["rows"], "8100001:lnd_width")
    assert width["status"] == "unresolved" and width["unit"] == "in" and not width["unit_documented"]
    assert width["value"] == 60.0 and width["model_value"] is None and "isn't documented" in width["reason"]
    assert result["geometry_permitted"] is False and run_planning(evidence) is None


def test_unsupported_or_missing_unit_is_unresolved():
    rows = dimension_rows(evidence_for("standard", dictionary_change={"ramp_width": {"unit": "m"}}))
    assert row(rows, "8100001:ramp_width")["status"] == "unresolved" and "m isn't a unit" in row(rows, "8100001:ramp_width")["reason"]
    rows = dimension_rows(with_item(evidence_for("standard"), "8100001:ramp_width", unit=None))
    assert row(rows, "8100001:ramp_width")["status"] == "unresolved" and "no unit" in row(rows, "8100001:ramp_width")["reason"]


def test_unsupported_unit_blocks_geometry_and_planning():
    evidence = evidence_for("standard", dictionary_change={"ramp_width": {"unit": "m"}})
    result = readiness(evidence)
    assert result["geometry_permitted"] is False
    assert checked_ramps(evidence) == [] and run_planning(evidence) is None


@pytest.mark.parametrize("field,update", [
    ("ramp_width", {"unit": None}),
    ("ramp_running_slope_total", {"unit": "in"}),
    ("ramp_width", {"value": 999}),
    ("ramp_width", {"value": float("nan")}),
    ("ramp_width", {"value": float("inf")}),
    ("ramp_width", {"value": True}),
    ("ramp_width", {"value": "bad"}),
    ("ramp_width", {"value": 0}),
    ("lnd_length", {"value": -1}),
])
def test_invalid_measured_dimension_cannot_generate_quantities(field, update):
    evidence = with_item(evidence_for("standard"), f"8100001:{field}", **update)
    assert checked_ramps(evidence) == []
    assert run_planning(evidence) is None
    result = readiness(evidence)
    assert not result["geometry_permitted"]
    assert row(result["rows"], f"8100001:{field}")["status"] == "unresolved"


def test_zero_and_negative_recorded_slopes_remain_valid_percentages():
    for slope in (0, -6.4):
        evidence = with_item(evidence_for("standard"), "8100001:ramp_running_slope_total", value=slope)
        assert checked_ramps(evidence)[0]["slope_pct"] == abs(slope)


def test_a_dimension_with_no_record_is_unresolved():
    evidence = [e for e in evidence_for("standard") if e.key != "8100001:lnd_length"]
    gone = row(dimension_rows(evidence), "8100001:lnd_length")
    assert gone["status"] == "unresolved" and gone["source"] is None and gone["reason"] == "No record gives this dimension."
    assert run_planning(evidence) is None


def test_on_site_measurement_keeps_who_when_and_its_unit():
    corner = load_corner("missing_or_stale")
    entry = dict(key="8300001:ramp_length", field="ramp_length", value=5.5, unit="ft", date="2026-11-02", by="Pat Example", photo=None)
    rows = dimension_rows(build_evidence(corner, load_dictionary(corner), [entry]))
    length = row(rows, "8300001:ramp_length")
    assert length["status"] == "documented" and length["on_site"] and length["source"] == "Measured on site by Pat Example"
    assert length["date"] == "2026-11-02" and length["unit"] == "ft" and length["model_value"] == 5.5
    assert row(rows, "8300001:ramp_width")["status"] == "stale"  # One new measurement doesn't refresh the rest


def test_readiness_never_changes_the_evidence():
    evidence = evidence_for("real_test")
    before = [e.model_dump() for e in evidence]
    readiness(evidence)
    assert [e.model_dump() for e in evidence] == before


# Planning basis and revision
def test_planning_basis_cites_each_input_and_the_assumptions_used():
    plan = run_planning(evidence_for("standard"))
    basis = plan["basis"]
    assert plan["revision"] == basis["revision"] and basis["model_version"] == revision.MODEL_VERSION
    assert len(basis["inputs"]) == 10 and all(i["status"] == "documented" for i in basis["inputs"])
    width = next(i for i in basis["inputs"] if i["ramp_id"] == "8100002" and i["input"] == "width_ft")
    assert width["value"] == 4.5 and width["unit"] == "ft" and width["recorded_value"] == 54.0 and width["recorded_unit"] == "in"
    assert width["source"] == "Pedestrian Ramp Locations, ramp 8100002" and width["date"] == "2023-06-14"
    slope = next(i for i in basis["inputs"] if i["ramp_id"] == "8100002" and i["input"] == "slope_pct")
    assert slope["value"] == 7.1 and slope["unit"] == "%"
    assert {a["id"] for a in basis["assumptions"]} == {"slab_thickness_in", "dws_depth_ft", "curb_extra_length_ft", "removal_factor"}
    assert all(a["status"] == "assumed" and a["reason"] for a in basis["assumptions"])


def test_identical_inputs_give_identical_revisions():
    assert run_planning(evidence_for("standard"))["revision"] == run_planning(evidence_for("standard"))["revision"]
    # Where the record came from doesn't change the geometry, so it doesn't change the revision
    relabeled = with_item(evidence_for("standard"), "8100001:ramp_width", source="Another copy of the same record")
    assert run_planning(relabeled)["revision"] == run_planning(evidence_for("standard"))["revision"]


@pytest.mark.parametrize("key,value", [("8100001:ramp_width", 66.0), ("8100002:ramp_length", 6.25), ("8100001:lnd_length", 48.0), ("8100002:ramp_running_slope_total", 7.4)])
def test_changing_a_planning_dimension_changes_the_revision(key, value):
    before = run_planning(evidence_for("standard"))
    after = run_planning(with_item(evidence_for("standard"), key, value=value))
    assert after["revision"] != before["revision"]


def test_changing_an_effective_assumption_changes_the_revision(monkeypatch, tmp_path):
    before = run_planning(evidence_for("standard"))
    _with_assumption(monkeypatch, tmp_path, "slab_thickness_in", 6)
    after = run_planning(evidence_for("standard"))
    assert after["revision"] != before["revision"] and after["basis"]["inputs"] == before["basis"]["inputs"]
    assert next(a for a in after["basis"]["assumptions"] if a["id"] == "slab_thickness_in")["value"] == 6


def test_model_version_is_part_of_the_planning_revision(monkeypatch):
    before = run_planning(evidence_for("standard"))["revision"]
    monkeypatch.setattr(planning, "MODEL_VERSION", revision.MODEL_VERSION + 1)
    assert run_planning(evidence_for("standard"))["revision"] != before


def test_planning_is_permitted_exactly_as_before():
    for key in ("standard", "constrained"):
        evidence = evidence_for(key)
        plan = run_planning(evidence)
        assert plan and {"concept_label", "scene", "takeoff", "cost", "crew", "equipment", "safety_questions"} <= set(plan)
        assert readiness(evidence)["geometry_permitted"] and not readiness(evidence)["blockers"]
    for key in ("missing_or_stale", "real_test"):
        assert run_planning(evidence_for(key)) is None and not readiness(evidence_for(key))["geometry_permitted"]


# The preview keeps its revisions
@pytest.mark.parametrize("inputs,expected", [
    (GOOD, "c859c21d"), ({**GOOD, "length_ft": 8}, "97c39fa7"), ({**GOOD, "slope_pct": 0}, "4c89cc14"),
    (dict(width_ft=1, length_ft=30, landing_width_ft=20, landing_length_ft=1, slope_pct=8.33), "44dd8971"),
    ({k: str(v) for k, v in GOOD.items()}, "c859c21d"),
])
def test_preview_revisions_are_unchanged(inputs, expected):
    # Recorded from main before the revision function moved to cornerbrief/revision.py
    assert preview.build_preview(inputs)["revision"] == expected


def test_preview_and_planning_share_one_model_version():
    assert preview.BASIS_VERSION == revision.MODEL_VERSION == 2
