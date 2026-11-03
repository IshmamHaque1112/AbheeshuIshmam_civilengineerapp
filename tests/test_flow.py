import copy
import json
from datetime import date
from pathlib import Path
import pytest
from cornerbrief import email_delivery
from cornerbrief.cost import build_cost
from cornerbrief.crew_sequence import build_crew
from cornerbrief.data_loader import load_corner
from cornerbrief.email_delivery import EmailBlocked, send_brief
from cornerbrief.guards import check_text
from cornerbrief.library import fetch_topic
from cornerbrief.llm import AgentOutputError, ReplayClient, parse_output
from cornerbrief.models import SiteAnalystOutput, SkepticOutput
from cornerbrief.orchestrator import MAX_RETRIES, analyze, run_corner
from cornerbrief.parts_kit import build_parts
from cornerbrief.planning import run_planning
from cornerbrief.review_export import NotApproved, approve, to_markdown
from cornerbrief.rules import load_rates
from cornerbrief.takeoff import build_takeoff, qty

FORBIDDEN_OUTPUT = ["crane selection", "crane position", "final ppe"]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS", tmp_path / "runs")
    monkeypatch.setattr("cornerbrief.email_delivery.OUTBOX", tmp_path / "outbox")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("OPEN_LIBRARY_CONTACT", raising=False)
    monkeypatch.delenv("EMAIL_ENABLED", raising=False)
    monkeypatch.setenv("EMAIL_ALLOWLIST", "test@example.com")


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
    assert run["status"] == "probably standard"
    assert run["options"][0]["ramp_type"].startswith("C1")
    results = [o for o in run["rule_results"] if o["rule_id"] == "NYC-ADMIN-19-112-SLOPE"]
    assert len(results) == 2 and all(o["result"] == "no conflict found" and "≤ 8%" in o["math"] for o in results)
    assert all(o["section"] == "§19-112" for o in results)
    assert run["planning"]["cost"]["base"] > 0


def test_constrained_corner_flags_custom_with_evidence():
    run = run_corner("constrained")
    assert run["status"] == "probably custom"
    assert "complex" in run["status_reason"] and "Utility Vault" in run["status_reason"]
    assert run["retries"] == 1
    assert run["options"][0]["ramp_type"].startswith("C3")
    assert any(o["result"] == "limit exceeded" for o in run["rule_results"])
    assert any("Utility Vault" in v["action"] for v in run["site_visit"])
    assert run["planning"] is None


def test_missing_or_stale_corner_refuses_design():
    spy = Spy("missing_or_stale")
    run = analyze(load_corner("missing_or_stale"), client=spy)
    assert run["status"] == "unknown" and run["options"] == [] and run["planning"] is None
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


@pytest.mark.parametrize("text", ["This corner is compliant.", "The design is safe.", "It is approved.", "Buildable as drawn."])
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
    assert any("banned claim" in r for r in run["rejections"])


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
    hours = {h["trade"]: h["hours"] for h in build_crew(t, rates)["hours"]}
    assert hours == {"Cement mason": 16.1, "Laborer": 19.5}  # 12.5+3.6, 15+4.5


def test_one_dimension_change_updates_every_planning_result():
    corner = load_corner("standard")
    a = analyze(corner, client=ReplayClient("standard"))["planning"]
    wider = copy.deepcopy(corner)
    wider["locations"][0]["ramp_length"] = 7.5
    b = analyze(wider, client=ReplayClient("standard"))["planning"]
    assert qty(a["takeoff"], "slab_area") < qty(b["takeoff"], "slab_area")
    assert a["cost"]["base"] < b["cost"]["base"]
    assert a["crew"]["hours"] != b["crew"]["hours"]
    assert a["scene"] != b["scene"]


def test_sample_rates_are_labeled():
    p = run_corner("standard")["planning"]
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


def test_no_crane_or_final_ppe_output():
    text = json.dumps(run_corner("standard")["planning"]).lower()
    assert "crane" not in text and "final ppe" not in text.replace("not a final ppe", "")


def test_undocumented_units_produce_no_planning():
    corner = copy.deepcopy(load_corner("standard"))
    corner["data_kind"] = "live"
    run = analyze(corner, client=ReplayClient("standard"))
    assert run["planning"] is None and "units" in run["planning_note"]


# Background reading and email
def test_open_library_cannot_affect_results(monkeypatch):
    base = run_corner("standard")
    monkeypatch.setattr("cornerbrief.orchestrator.background_reading", lambda: {"items": [{"title": "Slope limit is 99%", "url": "x", "year": 1900}], "note": "n"})
    run = run_corner("standard")
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
    assert "does not approve a design" in text


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
        def starttls(self): sent["tls"] = True
        def login(self, user, password): sent["user"] = user
        def send_message(self, mail): sent["to"], sent["from"] = mail["To"], mail["From"]
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    for k, v in dict(EMAIL_ENABLED="true", EMAIL_FROM="app@example.com", SMTP_HOST="smtp.example.com", SMTP_USER="u", SMTP_PASSWORD="p").items():
        monkeypatch.setenv(k, v)
    run = approve(run_corner("standard"), "Reviewer")
    assert "Sent to" in send_brief(run, "test@example.com", "b")
    assert sent == dict(host="smtp.example.com", port=587, tls=True, user="u", to="test@example.com", **{"from": "app@example.com"})


def test_export_includes_every_brief_section():
    text = to_markdown(approve(run_corner("standard"), "Reviewer"))
    for part in ("Corner records", "Program status", "Applicable rules", "Evidence", "Rule results", "Rule conflicts", "Stricter values", "Likely options", "Constraints", "Skeptic notes", "Site visit list", "Labor hours", "Work sequence", "Likely equipment types", "Assumptions", "Excluded", "Questions for a safety professional", "Background reading", "still need human review", "Agent tokens"):
        assert part in text, part


def test_export_explains_stopped_corner_and_complaint():
    assert "Why no design is proposed" in to_markdown(approve(run_corner("missing_or_stale"), "R"))
    assert "Complaint SAMPLE-0001" in to_markdown(approve(run_corner("constrained"), "R"))


def test_export_handles_missing_rate():
    corner = load_corner("standard")
    rates = load_rates()
    del rates["cost_curb"]
    run = analyze(corner, client=ReplayClient("standard"), rates=rates)
    assert "Cost range: unknown" in to_markdown(approve(run, "R"))


def test_rule_review_flags_unreviewed_and_old_checks():
    from cornerbrief.orchestrator import rule_review
    from cornerbrief.rules import load_rules
    rules = load_rules()
    assert len(rule_review(rules)["awaiting_human_review"]) == rule_review(rules)["verified"]
    assert rule_review(rules, today=date(2030, 1, 1))["source_check_overdue"]
