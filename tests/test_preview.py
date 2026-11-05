"""The 3D preview is useful, and it stays separate from evidence."""
import json
import pytest
from cornerbrief import preview
from cornerbrief.data_loader import list_corners, load_corner
from cornerbrief.llm import ReplayClient
from cornerbrief.orchestrator import analyze
from test_web_and_fetch import call, server  # noqa: F401

GOOD = dict(width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=5, slope_pct=6)


def quantity(result, item):
    return next(q["qty"] for q in result["quantities"] if q["id"] == item)


def test_known_dimensions_give_hand_checked_quantities():
    result = preview.build_preview(GOOD)
    assert quantity(result, "slab_area") == 55.0  # 5 x 6 + 5 x 5
    assert quantity(result, "dws_area") == 10.0   # 5 x 2
    assert quantity(result, "ramp_count") == 1
    assert result["rise_in"] == 4.3               # 6 ft x 6% = 4.32 in
    assert result["kind"] == "synthetic exploration" and "isn\'t field evidence" in result["notice"]


def test_changing_a_dimension_changes_geometry_quantities_and_revision():
    first, second = preview.build_preview(GOOD), preview.build_preview({**GOOD, "length_ft": 8})
    assert quantity(second, "slab_area") == 65.0
    assert quantity(second, "concrete_volume") > quantity(first, "concrete_volume")
    assert first["revision"] != second["revision"] and first["scene"]["faces"] != second["scene"]["faces"]
    assert "Ramp length 8 ft" in [d["label"] for d in second["dimensions"]]
    assert first["revision"] in first["review_note"]


def test_same_dimensions_keep_the_same_revision():
    assert preview.build_preview(GOOD)["revision"] == preview.build_preview({k: str(v) for k, v in GOOD.items()})["revision"]


@pytest.mark.parametrize("change,field", [
    (dict(width_ft=""), "width_ft"), (dict(width_ft=None), "width_ft"), (dict(length_ft=-1), "length_ft"), (dict(length_ft=0), "length_ft"),
    (dict(slope_pct=99), "slope_pct"), (dict(landing_width_ft="wide"), "landing_width_ft"), (dict(width_ft=True), "width_ft"),
    (dict(width_ft=float("nan")), "width_ft"), (dict(width_ft=float("inf")), "width_ft"), (dict(cost=5), "cost"),
])
def test_bad_dimensions_give_feedback_and_no_model(change, field):
    with pytest.raises(ValueError) as exc:
        preview.build_preview({**GOOD, **change})
    assert field in exc.value.problems


def test_missing_dimension_isnt_filled_in():
    raw = dict(GOOD)
    del raw["width_ft"]
    with pytest.raises(ValueError) as exc:
        preview.build_preview(raw)
    assert "width_ft" in exc.value.problems


def test_every_output_states_its_units_and_source():
    result = preview.build_preview(GOOD)
    assert all(i["unit"] and i["provenance"] == "synthetic, typed in" for i in result["inputs"])
    assert all(q["unit"] and "provisional" in q["basis"] and "synthetic" in q["basis"] for q in result["quantities"])
    assert all("ft" in d["label"] or "in" in d["label"] for d in result["dimensions"])


def test_preview_has_no_dollars_crew_rule_results_or_permission():
    text = json.dumps(preview.build_preview(GOOD)).lower()
    for word in ("$", "cost", "crew", "labor", "probably", "limit exceeded", "no conflict", "compliant", "approved"):
        assert word not in text, word


def test_warning_surface_and_ramp_dont_overlap():
    scene = preview.build_preview(GOOD)["scene"]
    colors = [f["c"] for f in scene["faces"]]
    assert colors.count("#f2c200") == 1 and colors.count("#b9bdb9") == 1
    short = preview.build_preview({**GOOD, "length_ft": 1.5})["scene"]
    assert [f["c"] for f in short["faces"]].count("#b9bdb9") == 0


def test_preview_cant_touch_packets(server, tmp_path):
    import cornerbrief.orchestrator as orch
    before_runs = sorted(p.name for p in orch.RUNS.glob("*.json"))
    before_corners = list_corners()
    expected = analyze(load_corner("standard"), client=ReplayClient("standard"), save=False)
    status, body = call(server + "/api/preview", GOOD)
    assert status == 200 and json.loads(body)["revision"]
    assert sorted(p.name for p in orch.RUNS.glob("*.json")) == before_runs
    assert list_corners() == before_corners
    after = analyze(load_corner("standard"), client=ReplayClient("standard"), save=False)
    for field in ("state", "evidence", "rule_results", "label", "planning", "field_measurements"):
        assert after[field] == expected[field]
    assert not any(c["key"].startswith("synthetic") for c in before_corners)


def test_preview_route_reports_problems_by_field(server):
    status, body = call(server + "/api/preview", {**GOOD, "width_ft": -1})
    out = json.loads(body)
    assert status == 400 and "width_ft" in out["problems"]
    status, body = call(server + "/api/preview")
    assert status == 200 and len(json.loads(body)["fields"]) == 5
