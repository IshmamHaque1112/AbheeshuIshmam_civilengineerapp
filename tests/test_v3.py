"""PRD v3: the two ending states, gated labels, site measurements and the adversarial suite (R28)."""
import base64, copy, json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import pytest
from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.field import validate_entries
from cornerbrief.guards import check_text
from cornerbrief.llm import AgentOutputError, OfflineClient, ReplayClient, get_client
from cornerbrief.models import SkepticOutput
from cornerbrief.orchestrator import CHECKS, STOP, analyze, rerun_with_field, run_corner
from cornerbrief.review_export import approve, to_markdown
from cornerbrief.rules import load_rules

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS", tmp_path / "runs")
    monkeypatch.setattr("cornerbrief.field.PHOTOS", tmp_path / "photos")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("SHOW_LABELS_AND_PLANS", raising=False)
    monkeypatch.delenv("EMAIL_ALLOWLIST", raising=False)


def verified_rules():
    return [dict(r, status="verified", reviewed_by="Pat Example", reviewed_on="2026-11-03") if r["status"] == "unreviewed" else r for r in load_rules()]


def assert_safe(run):
    """A safe ending has no label or plan on the page, in the saved run or in the download."""
    from cornerbrief.app import public
    assert run["label"] is None and run["planning"] is None
    assert "probably" not in json.dumps(run["brief"]).lower()
    shown = public(run)
    assert shown["label"] is None and shown["planning"] is None and shown["options"] == []
    text = to_markdown({**run, "approval": dict(reviewer="R", at="now", meaning="m")}).lower()
    assert "probably" not in text and "concept plan" not in text


@pytest.fixture(params=[False, True], ids=["labels off", "labels on"])
def label_setting(request, monkeypatch):
    if request.param:
        monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")


class Scripted(ReplayClient):
    def __init__(self, key="standard", skeptic=None):
        super().__init__(key)
        self.skeptic = skeptic

    def call(self, agent, attempt, system, payload, schema, tier="main"):
        if agent == "skeptic" and self.skeptic:
            return self.skeptic(schema), {}
        return super().call(agent, 0, system, payload, schema, tier)


def corner(**changes):
    c = copy.deepcopy(load_corner("standard"))
    c.update(changes)
    return c


# Demo corners: four expected states
@pytest.mark.parametrize("key,state", [("standard", CHECKS), ("constrained", CHECKS), ("missing_or_stale", STOP)])
def test_sample_corners_end_in_the_expected_state(key, state):
    run = run_corner(key)
    assert run["state"] == state
    assert_safe(run)


def test_labels_and_plans_stay_off_even_with_everything_reviewed():
    entries = [dict(key=f"corner:{f}", field=f, value=v, unit=u, date="2026-11-02", by="P E", photo=None) for f, v, u in
               [("sidewalk_width", 10.0, "ft"), ("legal_grade", 1.0, "percent"), ("ramp_type", "C1 perpendicular", None), ("sidewalk_transverse_slope", 2.0, "percent")]]
    run = analyze(load_corner("standard"), client=ReplayClient("standard"), rules=verified_rules(), field=entries)
    assert run["state"] == CHECKS
    assert_safe(run)


def test_turning_labels_on_is_not_enough_without_reviewed_rules(monkeypatch):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    assert_safe(run_corner("standard"))


def test_writer_label_is_rejected_while_labels_are_off():
    assert check_text("This is probably custom.", {}, labels_off=True)
    assert not check_text("This is probably custom.", {}, labels_off=False)


def test_supported_results_show_the_quote():
    results = [o for o in run_corner("standard")["rule_results"] if o["preview"]]
    assert results and all(o["section"] and o["quote"] and o["url"] for o in results)


# R28 adversarial suite
@pytest.mark.usefixtures("label_setting")
def test_r28_1_missing_survey_or_construction_dates():
    no_survey = corner()
    no_survey["locations"][0]["geocyclora"] = None
    no_built = corner(progress=[dict(load_corner("standard")["progress"][0], construc_1=None)])
    for c in (no_survey, no_built):
        run = analyze(c, client=ReplayClient("standard"))
        assert run["state"] == STOP
        assert_safe(run)


@pytest.mark.usefixtures("label_setting")
@pytest.mark.parametrize("road", ["not_recorded", "state", None])
def test_r28_2_unknown_road_owner(road):
    c = corner()
    c["context"] = {**c["context"], "road_control": road}
    run = analyze(c, client=ReplayClient("standard"))
    assert run["state"] == STOP and any("road owner" in p for p in run["problems"])
    assert_safe(run)


@pytest.mark.parametrize("change", [
    dict(progress=[dict(cornerid=123, construc_2="Constructed", construc_1="2021/01/01")]),
    dict(complaints=[dict(cmt_corner_id=123, complaint_id="X", complaint_date="2025-01-01")]),
])
@pytest.mark.usefixtures("label_setting")
def test_r28_3_unmatched_corner_ids(change):
    run = analyze(corner(**change), client=ReplayClient("standard"))
    assert run["state"] == STOP
    assert_safe(run)


@pytest.mark.usefixtures("label_setting")
def test_r28_4_undocumented_units(monkeypatch):
    dictionary = copy.deepcopy(load_dictionary(corner(data_kind="NYC Open Data")))
    for field in dictionary["fields"].values():
        field["unit_status"] = "assumed"
    monkeypatch.setattr("cornerbrief.orchestrator.load_dictionary", lambda _: dictionary)
    run = analyze(corner(data_kind="NYC Open Data"), client=ReplayClient("standard"))
    assert run["state"] == STOP and any("units" in p for p in run["problems"])
    assert all(o["result"] in ("unknown", "not applicable") and o["preview"] is None for o in run["rule_results"])
    assert_safe(run)


@pytest.mark.usefixtures("label_setting")
def test_r28_5_exceeded_limit_with_no_obstacle():
    c = corner()
    c["locations"][0]["ramp_running_slope_total"] = 9.5
    run = analyze(c, client=ReplayClient("standard"), rules=verified_rules())
    assert run["state"] == STOP and "above a limit" in run["state_reason"]
    assert_safe(run)


@pytest.mark.usefixtures("label_setting")
def test_r28_6_malformed_skeptic_output():
    def bad(schema):
        raise AgentOutputError("invalid")
    for key in ("standard", "constrained"):  # The complex corner must stop too
        run = analyze(load_corner(key), client=Scripted(key, bad))
        assert run["state"] == STOP and run["review_status"] == "incomplete"
        assert_safe(run)


@pytest.mark.usefixtures("label_setting")
def test_r28_7_exhausted_retries():
    run = analyze(load_corner("constrained"), client=Scripted("constrained", lambda schema: (SkepticOutput(verdict="rework", challenges=[]))))
    assert run["retry_limit_hit"] and run["state"] == STOP
    assert_safe(run)


@pytest.mark.usefixtures("label_setting")
def test_r28_8_unreviewed_rules(monkeypatch):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    run = run_corner("standard")
    numeric = [o for o in run["rule_results"] if o["preview"]]
    assert numeric and all(o["result"] == "unknown" for o in numeric)
    assert_safe(run)


@pytest.mark.usefixtures("label_setting")
def test_r28_9_conflicting_evidence():
    base = load_corner("standard")
    two_statuses = corner(progress=base["progress"] + [dict(base["progress"][0], construc_2="Complex Planned Construction", construc_1=None)])
    dup = corner()
    dup["locations"] = dup["locations"] + [dict(dup["locations"][0], ramp_width=30)]
    for c in (two_statuses, dup):
        run = analyze(c, client=ReplayClient("standard"))
        assert run["state"] == STOP and any("disagree" in p for p in run["problems"])
        assert_safe(run)


@pytest.mark.usefixtures("label_setting")
def test_r28_10_switching_between_corners_leaks_no_state():
    expected = {k: run_corner(k) for k in ("standard", "constrained", "missing_or_stale")}
    keys = list(expected) * 8
    with ThreadPoolExecutor(8) as pool:
        runs = list(pool.map(run_corner, keys))
    for key, run in zip(keys, runs):
        want = expected[key]
        assert run["corner"]["key"] == key and run["state"] == want["state"] and run["brief"] == want["brief"]
        assert_safe(run)
        assert run["rule_results"] == want["rule_results"] and run["site_visit"] == want["site_visit"]


@pytest.mark.usefixtures("label_setting")
def test_r28_10_site_measurements_stay_with_their_corner():
    first = run_corner("standard")
    rerun_with_field(first, [dict(key="corner:sidewalk_width", value=10)], "2026-11-02", "Pat Example")
    again = run_corner("standard")
    assert again["field_measurements"] == [] and again["changes"] is None
    assert not run_corner("constrained")["field_measurements"]


# R30 and R31: site measurements and rerun
def stale_entries(run):
    values = dict(ramp_running_slope_total=6, ramp_cross_slope=1.5, ramp_width=60, ramp_length=6, lnd_width=60, lnd_length=60, lnd_cross_slope=1.5, curb_reveal=0.25,
                  gutter_slope=1.5, counter_slope=3, ramp_right_flare=8, ramp_left_flare=8)
    return [dict(key=f["key"], value=values[f["field"]]) for f in run["field_inputs"] if f["field"] in values]


def test_field_inputs_list_what_the_site_visit_needs():
    run = run_corner("missing_or_stale")
    fields = {f["field"] for f in run["field_inputs"]}
    assert {"ramp_width", "curb_reveal", "sidewalk_width", "ramp_type"} <= fields
    assert all(f["label"] in ("missing", "stale", "assumed") for f in run["field_inputs"])


def test_rerun_moves_a_stopped_corner_and_reports_changes():
    first = run_corner("missing_or_stale")
    assert first["state"] == STOP
    run = rerun_with_field(first, stale_entries(first), "2026-11-02", "Pat Example")
    assert run["state"] == CHECKS and run["previous_run_id"] == first["id"]
    width = next(e for e in run["evidence"] if e["field"] == "ramp_width")
    assert width["on_site"] and width["label"] == "measured" and width["date"] == "2026-11-02" and "Pat Example" in width["source"]
    c = run["changes"]
    assert c["state_before"] == STOP and c["state_after"] == CHECKS and c["inputs"] and c["results"] and c["site_visit_done"]
    assert_safe(run)


def test_rerun_needs_a_new_release_and_doesnt_reuse_the_saved_review():
    first = approve(run_corner("standard"), "R")
    run = rerun_with_field(first, [dict(key="corner:sidewalk_width", value=10)], "2026-11-02", "Pat Example")
    assert run["approval"] is None and run["mode"] == "offline, no agents" and run["review_status"] == "not run"
    assert "wasn't reused" in run["state_reason"]
    text = to_markdown(approve(run, "R"))
    assert "What changed in this rerun" in text and "Measured on site" in text and "Pat Example" in text and "measured on site" in text


def test_entries_accumulate_across_reruns():
    first = run_corner("standard")
    second = rerun_with_field(first, [dict(key="corner:sidewalk_width", value=10)], "2026-11-02", "A B")
    third = rerun_with_field(second, [dict(key="corner:legal_grade", value=1)], "2026-11-03", "A B")
    assert {e["key"] for e in third["field_measurements"]} == {"corner:sidewalk_width", "corner:legal_grade"}
    assert len([c for c in third["changes"]["inputs"]]) == 1


def test_measurement_before_the_rebuild_is_still_stale():
    first = run_corner("missing_or_stale")
    run = rerun_with_field(first, stale_entries(first), "2025-01-01", "Pat Example")
    assert run["state"] == STOP
    assert next(e for e in run["evidence"] if e["field"] == "ramp_width")["label"] == "stale"


def _road(value):
    c = corner()
    c["context"] = {**c["context"], "road_control": "not_recorded"}
    entry = dict(key="corner:road_control", field="road_control", value=value, unit=None, date="2026-11-02", by="A B", photo=None)
    return analyze(c, client=OfflineClient(), field=[entry])


def test_unrecorded_road_owner_can_be_confirmed_on_site():
    first = analyze(corner(context=dict(load_corner("standard")["context"], road_control="not_recorded")), client=ReplayClient("standard"))
    assert any(f["key"] == "corner:road_control" for f in first["field_inputs"])
    assert _road("state")["state"] == STOP
    assert _road("city")["state"] == CHECKS


def test_real_corner_stays_unknown_when_site_values_are_added():
    c = corner(data_kind="NYC Open Data", key="standard")
    c["context"]["road_control"] = "not_recorded"
    run = analyze(c, client=OfflineClient(), field=[dict(key="corner:sidewalk_width", field="sidewalk_width", value=10.0, unit="ft", date="2026-11-02", by="A B", photo=None)])
    assert run["state"] == STOP and any("road owner" in p for p in run["problems"])
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])


def test_saved_replies_are_not_used_after_inputs_change():
    assert isinstance(get_client(load_corner("standard"), inputs_changed=True), OfflineClient)
    assert isinstance(get_client(load_corner("standard")), ReplayClient)


ALLOWED = [dict(key="r:ramp_width", field="ramp_width", unit="in"), dict(key="corner:ramp_type", field="ramp_type", unit=None)]


@pytest.mark.parametrize("raw,on,by,message", [
    ([dict(key="r:ramp_width", value=60)], "2026-11-02", " ", "name"),
    ([dict(key="r:ramp_width", value=60)], "11/02/2026", "A B", "date"),
    ([dict(key="r:ramp_width", value=60)], "2026-11-05", "A B", "future"),
    ([], "2026-11-02", "A B", "at least one"),
    ([dict(key="other", value=60)], "2026-11-02", "A B", "isn't an input"),
    ([dict(key="r:ramp_width", value="wide")], "2026-11-02", "A B", "number"),
    ([dict(key="r:ramp_width", value=999)], "2026-11-02", "A B", "plausible"),
    ([dict(key="r:ramp_width", value="nan")], "2026-11-02", "A B", "plausible"),
    ([dict(key="corner:ramp_type", value="Big")], "2026-11-02", "A B", "choices"),
    ([dict(key="r:ramp_width", value=60, photo=dict(name="x", data=base64.b64encode(b"not an image").decode()))], "2026-11-02", "A B", "JPEG"),
])
def test_bad_entries_are_refused(raw, on, by, message):
    with pytest.raises(ValueError, match=message):
        validate_entries(raw, ALLOWED, on, by, today=date(2026, 11, 3))


def test_photo_is_saved_and_attached(tmp_path):
    first = run_corner("standard")
    run = rerun_with_field(first, [dict(key="corner:sidewalk_width", value=10, photo=dict(name="a.png", data=f"data:image/png;base64,{PNG}"))], "2026-11-02", "A B")
    item = next(e for e in run["evidence"] if e["field"] == "sidewalk_width")
    assert item["photo"].endswith(".png") and (tmp_path / "photos" / item["photo"]).exists()
    kept = rerun_with_field(run, [dict(key="corner:sidewalk_width", value=11)], "2026-11-02", "A B")
    assert next(e for e in kept["evidence"] if e["field"] == "sidewalk_width")["photo"] == item["photo"]


# README user stories
def test_story_1_records_show_label_counts():
    run = run_corner("standard")
    assert run["evidence_counts"] == dict(__import__("collections").Counter(e["label"] for e in run["evidence"]))
    assert "Input labels:" in to_markdown(approve(run, "R"))


def test_story_4_every_calculated_check_traces_to_its_source():
    for key in ("standard", "constrained"):
        calculated = [o for o in run_corner(key)["rule_results"] if o["preview"] or o["math"]]
        assert calculated and all(o["title"] and o["section"] and o["url"] and o["quote"] for o in calculated)


def test_story_4_missing_evidence_stops_that_check_even_when_the_corner_continues():
    run = run_corner("standard")
    assert run["state"] == CHECKS
    stopped = [o for o in run["rule_results"] if o["evidence_stop"]]
    assert stopped and all(o["result"] == "unknown" and not o["preview"] for o in stopped)
    assert not any(o["evidence_stop"] for o in run["rule_results"] if o["preview"])
    assert "stop: evidence still needed" in to_markdown(approve(run, "R"))
    assert all(o["evidence_stop"] for o in run_corner("missing_or_stale")["rule_results"] if o["parameter"] and o["result"] == "unknown" and o["section"] and "source text" not in o["reason"] and "no numeric" not in o["reason"])


def test_story_3_a_measurement_removes_its_stop():
    first = run_corner("standard")
    assert any(o["parameter"] == "sidewalk_transverse_slope" and o["evidence_stop"] for o in first["rule_results"])
    run = rerun_with_field(first, [dict(key="corner:sidewalk_transverse_slope", value=2)], "2026-11-02", "A B")
    assert not any(o["parameter"] == "sidewalk_transverse_slope" and o["evidence_stop"] for o in run["rule_results"])
    assert any(r["after"] == "no conflict found" for r in run["changes"]["results"])
