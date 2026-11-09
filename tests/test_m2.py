"""Roadmap M2: cited dimensions, one shared revision with recalculation marking, and a draft sequence with every unknown kept unknown."""
import copy
import json

import pytest

from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.evidence import build_evidence
from cornerbrief.field import compare_runs
from cornerbrief.llm import OfflineClient
from cornerbrief.orchestrator import analyze
from cornerbrief.planning import run_planning
from cornerbrief.preview import build_preview
from cornerbrief.review_export import approve, to_markdown
from cornerbrief.work_plan import MISSING_INPUTS, build_work_plan, plan_status

DEFAULTS = dict(width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=5, slope_pct=6)


def planning_for(key="standard"):
    corner = load_corner(key)
    return run_planning(build_evidence(corner, load_dictionary(corner)))


def test_every_dimension_cites_its_record():  # M2.1
    plan = planning_for()
    assert plan and len(plan["dimensions"]) == len(plan["basis"]["inputs"])
    for d in plan["dimensions"]:
        assert d["citation"] and "no record" not in d["citation"] and d["label"].split(": ")[1].split()[-1] in ("ft", "%")
    assert any(" in from " in d["citation"] for d in plan["dimensions"])


def test_draft_and_quantities_share_one_revision():  # M2.2
    plan = planning_for()
    assert plan["work_plan"]["built_from_revision"] == plan["revision"] == plan["basis"]["revision"]
    assert plan_status(plan["work_plan"], plan["revision"])["state"] == "current"


def test_changed_dimension_marks_the_draft_for_recalculation():  # M2.2
    first = build_preview(DEFAULTS)
    second = build_preview(dict(DEFAULTS, width_ft=6))
    assert first["revision"] != second["revision"]
    status = plan_status(first["work_plan"], second["revision"])
    assert status["state"] == "needs recalculation" and first["revision"] in status["message"] and second["revision"] in status["message"]
    assert plan_status(second["work_plan"], second["revision"])["state"] == "current"
    assert plan_status(None, second["revision"])["state"] == "none"


def test_sequence_has_the_seven_steps_with_unknown_durations_and_resources():  # M2.3
    plan = build_preview(DEFAULTS)["work_plan"]
    assert [s["id"] for s in plan["steps"]] == ["sawcut", "demolition", "forming", "pour", "cure", "warning_surface", "restoration"]
    assert all(s["duration"] == "unknown" and s["people"] == "unknown" and s["equipment_availability"] == "unknown" for s in plan["steps"])
    assert plan["status"] == "draft" and "isn't a schedule" in plan["label"]
    assert [s["after"] for s in plan["steps"]][1:] == [s["id"] for s in plan["steps"]][:-1]


def test_quantities_come_from_the_takeoff():
    preview = build_preview(DEFAULTS)
    takeoff = {q["id"]: q["qty"] for q in preview["quantities"]}
    pour = next(s for s in preview["work_plan"]["steps"] if s["id"] == "pour")
    assert pour["quantities"][0]["qty"] == takeoff["concrete_volume"]


def test_missing_inputs_are_listed_and_nothing_is_filled_from_trade_data():  # M2.4
    plan = build_preview(DEFAULTS)["work_plan"]
    assert plan["missing_inputs"] == MISSING_INPUTS and len(MISSING_INPUTS) >= 6
    steps = json.dumps(plan["steps"]).lower()
    assert not any(word in steps for word in ("hours", "days", "minutes", "rate:"))
    text = json.dumps(plan).lower()
    assert not any(word in text for word in ("$", "crew", "labor", "approved", "compliant", "safe"))


def test_the_draft_has_no_dollars_even_with_sample_rates():  # M2.5
    text = json.dumps(planning_for()["work_plan"])
    assert "$" not in text and "cost" not in text.lower()


def test_rerun_with_a_new_revision_says_the_old_draft_needs_recalculation():
    before = dict(planning=dict(revision="aaaa1111"), evidence=[], rule_results=[], site_visit=[], state="x")
    after = dict(before, planning=dict(revision="bbbb2222"))
    note = compare_runs(before, after)["plan_note"]
    assert "aaaa1111" in note and "bbbb2222" in note and "needs recalculation" in note
    assert compare_runs(before, copy.deepcopy(before))["plan_note"] is None
    assert "no longer applies" in compare_runs(before, dict(before, planning=None))["plan_note"]


def test_packet_shows_readiness_for_the_real_corner():
    run = analyze(load_corner("real_test"), client=OfflineClient(), save=False)
    r = run["readiness"]
    assert len(r["rows"]) == 10 and r["counts"]["assumed"] == 10 and not r["geometry_permitted"]
    text = to_markdown(approve(run, "R"))
    assert "## Concept model inputs" in text and "0 documented, 10 assumed" in text


def test_ramp_type_names_dots_category_without_choosing_an_h1011_type():
    run = analyze(load_corner("real_test"), client=OfflineClient(), save=False)
    item = next(e for e in run["evidence"] if e["field"] == "ramp_type")
    assert item["label"] == "missing" and item["value"] is None and '"Ramp"' in item["reason"]


@pytest.mark.parametrize("bad", [dict(DEFAULTS, width_ft=0), dict(DEFAULTS, slope_pct="x")])
def test_bad_dimensions_build_no_draft(bad):
    with pytest.raises(ValueError):
        build_preview(bad)


def test_build_work_plan_ignores_unknown_quantity_ids():
    takeoff = dict(items=[dict(id="slab_area", label="Slab", qty=10.0, unit="sf")], assumptions=[], exclusions=[])
    plan = build_work_plan(takeoff, "r1")
    assert next(s for s in plan["steps"] if s["id"] == "forming")["quantities"] == [dict(label="Slab", qty=10.0, unit="sf")]
    assert next(s for s in plan["steps"] if s["id"] == "sawcut")["quantities"] == []
