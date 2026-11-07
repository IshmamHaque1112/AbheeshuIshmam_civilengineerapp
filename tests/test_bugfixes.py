"""Regression tests for bugs found in the November 4 code review."""
import copy, importlib.util, json, sys, types
from pathlib import Path
import pytest
from cornerbrief import config
from cornerbrief.applicability import resolve
from cornerbrief.checker import check_value, find_conflicts
from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.evidence import build_evidence, data_sufficient
from cornerbrief.field import compare_runs, validate_entries
from cornerbrief.guards import check_text
from cornerbrief.llm import AgentOutputError, LiveClient, OfflineClient, ReplayClient, get_client
from cornerbrief.models import BriefWriterOutput, EvidenceItem, RecordsOutput, SkepticOutput
from cornerbrief.orchestrator import CHECKS, STOP, analyze, rerun_with_field, run_corner, save_run
from cornerbrief.review_export import approve, presented, to_markdown
from cornerbrief.rules import RuleError, load_precedence, load_rules, validate_rule
from cornerbrief.site_visit import build_list


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS", tmp_path / "runs")
    monkeypatch.setattr("cornerbrief.field.PHOTOS", tmp_path / "photos")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("SHOW_LABELS_AND_PLANS", raising=False)


ENTRIES = [dict(key=f"corner:{f}", field=f, value=v, unit=u, date="2026-11-02", by="Pat Example", photo=None) for f, v, u in
           [("sidewalk_width", 10.0, "ft"), ("legal_grade", 1.0, "percent"), ("ramp_type", "C1 perpendicular", None), ("sidewalk_transverse_slope", 2.0, "percent")]]


def reviewed_rules(drop_sources=True):
    rules = [dict(r, status="verified", reviewed_by="Pat Example", reviewed_on="2026-11-03") if r["status"] == "unreviewed" else r for r in load_rules()]
    return [r for r in rules if r["status"] != "needs_source"] if drop_sources else rules


@pytest.fixture
def reviewed_precedence(monkeypatch):
    items = {k: dict(v, reviewed_by="Pat Example") for k, v in load_precedence().items()}
    monkeypatch.setattr("cornerbrief.orchestrator.load_precedence", lambda: items)


class Writer(ReplayClient):
    def __init__(self, key="standard", **agents):
        super().__init__(key)
        self.agents = agents

    def call(self, agent, attempt, system, payload, schema, tier="main"):
        if agent in self.agents:
            return self.agents[agent](schema), {}
        return super().call(agent, 0, system, payload, schema, tier)


# Label gate
def test_label_appears_only_with_full_rule_coverage(monkeypatch, reviewed_precedence):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    corner = load_corner("standard")
    run = analyze(corner, client=ReplayClient("standard"), rules=reviewed_rules(), field=ENTRIES)
    assert run["label"] == "probably standard" and run["planning"]
    missing_source = analyze(corner, client=ReplayClient("standard"), rules=reviewed_rules(drop_sources=False), field=ENTRIES)
    assert missing_source["label"] is None and missing_source["planning"] is None


def test_label_needs_reviewed_precedence(monkeypatch):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    run = analyze(load_corner("standard"), client=ReplayClient("standard"), rules=reviewed_rules(), field=ENTRIES)
    assert run["label"] is None and run["planning"] is None


def test_writer_cant_state_a_label_the_gate_refused(monkeypatch):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    client = Writer(brief_writer=lambda schema: schema(summary="This is probably standard.", findings_narrative="x"))
    run = analyze(load_corner("standard"), client=client)
    assert run["label"] is None and "probably" not in run["brief"]["summary"].lower()


def test_saved_label_and_plan_disappear_when_the_setting_is_off(monkeypatch, reviewed_precedence):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    run = approve(analyze(load_corner("standard"), client=ReplayClient("standard"), rules=reviewed_rules(), field=ENTRIES), "R")
    assert run["label"] and "probably standard" in to_markdown(run)
    monkeypatch.delenv("SHOW_LABELS_AND_PLANS")
    shown = presented(run)
    assert shown["label"] is None and shown["planning"] is None and shown["options"] == []
    text = to_markdown(run)
    assert "probably standard" not in text and "Concept plan" not in text and "Likely options" not in text


# Review and agent text
def test_pass_with_a_rework_challenge_isnt_finished():
    bad = lambda schema: schema(verdict="pass", challenges=[dict(claim="x", issue="Fix this.", severity="rework")])
    run = analyze(load_corner("standard"), client=Writer(skeptic=bad))
    assert run["review_status"] == "incomplete" and run["state"] == STOP


@pytest.mark.parametrize("text", ["Proceed with construction.", "It is ready to build.", "The corner meets the code.", "This ramp conforms.", "It is permitted.", "The work is acceptable.", "You can go ahead."])
def test_permission_language_is_rejected(text):
    assert check_text(text, {})


def test_rejected_output_doesnt_repeat_the_banned_word_in_the_packet():
    client = Writer(brief_writer=lambda schema: schema(summary="This corner is compliant.", findings_narrative="x"))
    run = analyze(load_corner("standard"), client=client)
    assert run["rejections"] and "compliant" not in to_markdown(approve(run, "R")).lower().replace("not a compliance", "")


def test_stopped_corner_keeps_the_road_owner_reason():
    corner = copy.deepcopy(load_corner("standard"))
    corner["context"]["road_control"] = "not_recorded"
    run = analyze(corner, client=ReplayClient("standard"))
    assert any("road" in o["reason"].lower() or "state" in o["reason"].lower() for o in run["rule_results"] if o["rule_id"] == "NYC-ADMIN-19-112-SLOPE")


# Settings and live agents
def test_env_values_can_be_quoted(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text('QUOTED_ONE="abc"\nQUOTED_TWO=\'def\'\n', encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.delenv("QUOTED_ONE", raising=False)
    monkeypatch.delenv("QUOTED_TWO", raising=False)
    config.load_env()
    import os
    assert os.environ.pop("QUOTED_ONE") == "abc" and os.environ.pop("QUOTED_TWO") == "def"


def _fake_anthropic(monkeypatch, create):
    module = types.ModuleType("anthropic")
    module.Anthropic = lambda: types.SimpleNamespace(messages=types.SimpleNamespace(create=create))
    monkeypatch.setitem(sys.modules, "anthropic", module)
    monkeypatch.setenv("MAIN_MODEL", "m")
    monkeypatch.setenv("FAST_MODEL", "f")


def test_live_needs_demo_mode_set_to_false(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert isinstance(get_client(load_corner("standard")), ReplayClient)


def test_live_api_failure_is_an_agent_error(monkeypatch, tmp_path):
    def fail(**kw):
        raise ConnectionError("no route")
    _fake_anthropic(monkeypatch, fail)
    monkeypatch.setattr("cornerbrief.llm.CACHE", tmp_path)
    with pytest.raises(AgentOutputError):
        LiveClient().call("records", 0, "s", {}, RecordsOutput)


def test_live_failure_stops_the_corner_instead_of_crashing(monkeypatch, tmp_path):
    def fail(**kw):
        raise ConnectionError("no route")
    _fake_anthropic(monkeypatch, fail)
    monkeypatch.setattr("cornerbrief.llm.CACHE", tmp_path)
    run = analyze(load_corner("standard"), client=LiveClient())
    assert run["state"] == STOP and run["review_status"] == "incomplete"


def test_invalid_live_output_isnt_cached(monkeypatch, tmp_path):
    calls = []
    def create(**kw):
        calls.append(1)
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="not json")], usage=types.SimpleNamespace(input_tokens=1, output_tokens=1))
    _fake_anthropic(monkeypatch, create)
    monkeypatch.setattr("cornerbrief.llm.CACHE", tmp_path)
    client = LiveClient()
    for _ in range(2):
        with pytest.raises(AgentOutputError):
            client.call("records", 0, "s", {}, RecordsOutput)
    assert len(calls) == 2


def test_missing_replay_file_is_an_agent_error(tmp_path):
    client = ReplayClient("standard")
    client.dir = tmp_path
    with pytest.raises(AgentOutputError):
        client.call("skeptic", 0, "s", {}, SkepticOutput)


# Rule math and rule files
@pytest.mark.parametrize("change", [dict(unit=None), dict(unit="yards"), dict(limit="eight"), dict(operator="range", limit=8), dict(operator="range", limit=dict(min=1))])
def test_malformed_numeric_rule_fails_to_load(change):
    rule = next(r for r in load_rules() if r["id"] == "NYC-ADMIN-19-112-SLOPE")
    with pytest.raises(RuleError):
        validate_rule({**rule, **change})


def _item(value, unit, field="ramp_width"):
    return EvidenceItem(key="1:x", ramp_id="1", field=field, value=value, unit=unit, unit_documented=True, label="measured", source="s")


def test_exact_foot_limit_has_no_rounding_error():
    for inches in range(1, 400):
        for operator in ("max", "min"):
            rule = dict(id="r", title="t", parameter="ramp_width", authority_type="a", section="s", url="u", quote="q", unit="ft", operator=operator, limit=inches / 12)
            assert check_value(rule, _item(inches, "in")).result == "no conflict found"


def test_math_doesnt_round_a_value_onto_its_limit():
    rule = dict(id="r", title="t", parameter="slope", authority_type="a", section="s", url="u", quote="q", unit="percent", operator="max", limit=8.3)
    out = check_value(rule, _item(8.3001, "percent", "slope"))
    assert out.result == "limit exceeded" and "8.3001" in out.math


def test_conflict_compares_feet_with_an_inch_maximum():
    rules = [dict(id=i, title="t", jurisdiction="nyc", applies_to=["corner_ramp_row"], authority_type="a", parameter="ramp_length", operator="max", limit=limit, unit=unit, stage="general", section="s", url="u", quote="q", status="unreviewed", notes="")
             for i, limit, unit in (("A", 72, "in"), ("B", 10, "ft"))]
    decisions = resolve(dict(inside_nyc=True, work_type="corner_ramp_row", road_control="city"), rules, load_precedence())
    within = find_conflicts(rules, decisions, [_item(5, "ft", "ramp_length")])
    outside = find_conflicts(rules, decisions, [_item(7, "ft", "ramp_length")])
    assert "within" in within[0].warning and "outside" in outside[0].warning


# Records
def test_blank_obstacle_isnt_an_obstacle():
    from cornerbrief.orchestrator import recorded_reasons
    assert recorded_reasons(dict(progress=[], locations=[dict(obstacles_ramp="", obstacles_landing="  ")])) == []
    assert recorded_reasons(dict(progress=[], locations=[dict(obstacles_ramp="none", obstacles_landing="NONE")])) == []


@pytest.mark.parametrize("where", ["locations", "progress"])
def test_a_missing_corner_id_stops(where):
    corner = copy.deepcopy(load_corner("standard"))
    corner[where][0]["cornerid"] = None
    ok, problems = data_sufficient(corner, build_evidence(corner, load_dictionary(corner)))
    assert not ok


@pytest.mark.parametrize("change", [dict(construc_2=None), dict(construc_2="Planned Construction", construc_1="garbage")])
def test_unreadable_program_record_stops(change):
    corner = copy.deepcopy(load_corner("standard"))
    corner["progress"][0].update(change)
    assert analyze(corner, client=ReplayClient("standard"))["state"] == STOP


def test_ramp_rows_from_two_corners_stop():
    corner = copy.deepcopy(load_corner("standard"))
    corner["locations"][1]["cornerid"] = 123
    corner["progress"].append(dict(corner["progress"][0], cornerid=123))
    ok, problems = data_sufficient(corner, build_evidence(corner, load_dictionary(corner)))
    assert not ok and any("more than one corner" in p for p in problems)


# Site entries
ALLOWED = [dict(key="r:ramp_width", field="ramp_width", unit="in"), dict(key="r:curb_reveal", field="curb_reveal", unit="in"), dict(key="r:lnd_cross_slope", field="lnd_cross_slope", unit="percent")]


@pytest.mark.parametrize("key,value", [("r:ramp_width", -60), ("r:ramp_width", 0), ("r:curb_reveal", 50), ("r:ramp_width", True), ("r:lnd_cross_slope", 90)])
def test_impossible_measurements_are_refused(key, value):
    with pytest.raises(ValueError):
        validate_entries([dict(key=key, value=value)], ALLOWED, "2026-11-02", "A B")


@pytest.mark.parametrize("raw,by,on", [("text", "A B", "2026-11-02"), ([1], "A B", "2026-11-02"), ({"key": "x"}, "A B", "2026-11-02"), ([dict(key="r:ramp_width", value=60)], 5, "2026-11-02"), ([dict(key="r:ramp_width", value=60)], "A B", 20261102), ([dict(key="r:ramp_width", value=60, photo="x")], "A B", "2026-11-02")])
def test_malformed_requests_are_value_errors(raw, by, on):
    with pytest.raises(ValueError):
        validate_entries(raw, ALLOWED, on, by)


def test_a_correction_of_only_date_or_person_is_reported():
    first = run_corner("standard")
    one = rerun_with_field(first, [dict(key="corner:sidewalk_width", value=10)], "2026-11-01", "A B")
    two = rerun_with_field(one, [dict(key="corner:sidewalk_width", value=10)], "2026-11-02", "C D")
    assert [i["key"] for i in two["changes"]["inputs"]] == ["corner:sidewalk_width"]
    assert "2026-11-02" in to_markdown(approve(two, "R"))


def test_review_turning_a_preview_final_is_reported():
    run = run_corner("standard")
    after = copy.deepcopy(run)
    target = next(o for o in after["rule_results"] if o["preview"])
    target["result"], target["preview"] = target["preview"], None
    assert any(r["after"] == target["result"] for r in compare_runs(run, after)["results"])


def test_new_site_visit_items_are_in_the_download():
    first = analyze(dict(load_corner("standard"), context=dict(inside_nyc=True, work_type="corner_ramp_row", road_control="not_recorded")), client=OfflineClient())
    second = copy.deepcopy(first)
    second["approval"] = dict(reviewer="R", at="now", meaning="m")
    second["changes"] = compare_runs(first, {**first, "site_visit": first["site_visit"] + [dict(where="Corner", action="Check this.", why="w")]})
    assert "Check this." in to_markdown(second)


# Export
def test_table_text_cant_break_the_download():
    corner = copy.deepcopy(load_corner("constrained"))
    corner["locations"][0]["obstacles_ramp"] = "Pipe | vault\nnext"
    text = to_markdown(approve(analyze(corner, client=ReplayClient("constrained")), "A | B\nC"))
    assert "Pipe | vault\nnext" not in text and "A | B\nC" not in text


def test_saving_leaves_no_temporary_files(tmp_path):
    run = run_corner("standard")
    save_run(run)
    assert [p.suffix for p in (tmp_path / "runs").iterdir()] == [".json"]


# Fetch script
spec = importlib.util.spec_from_file_location("fetch_for_bugfixes", Path(__file__).parent.parent / "scripts" / "fetch_corners.py")
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


def test_fetch_handles_text_in_number_fields():
    assert fetch.classify([dict(ramp_width="n/a", geocyclora="2020-01-01")], []) == "missing_or_stale"
    rows = fetch.num([dict(cornerid="", rampid="7")])
    assert rows[0]["cornerid"] is None and rows[0]["rampid"] == 7


def test_banner_matches_when_one_rule_is_reviewed(monkeypatch):
    import cornerbrief.orchestrator as orchestrator
    from cornerbrief.data_loader import load_corner
    from cornerbrief.llm import ReplayClient
    original = orchestrator.load_rules

    def one_reviewed(*args, **kwargs):
        rules = original(*args, **kwargs)
        for rule in rules:
            if rule["id"] == "NYC-ADMIN-19-112-SLOPE":
                rule.update(status="verified", reviewed_by="Test Person")
        return rules

    monkeypatch.setattr(orchestrator, "load_rules", one_reviewed)
    run = orchestrator.analyze(load_corner("standard"), client=ReplayClient("standard"), save=False)
    assert "every limit result stays unknown" not in run["state_reason"] and "marked unreviewed" in run["state_reason"]
