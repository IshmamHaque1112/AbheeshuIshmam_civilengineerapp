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


def _with_assumption(monkeypatch, tmp_path, key, value):
    """Point the parts kit at a copy of the assumptions file with one value changed."""
    import yaml
    from cornerbrief import parts_kit
    data = yaml.safe_load((parts_kit.DATA / "kit_assumptions.yaml").read_text(encoding="utf-8"))
    data[key]["value"] = value
    (tmp_path / "kit_assumptions.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(parts_kit, "DATA", tmp_path)


@pytest.mark.parametrize("key,value,item", [
    ("slab_thickness_in", 6, "concrete_volume"),
    ("dws_depth_ft", 1, "dws_area"),
    ("curb_extra_length_ft", 6, "curb_length"),
    ("removal_factor", 1.5, "removal_area"),
])
def test_changed_assumption_changes_quantities_and_revision(monkeypatch, tmp_path, key, value, item):
    # Same dimensions, different assumption: the old revision must not keep pointing at new quantities
    before = preview.build_preview(GOOD)
    _with_assumption(monkeypatch, tmp_path, key, value)
    after = preview.build_preview(GOOD)
    assert quantity(after, item) != quantity(before, item)
    assert after["revision"] != before["revision"] and after["inputs"] == before["inputs"]
    assert after["revision"] == preview.build_preview(GOOD)["revision"]


def test_basis_version_is_part_of_the_revision(monkeypatch):
    before = preview.build_preview(GOOD)
    assert before["basis_version"] == preview.BASIS_VERSION
    monkeypatch.setattr(preview, "BASIS_VERSION", preview.BASIS_VERSION + 1)
    assert preview.build_preview(GOOD)["revision"] != before["revision"]


def test_input_basis_separates_synthetic_assumed_and_unknown():
    basis = preview.build_preview({**GOOD, "width_ft": 7.5})["input_basis"]
    assert "Ramp width 7.5 ft" in basis["synthetic"] and "Running slope 6 %" in basis["synthetic"]
    assert "Slab thickness 4 in" in basis["assumed"]
    # Inputs the sandbox doesn't model are listed as unknown, never given a value
    assert "Sidewalk width" in basis["unknown"] and not any(ch.isdigit() for item in basis["unknown"] for ch in item)


@pytest.mark.parametrize("field,value,item,expected", [
    ("width_ft", 8, "slab_area", 73.0),           # 8 x 6 + 5 x 5
    ("width_ft", 8, "dws_area", 16.0),            # 8 x 2
    ("width_ft", 8, "curb_length", 12.0),         # 8 + 4 extra
    ("landing_width_ft", 7, "slab_area", 65.0),   # 5 x 6 + 7 x 5
    ("landing_length_ft", 3, "slab_area", 45.0),  # 5 x 6 + 5 x 3
    ("length_ft", 1.5, "dws_area", 7.5),          # The warning surface can't be deeper than the ramp
])
def test_each_dimension_moves_its_own_quantities(field, value, item, expected):
    assert quantity(preview.build_preview({**GOOD, field: value}), item) == expected


def test_slope_changes_rise_and_geometry_but_not_plan_area():
    flat, steep = preview.build_preview(GOOD), preview.build_preview({**GOOD, "slope_pct": 12})
    assert steep["rise_in"] == 8.6 and quantity(steep, "slab_area") == quantity(flat, "slab_area")
    top = lambda r: max(z for f in r["scene"]["faces"] for _, _, z in f["p"])
    assert top(steep) == pytest.approx(2 * top(flat))


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
