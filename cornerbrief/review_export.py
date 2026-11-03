"""Approval gate and plain-text export."""
import time
from .orchestrator import save_run


class NotApproved(Exception):
    pass


def approve(run: dict, reviewer: str) -> dict:
    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise ValueError("Enter the reviewer's name.")
    run["approval"] = {"reviewer": reviewer, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "meaning": "Reviewed for release as a pre-design brief. This does not approve a design."}
    save_run(run)
    return run


def to_markdown(run: dict) -> str:
    if not run.get("approval"):
        raise NotApproved("A person must approve this brief before it can be downloaded.")
    L = [f"# CornerBrief: {run['corner']['label']}", "", f"**{run['notice']}**", "",
         f"Data: {run['corner']['data_kind']}. Agent mode: {run['mode']}.",
         f"Released by {run['approval']['reviewer']} on {run['approval']['at']}. {run['approval']['meaning']}", "",
         f"## Status: {run['status']}", run["status_reason"], "", run["brief"]["summary"], "", run["brief"]["findings_narrative"], "", run["brief"]["engineer_note"], ""]
    L += ["## Applicable rules", "", "| Rule | Applies | Why | Decision source |", "| --- | --- | --- | --- |"]
    L += [f"| {d['title']} | {'Yes' if d['applies'] else 'No'} | {d['reason']} | {d['source_section']} {d['url']} |" for d in run["applicability"]]
    L += ["", "## Evidence", "", "| Input | Value | Unit | Label | Source | Note |", "| --- | --- | --- | --- | --- | --- |"]
    L += [f"| {e['key']} | {'' if e['value'] is None else e['value']} | {e['unit'] or ''} | {e['label']} | {e['source']} | {e['reason']} |" for e in run["evidence"]]
    L += ["", "## Rule results", "", "| Rule | Ramp | Limit | Result | Math or reason | Source |", "| --- | --- | --- | --- | --- | --- |"]
    L += [f"| {o['title']} | {o['ramp_id'] or ''} | {o['limit_text']} | {o['result']} | {o['math'] or o['reason']} | {o['section'] or ''} {o['url'] or ''} |" for o in run["rule_results"]]
    L += ["", "## Rule conflicts for engineer review", ""]
    for c in run["conflicts"]:
        L.append(f"- {c['parameter']}: {c['warning']} " + "; ".join(f"{r['section']}: {r['limit']}" for r in c["rules"]))
    if run["options"]:
        L += ["", "## Likely options", ""] + [f"- {o['ramp_type']}: {o['rationale']}" for o in run["options"]]
    if run["challenges"]:
        L += ["", "## Skeptic notes", ""] + [f"- {c['claim']}: {c['issue']}" for c in run["challenges"]]
    L += ["", "## Site visit list", ""] + [f"- {v['where']}: {v['action']} {v['why']}" for v in run["site_visit"]]
    if run["planning"]:
        p = run["planning"]
        L += ["", f"## Concept plan: {p['cost']['label']}", "", p["cost"]["range_note"], ""]
        L += [f"- {i['label']}: {i['qty']} {i['unit']}" for i in p["takeoff"]["items"]]
        L += ["", f"Cost range: ${p['cost']['low']:,} to ${p['cost']['high']:,}. Base: ${p['cost']['base']:,}. Uses sample rates: {p['cost']['contains_sample_rates']}."]
        L += ["", "Excluded: " + "; ".join(p["takeoff"]["exclusions"]) + ".", "", "### Questions for a safety professional", ""]
        L += [f"- {q['topic']}: {q['question']}" for q in p["safety_questions"]]
    elif run["planning_note"]:
        L += ["", "## Concept plan", "", run["planning_note"]]
    L += ["", "## Background reading", "", run["background"]["note"]]
    L += [f"- {b['title']} ({b.get('year') or 'year unknown'}): {b['url']}" for b in run["background"]["items"]]
    return "\n".join(L) + "\n"
