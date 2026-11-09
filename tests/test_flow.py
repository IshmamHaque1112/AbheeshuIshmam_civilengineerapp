import copy
import json
from datetime import date
from pathlib import Path
import pytest
from cornerbrief import email_delivery
from cornerbrief.cost import build_cost
from cornerbrief.crew_sequence import build_crew
from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.email_delivery import EmailBlocked, send_brief
from cornerbrief.guards import check_text
from cornerbrief.library import fetch_topic
from cornerbrief.llm import AgentOutputError, ReplayClient, parse_output
from cornerbrief.models import SiteAnalystOutput, SkepticOutput
from cornerbrief.orchestrator import CHECKS, MAX_RETRIES, STOP, analyze, run_corner
from cornerbrief.parts_kit import build_parts
from cornerbrief.planning import run_planning
from cornerbrief.review_export import NotApproved, approve, to_markdown
from cornerbrief.rules import load_rates
from cornerbrief.rules import load_precedence, load_rules
from cornerbrief.takeoff import build_takeoff, qty

FORBIDDEN_OUTPUT = ["crane selection", "crane position", "final ppe"]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS", tmp_path / "runs")
    monkeypatch.setattr("cornerbrief.email_delivery.OUTBOX", tmp_path / "outbox")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("OPEN_LIBRARY_CONTACT", raising=False)
    monkeypatch.delenv("EMAIL_ENABLED", raising=False)
    monkeypatch.delenv("SHOW_LABELS_AND_PLANS", raising=False)
    monkeypatch.setenv("EMAIL_ALLOWLIST", "test@example.com")


def full_entries():
    entry = lambda key, field, value, unit: dict(key=key, field=field, value=value, unit=unit, date="2026-11-02", by="Pat Example", photo=None)
    return [entry("corner:sidewalk_width", "sidewalk_width", 10.0, "ft"), entry("corner:legal_grade", "legal_grade", 1.0, "percent"),
            entry("corner:ramp_type", "ramp_type", "C1 perpendicular", None), entry("corner:sidewalk_transverse_slope", "sidewalk_transverse_slope", 2.0, "percent")]


@pytest.fixture
def fully_reviewed(monkeypatch):
    """Everything a label and plan need: the setting on, verified rules, complete evidence and a finished review."""
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    rules = [dict(r, status="verified", reviewed_by="Pat Example", reviewed_on="2026-11-03") for r in load_rules() if r["status"] == "unreviewed"]
    decisions = {k: dict(v, reviewed_by="Pat Example") for k, v in load_precedence().items()}
    monkeypatch.setattr("cornerbrief.orchestrator.load_precedence", lambda: decisions)
    def run(corner=None, rates=None, key="standard"):
        corner = load_corner(key) if corner is None else corner
        return analyze(corner, client=ReplayClient(key), rules=rules, rates=rates, field=full_entries())
    return run


class Spy(ReplayClient):
    def __init__(self, key):
        super().__init__(key)
        self.calls = []

    def call(self, agent, attempt, system, payload, schema, tier="main"):
        self.calls.append(agent)
        return super().call(agent, attempt, system, payload, schema, tier)


class AlwaysRework(Spy):
    def call(self, agent, attempt, system, payload, schema, tier="main"):
        if agent == "skeptic":
            self.calls.append(agent)
            return SkepticOutput(verdict="rework", challenges=[]), {}
        return super().call(agent, 0, system, payload, schema, tier)


# Three demo corners
def test_standard_corner():
    run = run_corner("standard")
    assert run["state"] == CHECKS and run["label"] is None and run["planning"] is None
    results = [o for o in run["rule_results"] if o["rule_id"] == "NYC-ADMIN-19-112-SLOPE"]
    assert len(results) == 2 and all(o["result"] == "unknown" and o["preview"] == "no conflict found" and "≤ 8%" in o["math"] for o in results)
    assert all(o["section"] == "§19-112" for o in results)
    assert "isn't permission to proceed" in run["state_reason"]


def test_constrained_corner_flags_custom_with_evidence():
    run = run_corner("constrained")
    assert run["state"] == CHECKS and run["label"] is None
    assert run["retries"] == 1 and run["review_status"] == "finished"
    assert any(o["preview"] == "limit exceeded" for o in run["rule_results"])
    assert any("Utility Vault" in v["action"] for v in run["site_visit"])
    assert run["planning"] is None


def test_missing_or_stale_corner_refuses_design():
    spy = Spy("missing_or_stale")
    run = analyze(load_corner("missing_or_stale"), client=spy)
    assert run["state"] == STOP and run["options"] == [] and run["planning"] is None
    assert "site_analyst" not in spy.calls and "skeptic" not in spy.calls
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])
    assert any("Re-measure" in v["action"] for v in run["site_visit"])
    assert run["problems"]


def test_retry_limit():
    spy = AlwaysRework("standard")
    run = analyze(load_corner("standard"), client=spy)
    assert spy.calls.count("skeptic") == MAX_RETRIES + 1
    assert spy.calls.count("site_analyst") == MAX_RETRIES + 1
    assert run["retry_limit_hit"] is True
    assert run["review_status"] == "incomplete" and run["state"] == STOP and run["planning"] is None


# Agents cannot supply limits, numbers or claims
def test_agent_cannot_supply_a_limit_field():
    text = json.dumps({"constraints": [], "options": [], "limit": {"max_slope": 12}})
    with pytest.raises(AgentOutputError):
        parse_output(text, SiteAnalystOutput)


def test_agent_output_cannot_change_rule_results():
    class Lying(Spy):
        def call(self, agent, attempt, system, payload, schema, tier="main"):
            if agent == "skeptic":
                return parse_output('{"verdict":"pass","challenges":[],"rule_results":[]}', schema), {}
            return super().call(agent, attempt, system, payload, schema, tier)
    baseline = run_corner("constrained")["rule_results"]
    run = analyze(load_corner("constrained"), client=Lying("constrained"))
    assert [o["result"] for o in run["rule_results"]] == [o["result"] for o in baseline]


@pytest.mark.parametrize("text", ["This corner is compliant.", "The design is safe.", "It is approved.", "Buildable as drawn.", "This ramp is allowed."])
def test_banned_claims_rejected(text):
    assert check_text(text, {})


def test_unsupported_number_rejected():
    assert check_text("The limit is 12%.", {"a": 8})
    assert not check_text("The limit is 8%. Use option C1.", {"a": 8})


def test_brief_writer_claim_falls_back_to_checked_results():
    class Claiming(Spy):
        def call(self, agent, attempt, system, payload, schema, tier="main"):
            if agent == "brief_writer":
                return schema(summary="This corner is compliant.", findings_narrative="x"), {}
            return super().call(agent, attempt, system, payload, schema, tier)
    run = analyze(load_corner("standard"), client=Claiming("standard"))
    assert "compliant" not in run["brief"]["summary"]
    assert any("banned approval or permission word" in r for r in run["rejections"])


def test_fake_evidence_key_is_rejected():
    class Fake(Spy):
        def call(self, agent, attempt, system, payload, schema, tier="main"):
            if agent == "site_analyst":
                return schema(constraints=[], options=[dict(ramp_type="C1 perpendicular", rationale="x", evidence_keys=["9:nope"])]), {}
            return super().call(agent, attempt, system, payload, schema, tier)
    run = analyze(load_corner("standard"), client=Fake("standard"))
    assert run["retry_limit_hit"] and run["options"] == []


def test_false_records_label_is_reported():
    class Liar(Spy):
        def call(self, agent, attempt, system, payload, schema, tier="main"):
            if agent == "records":
                return schema(summary="x", labels=[dict(key="8300001:curb_reveal", label="measured")]), {}
            return super().call(agent, attempt, system, payload, schema, tier)
    run = analyze(load_corner("missing_or_stale"), client=Liar("missing_or_stale"))
    assert any("shows missing" in r for r in run["rejections"])
    assert next(e for e in run["evidence"] if e["key"] == "8300001:curb_reveal")["label"] == "missing"


# Takeoff, hand-checked
def test_takeoff_cost_and_labor_hand_checked():
    ramp = dict(ramp_id="1", width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=4, slope_pct=6)
    t = build_takeoff(build_parts([ramp]))
    assert qty(t, "slab_area") == 50  # 5x6 + 5x4
    assert qty(t, "dws_area") == 10  # 5x2
    assert qty(t, "curb_length") == 9  # 5+4
    assert qty(t, "removal_area") == 62.5  # 50x1.25
    assert qty(t, "concrete_volume") == round(50 * (4 / 12) / 27, 2)
    rates = load_rates()
    cost = build_cost(t, rates)
    assert cost["base"] == 2000 + 600 + 810 + 750  # 50x40 + 10x60 + 9x90 + 62.5x12
    assert (cost["low"], cost["high"]) == (2080, 8320)
    hours = {h["trade"]: h["hours"] for h in build_crew(t, rates, allow_sample=True)["hours"]}
    assert hours == {"Cement mason": 16.1, "Laborer": 19.5}  # 12.5+3.6, 15+4.5


def test_one_dimension_change_updates_every_planning_result(fully_reviewed):
    corner = load_corner("standard")
    a = fully_reviewed(corner)["planning"]
    wider = copy.deepcopy(corner)
    wider["locations"][0]["ramp_length"] = 7.5
    b = fully_reviewed(wider)["planning"]
    assert qty(a["takeoff"], "slab_area") < qty(b["takeoff"], "slab_area")
    assert a["cost"]["base"] < b["cost"]["base"]
    assert a["work_plan"]["steps"] != b["work_plan"]["steps"] and a["revision"] != b["revision"]
    assert a["scene"] != b["scene"]


def test_sample_rates_are_labeled(fully_reviewed):
    p = fully_reviewed()["planning"]
    assert p["cost"]["contains_sample_rates"] and p["crew"]["contains_sample_rates"]
    assert p["cost"]["label"] == "Class 5 concept estimate, not a bid"
    assert p["takeoff"]["exclusions"]


def test_missing_rate_returns_unknown():
    rates = load_rates()
    del rates["cost_curb"]
    t = build_takeoff(build_parts([dict(ramp_id="1", width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=4, slope_pct=6)]))
    cost = build_cost(t, rates)
    assert cost["base"] is None and cost["result"] == "unknown"


def test_old_rate_is_flagged():
    t = build_takeoff(build_parts([dict(ramp_id="1", width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=4, slope_pct=6)]))
    assert build_cost(t, load_rates(), today=date(2030, 1, 1))["lines"][0]["rate_out_of_date"]


def test_no_crane_or_final_ppe_output(fully_reviewed):
    text = json.dumps(fully_reviewed()["planning"]).lower()
    assert "crane" not in text and "final ppe" not in text.replace("not a final ppe", "")


def test_undocumented_units_produce_no_planning(monkeypatch):
    corner = copy.deepcopy(load_corner("standard"))
    corner["data_kind"] = "live"
    dictionary = copy.deepcopy(load_dictionary(corner))
    for field in dictionary["fields"].values():
        field["unit_status"] = "assumed"
    monkeypatch.setattr("cornerbrief.orchestrator.load_dictionary", lambda _: dictionary)
    run = analyze(corner, client=ReplayClient("standard"))
    assert run["planning"] is None and any("units" in x for x in run["problems"]) and run["state"] == STOP


# Background reading and email
def test_open_library_cannot_affect_results(monkeypatch, fully_reviewed):
    base = fully_reviewed()
    monkeypatch.setattr("cornerbrief.orchestrator.background_reading", lambda: {"items": [{"title": "Slope limit is 99%", "url": "x", "year": 1900}], "note": "n"})
    run = fully_reviewed()
    assert run["rule_results"] == base["rule_results"]
    assert run["planning"]["cost"] == base["planning"]["cost"]
    assert run["brief"] == base["brief"]


def test_open_library_stores_citation_details_only(monkeypatch):
    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    seen = {}
    def fake(req, timeout=0):
        seen["agent"] = req.get_header("User-agent")
        import io
        return io.BytesIO(json.dumps({"docs": [{"title": "T", "author_name": ["A"], "first_publish_year": 1900, "key": "/works/1", "text": ["book text"]}]}).encode())
    monkeypatch.setattr("urllib.request.urlopen", fake)
    rows = fetch_topic("x", "team@example.com", base="https://example.test")
    assert "team@example.com" in seen["agent"]
    assert "text" not in rows[0] and rows[0]["title"] == "T"


def test_email_blocked_without_approval():
    with pytest.raises(EmailBlocked):
        send_brief(run_corner("standard"), "test@example.com", "b")


def test_email_blocked_for_address_not_on_allowlist():
    run = approve(run_corner("standard"), "Reviewer")
    with pytest.raises(EmailBlocked):
        send_brief(run, "other@example.com", "b")


def test_email_dry_run_saves_locally(tmp_path):
    run = approve(run_corner("standard"), "Reviewer")
    assert "No email left" in send_brief(run, "test@example.com", "b")
    assert list((tmp_path / "outbox").glob("*.json"))


# Approval
def test_download_needs_approval():
    run = run_corner("standard")
    with pytest.raises(NotApproved):
        to_markdown(run)
    with pytest.raises(ValueError):
        approve(run, " ")
    text = to_markdown(approve(run, "Reviewer"))
    assert "not a compliance decision" in text and "SAMPLE DATA" in text and "§19-112" in text
    assert "Releasing is not approval" in text


def test_every_corner_shows_applicable_law():
    for key in ("standard", "constrained", "missing_or_stale"):
        decisions = run_corner(key)["applicability"]
        assert next(d for d in decisions if d["rule_id"] == "NYS-BCNYS-2025")["applies"] is False


def test_smtp_needs_settings_and_is_off_by_default(monkeypatch):
    run = approve(run_corner("standard"), "Reviewer")
    assert "No email left" in send_brief(run, "test@example.com", "b")
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    for key in ("EMAIL_FROM", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(EmailBlocked, match="settings are missing"):
        send_brief(run, "test@example.com", "b")


def test_smtp_sends_after_approval_with_settings(monkeypatch):
    sent = {}
    class FakeSMTP:
        def __init__(self, host, port, timeout=0): sent.update(host=host, port=port)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): sent["tls"] = True
        def login(self, user, password): sent["user"] = user
        def send_message(self, mail): sent["to"], sent["from"] = mail["To"], mail["From"]
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    for k, v in dict(EMAIL_ENABLED="true", EMAIL_FROM="app@example.com", SMTP_HOST="smtp.example.com", SMTP_USER="u", SMTP_PASSWORD="p").items():
        monkeypatch.setenv(k, v)
    run = approve(run_corner("standard"), "Reviewer")
    assert "Sent to" in send_brief(run, "test@example.com", "b")
    assert sent == dict(host="smtp.example.com", port=587, tls=True, user="u", to="test@example.com", **{"from": "app@example.com"})


def test_export_includes_every_packet_section():
    text = to_markdown(approve(run_corner("standard"), "Reviewer"))
    for part in ("Corner records", "Program status", "Applicable rules", "Evidence", "Rule results", "Quote", "Rule conflicts", "Stricter values", "Constraints", "Skeptic notes", "Site visit list", "still need a named reviewer", "Agent tokens", "affiliation", "2023-06-14"):
        assert part in text, part
    for hidden in ("Likely options", "Concept plan", "Labor hours", "probably standard"):
        assert hidden not in text, hidden


def test_export_includes_the_plan_only_with_a_label(fully_reviewed):
    text = to_markdown(approve(fully_reviewed(), "Reviewer"))
    for part in ("Label: probably standard", "Likely options", "Labor hours", "Draft work sequence", "Dimensions used, with their records", "Likely equipment types", "Assumptions", "Excluded", "Questions for a safety professional", "Source: https"):
        assert part in text, part


def test_export_explains_stopped_corner_and_complaint():
    assert "Evidence still needed" in to_markdown(approve(run_corner("missing_or_stale"), "R"))
    assert "Complaint SAMPLE-0001" in to_markdown(approve(run_corner("constrained"), "R"))


def test_export_handles_missing_rate(monkeypatch, fully_reviewed):
    monkeypatch.setenv("SHOW_DOLLARS", "true")
    rates = load_rates()
    del rates["cost_curb"]
    run = fully_reviewed(rates=rates)
    assert "Dollar figures are hidden" in to_markdown(approve(run, "R"))


def test_rule_review_flags_unreviewed_and_old_checks():
    from cornerbrief.orchestrator import rule_review
    from cornerbrief.rules import load_precedence, load_rules
    rules = load_rules()
    assert rule_review(rules)["verified"] == 0 and rule_review(rules)["awaiting_human_review"]
    assert rule_review(rules, today=date(2030, 1, 1))["source_check_overdue"]
    assert rule_review(rules)["precedence_awaiting_review"]


def test_standard_corner_shows_design_targets_without_failing_it():
    run = run_corner("standard")
    assert run["state"] == CHECKS
    assert not [o for o in run["rule_results"] if o["preview"] == "limit exceeded"]
    assert [o for o in run["design_targets"] if o["preview"] == "limit exceeded"]
    assert "If this corner is rebuilt" in to_markdown(approve(run, "R"))


def test_stopped_corner_has_no_design_targets():
    assert run_corner("missing_or_stale")["design_targets"] == []


# Status and review rules from PRD v2
def test_exceeded_limit_with_no_obstacle_stops():
    corner = copy.deepcopy(load_corner("standard"))
    corner["locations"][0]["ramp_running_slope_total"] = 9.5
    run = analyze(corner, client=ReplayClient("standard"))
    assert run["state"] == STOP and "above a limit" in run["state_reason"] and run["planning"] is None


def test_invalid_skeptic_reply_is_incomplete_not_a_pass():
    class Bad(Spy):
        def call(self, agent, attempt, system, payload, schema, tier="main"):
            if agent == "skeptic":
                raise AgentOutputError("invalid")
            return super().call(agent, 0, system, payload, schema, tier)
    run = analyze(load_corner("standard"), client=Bad("standard"))
    assert run["review_status"] == "incomplete" and run["state"] == STOP
    assert any("isn't complete" in r for r in run["rejections"])


def test_skeptic_and_records_text_are_guarded():
    class Claims(Spy):
        def call(self, agent, attempt, system, payload, schema, tier="main"):
            if agent == "skeptic":
                return schema(verdict="pass", challenges=[dict(claim="x", issue="This ramp is compliant.", severity="note")]), {}
            if agent == "records":
                return schema(summary="This corner is safe.", labels=[]), {}
            return super().call(agent, 0, system, payload, schema, tier)
    run = analyze(load_corner("standard"), client=Claims("standard"))
    assert any(r.startswith("Records agent") for r in run["rejections"])
    assert any(r.startswith("Skeptic attempt") for r in run["rejections"])
    assert not run["challenges"] and run["review_status"] == "incomplete"


def test_export_carries_notices_and_sample_label():
    text = to_markdown(approve(run_corner("standard"), "R"))
    assert "no affiliation to NYC" in text and "SAMPLE DATA" in text and "not a compliance decision" in text


def test_dollars_are_hidden_by_default(monkeypatch, fully_reviewed):
    monkeypatch.delenv("SHOW_DOLLARS", raising=False)
    run = approve(fully_reviewed(), "R")
    text = to_markdown(run)
    assert "$" not in text and "hidden for this demo" in text
    from cornerbrief.app import public
    shown = public(run)["planning"]["cost"]
    assert shown["hidden"] and "base" not in shown and "rate" not in shown["lines"][0]
    monkeypatch.setenv("SHOW_DOLLARS", "true")
    assert "$" not in to_markdown(run)


def test_takeoff_has_counts(fully_reviewed):
    t = fully_reviewed()["planning"]["takeoff"]
    assert qty(t, "ramp_count") == 2 and qty(t, "landing_count") == 2


def test_missing_crew_rate_returns_unknown():
    rates = load_rates()
    del rates["crew_laborer_curb"]
    t = build_takeoff(build_parts([dict(ramp_id="1", width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=4, slope_pct=6)]))
    crew = build_crew(t, rates)
    assert crew["result"] == "unknown" and crew["hours"] == []


def test_old_crew_rate_is_flagged():
    t = build_takeoff(build_parts([dict(ramp_id="1", width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=4, slope_pct=6)]))
    assert build_crew(t, load_rates(), today=date(2030, 1, 1))["rates_out_of_date"]


def test_sample_rates_give_no_labor_hours():  # Roadmap M2.4
    t = build_takeoff(build_parts([dict(ramp_id="1", width_ft=5, length_ft=6, landing_width_ft=5, landing_length_ft=4, slope_pct=6)]))
    crew = build_crew(t, load_rates())
    assert crew["result"] == "unknown" and crew["hours"] == [] and "placeholder samples" in crew["reason"] and crew["contains_sample_rates"]


def test_email_and_reading_are_hidden_unless_configured(monkeypatch):
    monkeypatch.delenv("EMAIL_ALLOWLIST", raising=False)
    from cornerbrief.app import public
    run = approve(run_corner("standard"), "R")
    assert public(run)["features"]["email"] is False
    assert "Background reading" not in to_markdown(run)


REAL = dict(key="real_test", label="A and B", data_kind="NYC Open Data", dataset_note="Real test corner. The ramp measurement dataset was last updated in October 2021.",
            context=dict(inside_nyc=True, work_type="corner_ramp_row", road_control="not_recorded"),
            locations=[dict(cornerid=1, rampid=2, geocyclora="2023-01-01", curb_reveal="0.2", ramp_running_slope_total="6", ramp_cross_slope="1", ramp_width="60", ramp_length="6",
                            lnd_width="60", lnd_length="60", lnd_cross_slope="1", gutter_slope="1", counter_slope="2", ramp_right_flare="8", ramp_left_flare="8", obstacles_ramp="None", obstacles_landing="None")],
            progress=[dict(cornerid=1, construc_2="Constructed", construc_1="2022/01/01")], complaints=[])


def test_real_test_corner_runs_offline_with_every_limit_unknown():
    from cornerbrief.llm import OfflineClient, get_client
    client = get_client(REAL)
    assert isinstance(client, OfflineClient)
    run = analyze(REAL, client=client)
    assert run["state"] == STOP and run["options"] == [] and run["planning"] is None and run["tokens"] == dict(input=0, output=0)
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])
    assert not any("units" in p for p in run["problems"]) and any("road owner" in p for p in run["problems"])
    assert next(e for e in run["evidence"] if e["field"] == "ramp_width")["label"] == "measured"
    assert any("road" in v["action"] for v in run["site_visit"])
    assert "October 2021" in to_markdown(approve(run, "R"))


def test_real_test_only_listed_when_saved_and_samples_never_change(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path
    from cornerbrief import data_loader
    data = tmp_path / "data"
    shutil.copytree(Path(__file__).parent.parent / "data", data)
    monkeypatch.setattr(data_loader, "DATA", data)
    (data / "live" / "real_test.json").unlink()
    assert [c["key"] for c in data_loader.list_corners()] == ["standard", "constrained", "missing_or_stale"]
    with pytest.raises(KeyError):
        data_loader.load_corner("real_test")
    (data / "live" / "real_test.json").write_text(json.dumps(REAL))
    (data / "live" / "standard.json").write_text(json.dumps(REAL))
    assert [c["key"] for c in data_loader.list_corners()] == ["standard", "constrained", "real_test", "missing_or_stale"]
    assert data_loader.load_corner("standard")["data_kind"] == "SAMPLE DATA"
