"""Run the required flow. Python decides data sufficiency, applicability, limits and status."""
import json, os, time, uuid
from collections import Counter
from datetime import date, timedelta
from .agents import brief_writer, records, site_analyst, skeptic
from .applicability import resolve
from .checker import design_targets, find_conflicts, run_checks
from .data_loader import load_corner, load_dictionary
from .config import labels_enabled
from .evidence import build_evidence, data_sufficient, join_report, survey_lines, validate_labels
from .field import compare_runs, field_inputs, merge_entries, validate_entries
from .guards import check_text
from .library import background_reading
from .llm import AgentOutputError, get_client
from .models import BriefWriterOutput
from .trace import TracingClient, redact
from .paths import RUNS
from .planning import run_planning
from .rules import load_precedence, load_rules
from .site_visit import build_list

MAX_RETRIES = 2
CHECKS = "checks the evidence supports"
STOP = "stop: evidence still needed"
NOTICE = "Demo only, with no affiliation to NYC. Pre-design support, not a compliance decision. A licensed professional must review any design."


def _dump(x):
    return x.model_dump() if hasattr(x, "model_dump") else x


def recorded_reasons(corner: dict) -> list[str]:
    reasons = []
    program = "the sample program record" if corner.get("data_kind") == "SAMPLE DATA" else "the city's program record"
    if any("Complex" in str(r.get("construc_2")) for r in corner.get("progress", [])):
        reasons.append(f"{program} lists this corner as complex")
    obstacles = [str(row[f]).strip() for row in corner.get("locations", []) for f in ("obstacles_ramp", "obstacles_landing") if str(row.get(f) or "").strip().lower() not in ("", "none")]
    if obstacles:
        reasons.append("the record shows these obstacles: " + ", ".join(dict.fromkeys(obstacles)))
    return reasons


def _exceeded(outcomes) -> bool:
    return any("limit exceeded" in (o.result, o.preview) for o in outcomes)


def decide_state(sufficient, corner, outcomes, review_status) -> tuple[str, str]:
    """Every corner ends in one of two states. Anything incomplete or unexplained stops."""
    if not sufficient:
        return STOP, "Required evidence is missing, out of date, unconfirmed or in conflict, so this check stops here."
    if review_status == "incomplete":
        return STOP, "The agent review didn't finish, so this check stops here."
    if _exceeded(outcomes) and not recorded_reasons(corner):
        return STOP, "A calculated value is above a limit, and no recorded constraint explains why. An engineer should look at this corner."
    note = " The saved agent review wasn't reused, because the inputs changed." if review_status == "not run" else ""
    if any(o.preview for o in outcomes):
        return CHECKS, f"The records support these calculations, but no named person has reviewed the rules, so every limit result stays unknown. This isn't permission to proceed.{note}"
    return CHECKS, f"The evidence supports the checks below. An engineer still decides what they mean, so this isn't permission to proceed.{note}"


def provisional_label(state, corner, outcomes, evidence, review_status, decisions, rules, precedence) -> tuple[str | None, str]:
    """Return a label only when it's turned on and the evidence, review, rules and which-rule decisions are all complete."""
    complete = state == CHECKS and review_status == "finished" and all(e.label == "measured" for e in evidence)
    by_id = {r["id"]: r for r in rules}
    applicable = [d for d in decisions if d.applies]
    rules_reviewed = all(d.status == "verified" and not d.forced_unknown for d in applicable) and all(precedence[d.precedence_id].get("reviewed_by") for d in decisions)
    checks_resolved = not any(o.preview for o in outcomes) and not any(o.result == "unknown" and by_id[o.rule_id]["operator"] != "reference" for o in outcomes)
    has_result = any(o.result == "no conflict found" for o in outcomes)
    if not (labels_enabled() and complete and rules_reviewed and checks_resolved and has_result) or _exceeded(outcomes):
        return None, ""
    reasons = recorded_reasons(corner)
    if reasons:
        return "probably custom", "Provisional: probably custom because " + " and ".join(reasons) + ". This isn't an approval."
    return "probably standard", "Provisional: no recorded complexity or obstacle, and no value above a limit. This isn't an approval."


def corner_records(corner: dict) -> dict:
    return dict(
        program=[dict(status=r.get("construc_2"), construction_type=r.get("constructi"), completed=r.get("construc_1")) for r in corner.get("progress", [])],
        complaints=[dict(id=r.get("complaint_id"), date=str(r.get("complaint_date") or "")[:10], repair_feasible=r.get("temp_repair_feasible"), repair_date=str(r.get("temp_repair_date") or "")[:10], repair_type=r.get("temp_repair_type")) for r in corner.get("complaints", [])],
        ramps=[dict(ramp_id=str(r.get("rampid")), surveyed=str(r.get("geocyclora") or "")[:10], warning_surface=r.get("dws_conditions"), ponding=r.get("ponding"), obstacles_ramp=r.get("obstacles_ramp"), obstacles_landing=r.get("obstacles_landing")) for r in corner.get("locations", [])])


def rule_review(rules: list[dict], precedence: dict | None = None, today: date | None = None) -> dict:
    today = today or date.today()
    verified = [r for r in rules if r["status"] == "verified"]
    waiting = [r for r in rules if r["status"] == "unreviewed"]
    sourced = verified + waiting
    overdue = [r["id"] for r in sourced if date.fromisoformat(str(r["retrieved_on"])) < today - timedelta(days=365)]
    precedence = load_precedence() if precedence is None else precedence
    return dict(verified=len(verified), awaiting_human_review=[r["id"] for r in waiting], source_check_overdue=overdue,
                precedence_awaiting_review=[k for k, v in precedence.items() if not v.get("reviewed_by")])


def _log(log, agent, attempt, payload, output, usage, error=None):
    log.append(redact(dict(agent=agent, attempt=attempt, input=payload, output=_dump(output) if output is not None else None, usage=usage, error=error)))


def analyze(corner: dict, client=None, rules=None, rates=None, save=True, field=None) -> dict:
    rules = load_rules() if rules is None else rules
    precedence = load_precedence()
    field = field or []
    client = TracingClient(client or get_client(corner, inputs_changed=bool(field)))
    road = next((e["value"] for e in field if e["key"] == "corner:road_control"), None)
    if road:
        context = {k: v for k, v in corner.get("context", {}).items() if k != "road_control_basis"}
        corner = {**corner, "context": {**context, "road_control": road}}
    labels_off = not labels_enabled()
    log, rejections = [], []
    evidence = build_evidence(corner, load_dictionary(corner), field)
    joins = join_report(corner)

    payload = {"corner": corner["label"], "evidence": [e.model_dump() for e in evidence], "join_notes": joins}
    records_summary = ""
    try:
        out, usage = records.run(client, 0, payload)
        _log(log, "records", 0, payload, out, usage)
        rejections += validate_labels(out, evidence)
        issues = check_text(out.summary, payload, labels_off=True)
        if issues:
            rejections += [f"Records agent: {i}" for i in issues]
        else:
            records_summary = out.summary
    except AgentOutputError as exc:
        _log(log, "records", 0, payload, None, {}, str(exc))
        rejections.append("The Records agent's output was rejected, so Python's labels were used.")

    context = corner.get("context", {})
    decisions = resolve(context, rules, precedence)
    sufficient, problems = data_sufficient(corner, evidence)
    visits = build_list(evidence, corner)
    outcomes, options, constraints, challenges, retries, retry_limit_hit = [], [], [], [], 0, False
    review_status = "not needed"

    if sufficient and not getattr(client, "runs_review", True):
        review_status = "not run"
        outcomes = run_checks(rules, decisions, evidence)
    elif sufficient:
        review_status = "incomplete"
        keys = {e.key for e in evidence}
        feedback, attempt = [], 0
        while True:
            analyst_in = {"corner": corner["label"], "evidence": [e.model_dump() for e in evidence],
                          "progress": corner.get("progress", []), "complaints": corner.get("complaints", []), "reviewer_challenges": feedback}
            try:
                analyst, usage = site_analyst.run(client, attempt, analyst_in)
                text = " ".join([c.text for c in analyst.constraints] + [o.rationale for o in analyst.options])
                issues = check_text(text, analyst_in) + check_text(" ".join(c.text for c in analyst.constraints), analyst_in, labels_off=True)
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
                    if any(c.severity == "rework" for c in review.challenges):
                        verdict = "rework"  # A pass can't leave a rework challenge open
                    text_issues = check_text(" ".join(c.claim + " " + c.issue for c in review.challenges), skeptic_in, labels_off=True)
                    if text_issues:
                        challenges, feedback, verdict = [], [{"claim": "Your previous review", "issue": i, "severity": "rework"} for i in text_issues], "rework"
                        rejections += [f"Skeptic attempt {attempt + 1}: {i}" for i in text_issues]
                except AgentOutputError as exc:
                    _log(log, "skeptic", attempt, skeptic_in, None, {}, str(exc))
                    rejections.append(f"Skeptic attempt {attempt + 1}: the output was invalid, so the review isn't complete.")
                    verdict = "rework"
            if verdict == "pass":
                review_status = "finished"
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
        outcomes = [o.model_copy(update={"reason": "Not checked, because required data is missing or out of date."}) if o.reason == "There is no value for this field." else o for o in outcomes]

    targets = design_targets(rules, decisions, evidence) if sufficient else []
    conflicts = find_conflicts(rules, decisions, evidence if sufficient else [])
    state, state_reason = decide_state(sufficient, corner, outcomes, review_status)
    label, label_reason = provisional_label(state, corner, outcomes, evidence, review_status, decisions, rules, precedence)
    planning = run_planning(evidence, rates) if label == "probably standard" else None
    planning_note = None
    if labels_off:
        planning_note = "Concept plans stay off until R28 has documented pass evidence and a named person authorizes them."
    elif planning is None:
        planning_note = "No model or quantities were made, because a plan needs complete evidence, a finished review, verified rules and no exceeded limit."
    record = dict(state=state, state_reason=state_reason, label=label, problems=problems, evidence=[e.model_dump() for e in evidence],
                  rule_results=[o.model_dump() for o in outcomes], design_targets=[o.model_dump() for o in targets], options=options if label else [], constraints=constraints, challenges=challenges,
                  site_visit=visits, planning_quantities=planning["takeoff"]["items"] if planning else [])
    writer_in = {"corner": corner["label"], "record": record, "records_summary": records_summary}
    try:
        written, usage = brief_writer.run(client, 0, writer_in)
        issues = check_text(" ".join([written.summary, written.findings_narrative, written.engineer_note]), writer_in, labels_off=label is None)
        _log(log, "brief_writer", 0, writer_in, written, usage, "; ".join(issues) or None)
    except AgentOutputError as exc:
        written, issues = None, [str(exc)]
        _log(log, "brief_writer", 0, writer_in, None, {}, str(exc))
    if issues:
        rejections += [f"Brief writer: {i}" for i in issues]
        written = BriefWriterOutput(summary=f"{state_reason} See the sections below.", findings_narrative="The narrative was rejected, so only checked results are shown.")

    token_in = sum((e.get("usage") or {}).get("input_tokens", 0) for e in client.calls)
    token_out = sum((e.get("usage") or {}).get("output_tokens", 0) for e in client.calls)
    run = dict(id=uuid.uuid4().hex[:12], created=time.strftime("%Y-%m-%d %H:%M:%S"), mode=client.mode, notice=NOTICE,
               corner=dict(key=corner.get("key"), label=corner["label"], data_kind=corner["data_kind"]),
               context=corner.get("context", {}), state=state, state_reason=state_reason, label=label, label_reason=label_reason, sufficient=sufficient, problems=problems, join_notes=joins,
               brief=written.model_dump(), applicability=[d.model_dump() for d in decisions], evidence=[e.model_dump() for e in evidence],
               rule_results=[o.model_dump() for o in outcomes], design_targets=[o.model_dump() for o in targets], conflicts=[c.model_dump() for c in conflicts], options=options,
               constraints=constraints, challenges=challenges, site_visit=visits, planning=planning, planning_note=planning_note,
               background=background_reading(), rejections=rejections, retries=retries, retry_limit_hit=retry_limit_hit, review_status=review_status,
               field_measurements=field, field_inputs=field_inputs([e.model_dump() for e in evidence]), changes=None, previous_run_id=None,
               source_provenance=corner.get("source_provenance", []),
               street_segments=corner.get("street_segments") or [], permits=corner.get("permits") or [], dot_survey=survey_lines(corner),
               dataset_note=corner.get("dataset_note"), evidence_counts=dict(Counter(e.label for e in evidence)),
               tokens=dict(input=token_in, output=token_out), approval=None, agent_log=log, trace_events=client.calls,
               records=corner_records(corner), rule_review=rule_review(rules, precedence),
               rules_needing_sources=[r["id"] for r in rules if r["status"] == "needs_source"])
    run = redact(run)
    if save:
        save_run(run)
    return run


def save_run(run: dict):
    """Write to a temporary file first, so a reader never sees a half-written run."""
    RUNS.mkdir(parents=True, exist_ok=True)
    temporary = RUNS / f"{run['id']}.{uuid.uuid4().hex[:6]}.tmp"
    temporary.write_text(json.dumps(run, indent=1, default=str), encoding="utf-8")
    for attempt in range(5):
        try:
            os.replace(temporary, RUNS / f"{run['id']}.json")
            return
        except PermissionError:  # Windows refuses while another request is reading the file
            if attempt == 4:
                temporary.unlink(missing_ok=True)
                raise
            time.sleep(0.05)


def load_run(run_id: str) -> dict:
    if not run_id.isalnum():
        raise FileNotFoundError(run_id)
    try:
        run = json.loads((RUNS / f"{run_id}.json").read_text(encoding="utf-8"))
    except ValueError as exc:
        raise FileNotFoundError(run_id) from exc
    if not isinstance(run, dict) or not {"state", "evidence_counts", "field_inputs"} <= set(run):
        raise FileNotFoundError(run_id)  # Saved by an older version of the app
    return run


def rerun_with_field(previous: dict, raw: list[dict], measured_on: str, by: str, client=None) -> dict:
    """Add site measurements, rerun every check and record what changed. The new version needs its own release."""
    new = validate_entries(raw, previous["field_inputs"], measured_on, by)
    corner = load_corner(previous["corner"]["key"])
    run = analyze(corner, client=client, field=merge_entries(previous["field_measurements"], new), save=False)
    run["changes"] = compare_runs(previous, run)
    run["previous_run_id"] = previous["id"]
    save_run(run)
    return run


def run_corner(key: str, client=None) -> dict:
    return analyze(load_corner(key), client=client)
