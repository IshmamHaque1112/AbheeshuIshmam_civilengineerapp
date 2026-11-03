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


def stricter(c: dict) -> str:
    unit = "%" if c["unit"] == "percent" else " in"
    parts = []
    if c.get("stricter_min") is not None:
        parts.append(f"minimum {c['stricter_min']:.3g}{unit}")
    if c.get("stricter_max") is not None:
        parts.append(f"maximum {c['stricter_max']:.3g}{unit}")
    return " and ".join(parts)


def to_markdown(run: dict) -> str:
    if not run.get("approval"):
        raise NotApproved("A person must approve this brief before it can be downloaded.")
    L = [f"# CornerBrief: {run['corner']['label']}", "", f"**{run['notice']}**", "",
         f"Data: {run['corner']['data_kind']}. Agent mode: {run['mode']}.",
         f"Released by {run['approval']['reviewer']} on {run['approval']['at']}. {run['approval']['meaning']}", "",
         f"## Status: {run['status']}", run["status_reason"], "", run["brief"]["summary"], "", run["brief"]["findings_narrative"], "", run["brief"]["engineer_note"], ""]
    if run["problems"]:
        L += ["## Why no design is proposed", ""] + [f"- {x}" for x in run["problems"]] + [""]
    rec = run["records"]
    L += ["## Corner records", ""]
    L += [f"- Program status: {p['status']}; type: {p['construction_type'] or 'not listed'}; completed: {p['completed'] or 'not listed'}" for p in rec["program"]]
    L += [f"- Ramp {r['ramp_id']}: surveyed {r['surveyed']}; warning surface: {r['warning_surface']}; ponding: {r['ponding']}; ramp obstacles: {r['obstacles_ramp']}; landing obstacles: {r['obstacles_landing']}" for r in rec["ramps"]]
    L += [f"- Complaint {c['id']} on {c['date']}: temporary repair feasible: {c['repair_feasible']}" for c in rec["complaints"]]
    L += [f"- Join note: {x}" for x in run["join_notes"]] + [""]
    review = run["rule_review"]
    L += [f"Rule review: {len(review['awaiting_human_review'])} of {review['verified']} checked rules still need human review. {len(run['rules_needing_sources'])} rules still need sources.", ""]
    L += ["## Applicable rules", "", "| Rule | Applies | Why | Decision source |", "| --- | --- | --- | --- |"]
    L += [f"| {d['title']} | {'Yes' if d['applies'] else 'No'} | {d['reason']} | {d['source_section']} {d['url']} |" for d in run["applicability"]]
    L += ["", "## Evidence", "", "| Input | Value | Unit | Label | Source | Note |", "| --- | --- | --- | --- | --- | --- |"]
    L += [f"| {e['key']} | {'' if e['value'] is None else e['value']} | {e['unit'] or ''} | {e['label']} | {e['source']} | {e['reason']} |" for e in run["evidence"]]
    L += ["", "## Rule results", "", "| Rule | Ramp | Limit | Result | Math or reason | Source |", "| --- | --- | --- | --- | --- | --- |"]
    L += [f"| {o['title']} | {o['ramp_id'] or ''} | {o['limit_text']} | {o['result']} | {o['math'] or o['reason']} | {o['section'] or ''} {o['url'] or ''} |" for o in run["rule_results"]]
    L += ["", "## Rule conflicts for engineer review", ""]
    for c in run["conflicts"]:
        L.append(f"- {c['parameter']}: {c['warning']} " + "; ".join(f"{r['section']}: {r['limit']}" for r in c["rules"]) + f". Stricter values: {stricter(c)}. {c['decision']}.")
    if run["options"]:
        L += ["", "## Likely options", ""] + [f"- {o['ramp_type']}: {o['rationale']}" for o in run["options"]]
    if run["constraints"]:
        L += ["", "## Constraints", ""] + [f"- {c['text']}" for c in run["constraints"]]
    if run["challenges"]:
        L += ["", "## Skeptic notes", ""] + [f"- {c['claim']}: {c['issue']}" for c in run["challenges"]]
    L += ["", "## Site visit list", ""] + [f"- {v['where']}: {v['action']} {v['why']}" for v in run["site_visit"]]
    if run["planning"]:
        p = run["planning"]
        L += ["", f"## Concept plan: {p['cost']['label']}", "", p["cost"]["range_note"], ""]
        L += [f"- {i['label']}: {i['qty']} {i['unit']}" for i in p["takeoff"]["items"]]
        if p["cost"]["base"] is None:
            L += ["", "Cost range: unknown, because a rate is missing."]
        else:
            L += ["", f"Cost range: ${p['cost']['low']:,} to ${p['cost']['high']:,}. Base: ${p['cost']['base']:,}. Uses sample rates: {p['cost']['contains_sample_rates']}."]
        L += ["", "### Labor hours", ""] + [f"- {h['trade']}: {h['hours']} hours" for h in p["crew"]["hours"]]
        L += ["", "### Work sequence", ""] + [f"{i}. {s}" for i, s in enumerate(p["crew"]["sequence"], 1)]
        L += ["", "### Likely equipment types", ""] + [f"- {e['type']}: {e['use']}" for e in p["equipment"]]
        L += ["", "### Assumptions", ""] + [f"- {a['basis']}" for a in p["takeoff"]["assumptions"]]
        L += ["", "Excluded: " + "; ".join(p["takeoff"]["exclusions"]) + ".", "", "### Questions for a safety professional", ""]
        L += [f"- {q['topic']}: {q['question']}" for q in p["safety_questions"]]
    elif run["planning_note"]:
        L += ["", "## Concept plan", "", run["planning_note"]]
    if run["rejections"]:
        L += ["", "## Rejected agent output", ""] + [f"- {x}" for x in run["rejections"]]
    L += ["", f"Agent tokens used: {run['tokens']['input'] + run['tokens']['output']}."]
    L += ["", "## Background reading", "", run["background"]["note"]]
    L += [f"- {b['title']} ({b.get('year') or 'year unknown'}): {b['url']}" for b in run["background"]["items"]]
    return "\n".join(L) + "\n"
