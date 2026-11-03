"""Run the required flow. Python decides data sufficiency, applicability, limits and status."""
import json, time, uuid
from datetime import date, timedelta
from .agents import brief_writer, records, site_analyst, skeptic
from .applicability import resolve
from .checker import find_conflicts, run_checks
from .data_loader import load_corner, load_dictionary
from .evidence import build_evidence, data_sufficient, join_report, validate_labels
from .guards import check_text
from .library import background_reading
from .llm import AgentOutputError, get_client
from .models import BriefWriterOutput
from .paths import RUNS
from .planning import run_planning
from .rules import load_precedence, load_rules
from .site_visit import build_list

MAX_RETRIES = 2
NOTICE = "Pre-design support only. This is not a compliance decision, and a licensed professional must review any design."


def _dump(x):
    return x.model_dump() if hasattr(x, "model_dump") else x


def decide_status(sufficient, corner, outcomes) -> tuple[str, str]:
    if not sufficient:
        return "unknown", "Required data is missing or out of date, so no design is proposed."
    reasons = []
    if any("Complex" in str(r.get("construc_2")) for r in corner.get("progress", [])):
        reasons.append("the city's program lists this corner as complex")
    obstacles = [row[f] for row in corner.get("locations", []) for f in ("obstacles_ramp", "obstacles_landing") if row.get(f) not in (None, "None")]
    if obstacles:
        reasons.append("the record shows these obstacles: " + ", ".join(dict.fromkeys(obstacles)))
    if reasons:
        return "probably custom", "Probably custom because " + " and ".join(dict.fromkeys(reasons)) + "."
    return "probably standard", "No recorded complexity or obstacle was found in the available records."


def corner_records(corner: dict) -> dict:
    return dict(
        program=[dict(status=r.get("construc_2"), construction_type=r.get("constructi"), completed=r.get("construc_1")) for r in corner.get("progress", [])],
        complaints=[dict(id=r.get("complaint_id"), date=str(r.get("complaint_date") or "")[:10], repair_feasible=r.get("temp_repair_feasible"), repair_date=str(r.get("temp_repair_date") or "")[:10], repair_type=r.get("temp_repair_type")) for r in corner.get("complaints", [])],
        ramps=[dict(ramp_id=str(r.get("rampid")), surveyed=str(r.get("geocyclora") or "")[:10], warning_surface=r.get("dws_conditions"), ponding=r.get("ponding"), obstacles_ramp=r.get("obstacles_ramp"), obstacles_landing=r.get("obstacles_landing")) for r in corner.get("locations", [])])


def rule_review(rules: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    verified = [r for r in rules if r["status"] == "verified"]
    overdue = [r["id"] for r in verified if date.fromisoformat(str(r["retrieved_on"])) < today - timedelta(days=365)]
    return dict(verified=len(verified), awaiting_human_review=[r["id"] for r in verified if not r.get("reviewed_by")], source_check_overdue=overdue)


def _log(log, agent, attempt, payload, output, usage, error=None):
    log.append(dict(agent=agent, attempt=attempt, input=payload, output=_dump(output) if output is not None else None, usage=usage, error=error))


def analyze(corner: dict, client=None, rules=None, rates=None, save=True) -> dict:
    rules = load_rules() if rules is None else rules
    precedence = load_precedence()
    client = client or get_client(corner)
    log, rejections = [], []
    evidence = build_evidence(corner, load_dictionary(corner))
    joins = join_report(corner)

    payload = {"corner": corner["label"], "evidence": [e.model_dump() for e in evidence], "join_notes": joins}
    records_summary = ""
    try:
        out, usage = records.run(client, 0, payload)
        _log(log, "records", 0, payload, out, usage)
        rejections += validate_labels(out, evidence)
        records_summary = out.summary
    except AgentOutputError as exc:
        _log(log, "records", 0, payload, None, {}, str(exc))
        rejections.append("The Records agent's output was rejected, so Python's labels were used.")

    context = corner.get("context", {})
    decisions = resolve(context, rules, precedence)
    sufficient, problems = data_sufficient(corner, evidence)
    visits = build_list(evidence, corner)
    outcomes, options, constraints, challenges, retries, retry_limit_hit = [], [], [], [], 0, False

    if sufficient:
        keys = {e.key for e in evidence}
        feedback, attempt = [], 0
        while True:
            analyst_in = {"corner": corner["label"], "evidence": [e.model_dump() for e in evidence],
                          "progress": corner.get("progress", []), "complaints": corner.get("complaints", []), "reviewer_challenges": feedback}
            try:
                analyst, usage = site_analyst.run(client, attempt, analyst_in)
                text = " ".join([c.text for c in analyst.constraints] + [o.rationale for o in analyst.options])
                issues = check_text(text, analyst_in)
                bad_keys = sorted({k for x in analyst.constraints + analyst.options for k in x.evidence_keys} - keys)
                if bad_keys:
                    issues.append(f"Cites evidence that doesn't exist: {bad_keys}.")
                _log(log, "site_analyst", attempt, analyst_in, analyst, usage, "; ".join(issues) or None)
            except AgentOutputError as exc:
                analyst, issues = None, [f"Output failed the schema: {exc}"]
                _log(log, "site_analyst", attempt, analyst_in, None, {}, issues[0])
            if issues:
                feedback = [{"claim": "Your previous output", "issue": i, "severity": "rework"} for i in issues]
                rejections += [f"Site analyst attempt {attempt + 1}: {i}" for i in issues]
                verdict = "rework"
            else:
                options, constraints = [o.model_dump() for o in analyst.options], [c.model_dump() for c in analyst.constraints]
                outcomes = run_checks(rules, decisions, evidence)
                skeptic_in = {"options": options, "constraints": constraints, "evidence": [e.model_dump() for e in evidence],
                              "rule_results": [o.model_dump() for o in outcomes], "applicability": [d.model_dump() for d in decisions]}
                try:
                    review, usage = skeptic.run(client, attempt, skeptic_in)
                    _log(log, "skeptic", attempt, skeptic_in, review, usage)
                    challenges = [c.model_dump() for c in review.challenges]
                    feedback, verdict = challenges, review.verdict
                except AgentOutputError as exc:
                    _log(log, "skeptic", attempt, skeptic_in, None, {}, str(exc))
                    rejections.append("The Skeptic's output was rejected, so its review is missing.")
                    verdict = "pass"
            if verdict == "pass":
                break
            if retries >= MAX_RETRIES:
                retry_limit_hit = True
                break
            retries += 1
            attempt += 1
        if not outcomes:
            outcomes = run_checks(rules, decisions, evidence)
    else:
        outcomes = run_checks(rules, decisions, [])
        outcomes = [o.model_copy(update={"reason": "Not checked, because required data is missing or out of date."}) if o.result == "unknown" and o.parameter else o for o in outcomes]

    conflicts = find_conflicts(rules, decisions, evidence if sufficient else [])
    status, status_reason = decide_status(sufficient, corner, outcomes)
    planning = run_planning(evidence, rates) if sufficient and status == "probably standard" else None
    planning_note = None
    if sufficient and status != "probably standard":
        planning_note = "No model or estimate was made, because a custom layout needs an engineer first."
    elif sufficient and planning is None:
        planning_note = "No model or estimate was made, because the measurement units aren't confirmed yet."
    elif not sufficient:
        planning_note = "No model or estimate was made, because required data is missing or out of date."

    record = dict(status=status, status_reason=status_reason, problems=problems, evidence=[e.model_dump() for e in evidence],
                  rule_results=[o.model_dump() for o in outcomes], options=options, constraints=constraints, challenges=challenges,
                  site_visit=visits, planning_quantities=planning["takeoff"]["items"] if planning else [],
                  planning_cost=({k: planning["cost"][k] for k in ("base", "low", "high")} if planning else None))
    writer_in = {"corner": corner["label"], "record": record, "records_summary": records_summary}
    try:
        written, usage = brief_writer.run(client, 0, writer_in)
        issues = check_text(" ".join([written.summary, written.findings_narrative, written.engineer_note]), writer_in)
        _log(log, "brief_writer", 0, writer_in, written, usage, "; ".join(issues) or None)
    except AgentOutputError as exc:
        written, issues = None, [str(exc)]
        _log(log, "brief_writer", 0, writer_in, None, {}, str(exc))
    if issues:
        rejections += [f"Brief writer: {i}" for i in issues]
        written = BriefWriterOutput(summary=f"{status_reason} See the sections below.", findings_narrative="The narrative was rejected, so only checked results are shown.")

    token_in = sum(e["usage"].get("input_tokens", 0) for e in log)
    token_out = sum(e["usage"].get("output_tokens", 0) for e in log)
    run = dict(id=uuid.uuid4().hex[:12], created=time.strftime("%Y-%m-%d %H:%M:%S"), mode=client.mode, notice=NOTICE,
               corner=dict(key=corner.get("key"), label=corner["label"], data_kind=corner["data_kind"]),
               context=context, status=status, status_reason=status_reason, sufficient=sufficient, problems=problems, join_notes=joins,
               brief=written.model_dump(), applicability=[d.model_dump() for d in decisions], evidence=[e.model_dump() for e in evidence],
               rule_results=[o.model_dump() for o in outcomes], conflicts=[c.model_dump() for c in conflicts], options=options,
               constraints=constraints, challenges=challenges, site_visit=visits, planning=planning, planning_note=planning_note,
               background=background_reading(), rejections=rejections, retries=retries, retry_limit_hit=retry_limit_hit,
               tokens=dict(input=token_in, output=token_out), approval=None, agent_log=log,
               records=corner_records(corner), rule_review=rule_review(rules),
               rules_needing_sources=[r["id"] for r in rules if r["status"] == "needs_source"])
    if save:
        save_run(run)
    return run


def save_run(run: dict):
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{run['id']}.json").write_text(json.dumps(run, indent=1, default=str), encoding="utf-8")


def load_run(run_id: str) -> dict:
    if not run_id.isalnum():
        raise FileNotFoundError(run_id)
    return json.loads((RUNS / f"{run_id}.json").read_text(encoding="utf-8"))


def run_corner(key: str, client=None) -> dict:
    return analyze(load_corner(key), client=client)
