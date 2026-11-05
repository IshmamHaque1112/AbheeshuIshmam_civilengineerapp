"""Release gate and plain-text export."""
import time
from .config import labels_enabled
from .evidence import input_name
from .library import background_reading
from .trace import redact
from .cost import hide_dollars
from .orchestrator import save_run


class NotApproved(Exception):
    pass


def approve(run: dict, reviewer: str) -> dict:
    reviewer = " ".join(reviewer.split()) if isinstance(reviewer, str) else ""
    if not reviewer:
        raise ValueError("Enter your name to release this packet.")
    run["approval"] = {"reviewer": reviewer, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "meaning": "Released as a pre-design packet. Releasing is not approval."}
    reading = background_reading()  # Citations saved since the run started. Reading never changes a result.
    if reading["items"]:
        run["background"] = reading
    save_run(run)
    return run


def presented(run: dict) -> dict:
    """Apply the demo's display rules, so the page and the download match."""
    if run.get("planning"):
        run = {**run, "planning": {**run["planning"], "cost": hide_dollars(run["planning"]["cost"])}}
    if not labels_enabled():
        run = {**run, "label": None, "label_reason": "", "planning": None}  # This also covers runs saved while the setting was on
    if not run.get("label"):
        run = {**run, "options": []}  # A likely ramp type reads as a label, so it needs the same evidence
    return run


def row(*cells) -> str:
    """Build a table row. Text from records can't break the table."""
    return "| " + " | ".join(" ".join(str("" if c is None else c).split()).replace("|", "\\|") for c in cells) + " |"


def stricter(c: dict) -> str:
    unit = "%" if c["unit"] == "percent" else " in"
    parts = []
    if c.get("stricter_min") is not None:
        parts.append(f"minimum {c['stricter_min']:.3g}{unit}")
    if c.get("stricter_max") is not None:
        parts.append(f"maximum {c['stricter_max']:.3g}{unit}")
    return " and ".join(parts)


def site_visit_markdown(run: dict) -> str:
    """A field sheet needs no release, because it lists what to find out and contains no limit result."""
    L = [f"# CornerBrief site visit list: {run['corner']['label']}", "", f"**{run['notice']}**", "",
         f"Data: {run['corner']['data_kind']}. Prepared {run['created']}.",
         "This list shows what to measure or confirm. It isn't a released packet, a limit result or permission to proceed.", ""]
    if run["site_visit"]:
        L += ["| Where | What to do | Why | Value found | Date | Checked by |", "| --- | --- | --- | --- | --- | --- |"]
        L += [row(v["where"], v["action"], v["why"], "", "", "") for v in run["site_visit"]]
    else:
        L.append("The records didn't produce any site visit items.")
    return "\n".join(" ".join(line.splitlines()) for line in L) + "\n"


def to_markdown(run: dict) -> str:
    if not run.get("approval"):
        raise NotApproved("A person must release this packet before it can be downloaded.")
    run = redact(presented(run), hide_cost=True)
    L = [f"# CornerBrief packet: {run['corner']['label']}", "", f"**{run['notice']}**", "",
         f"Data: {run['corner']['data_kind']}. Agent mode: {run['mode']}.",
         f"Released by {run['approval']['reviewer']} on {run['approval']['at']}. {run['approval']['meaning']}", "",
         f"## State: {run['state']}", run["state_reason"], ""] + ([f"Label: {run['label']}. {run['label_reason']}", ""] if run["label"] else []) + [run["brief"]["summary"], "", run["brief"]["findings_narrative"], "", run["brief"]["engineer_note"], ""]
    if run.get("source_provenance"):
        L += ["## NYC source retrievals", ""]
        L += [f"- {s['dataset']}: {s['url']} · retrieved {s.get('retrieved_at') or 'time unavailable'}. {s['note']}" for s in run["source_provenance"]] + [""]
    if run["problems"]:
        L += ["## Evidence still needed", ""] + [f"- {x}" for x in run["problems"]] + [""]
    if run["changes"]:
        c = run["changes"]
        L += ["## What changed in this rerun", "", f"State: {c['state_before']} to {c['state_after']}.", ""]
        L += [f"- {input_name(i['field'], i['ramp_id'])}: {i['before_label']} {'' if i['before_value'] is None else i['before_value']} to {i['after_label']} {'' if i['after_value'] is None else i['after_value']} {i['unit'] or ''}".rstrip() + (f", {i['after_date']}" if i.get("on_site") else "") for i in c["inputs"]]
        L += [f"- Result, {r['title']}{', ramp ' + r['ramp_id'] if r['ramp_id'] else ''}: {r['before']} to {r['after']}{' (unreviewed calculation)' if r['unreviewed'] else ''}. {r['math']}" for r in c["results"]]
        L += [f"- Site visit item done: {x}" for x in c["site_visit_done"]] + [f"- New site visit item: {x}" for x in c.get("site_visit_added", [])] + [""]
    if run["field_measurements"]:
        L += ["## Measured on site", "", "| Input | Value | Unit | Date | Measured by | Photo |", "| --- | --- | --- | --- | --- | --- |"]
        L += [row(input_name(e["field"], None if e["key"].startswith("corner:") else e["key"].split(":")[0]), e["value"], e["unit"], e["date"], e["by"], e["photo"]) for e in run["field_measurements"]] + [""]
    rec = run["records"]
    L += ["## Corner records", ""]
    L += [f"- Program status: {p['status']}; type: {p['construction_type'] or 'not listed'}; completed: {p['completed'] or 'not listed'}" for p in rec["program"]]
    L += [f"- Ramp {r['ramp_id']}: surveyed {r['surveyed']}; warning surface: {r['warning_surface']}; ponding: {r['ponding']}; ramp obstacles: {r['obstacles_ramp']}; landing obstacles: {r['obstacles_landing']}" for r in rec["ramps"]]
    L += [f"- Complaint {c['id']} on {c['date']}: temporary repair feasible: {c['repair_feasible']}" for c in rec["complaints"]]
    L += [f"- Join note: {x}" for x in run["join_notes"]]
    L += [f"- Permit {p.get('permitnumber')}: {p.get('permittypedesc')}; work {str(p.get('issuedworkstartdate') or '')[:10]} to {str(p.get('issuedworkenddate') or '')[:10]}; {', '.join(str(x).strip() for x in (p.get('onstreetname'), p.get('fromstreetname'), p.get('tostreetname')) if x)}; status: {p.get('permitstatusshortdesc')}" for p in run.get("permits") or []] + [""]
    review = run["rule_review"]
    L += [f"Rule review: {len(review['awaiting_human_review'])} of {review['verified'] + len(review['awaiting_human_review'])} sourced rules still need a named reviewer. {len(run['rules_needing_sources'])} rules still need sources. {len(review['precedence_awaiting_review'])} which-rule-applies decisions still need review.", ""]
    if run.get("dataset_note"):
        L += [run["dataset_note"], ""]
    counts = run["evidence_counts"]
    L += ["Input labels: " + ", ".join(f"{counts[k]} {k}" for k in ("measured", "assumed", "stale", "missing") if counts.get(k)) + ".", ""]
    L += ["## Applicable rules", "", "| Rule | Applies | Why | Decision source |", "| --- | --- | --- | --- |"]
    L += [row(d["title"], "Yes" if d["applies"] else "No", d["reason"], f"{d['source_section']} {d['url']}") for d in run["applicability"]]
    L += ["", "## Evidence", "", "| Input | Value | Unit | Label | Source | Date | Note |", "| --- | --- | --- | --- | --- | --- | --- |"]
    L += [row(input_name(e["field"], e["ramp_id"]), e["value"], e["unit"], "measured on site" if e.get("on_site") and e["label"] == "measured" else e["label"], e["source"], e["date"], e["reason"]) for e in run["evidence"]]
    L += ["", "## Rule results", "", "| Rule | Ramp | Limit | Result | Math or reason | Source | Quote |", "| --- | --- | --- | --- | --- | --- | --- |"]
    L += [row(o["title"], o["ramp_id"], o["limit_text"], o["result"] + (" (stop: evidence still needed)" if o["evidence_stop"] else ""), o["math"] or o["reason"], f"{o['section'] or ''} {o['url'] or ''}", o["quote"]) for o in run["rule_results"]]
    if run["design_targets"]:
        L += ["", "## If this corner is rebuilt: H-1011 design targets", "", "These apply to new design and field layout, not to the existing ramp.", "", "| Target | Ramp | Limit | Surveyed value | Source |", "| --- | --- | --- | --- | --- |"]
        L += [row(o["title"], o["ramp_id"], o["limit_text"], f"{o['result']}: {o['math'] or o['reason']}", f"{o['section']} {o['url']}") for o in run["design_targets"]]
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
        L += ["", f"## Concept plan: {p['cost']['label']}", ""]
        L += [p["cost"]["range_note"], ""] if p["cost"].get("range_note") else []
        L += [f"- {i['label']}: {i['qty']} {i['unit']}" for i in p["takeoff"]["items"]]
        if p["cost"].get("hidden"):
            L += ["", p["cost"]["note"]]
        elif p["cost"]["base"] is None:
            L += ["", "Cost range: unknown, because a rate is missing."]
        else:
            L += ["", f"Cost range: ${p['cost']['low']:,} to ${p['cost']['high']:,}. Base: ${p['cost']['base']:,}. Uses sample rates: {p['cost']['contains_sample_rates']}."]
            L += [f"- {l['item']}: rate {l.get('rate', 'unknown')} per {l.get('unit', '')}; status {l['status']}; source date {l.get('source_date', 'unknown')}" for l in p["cost"]["lines"]]
        L += ["", "### Labor hours", ""]
        if p["crew"]["result"] == "unknown":
            L += ["Unknown, because a crew rate is missing."]
        else:
            L += [f"- {h['trade']}: {h['hours']} hours{', from sample rates' if p['crew']['contains_sample_rates'] else ''}{', from an out-of-date rate' if p['crew']['rates_out_of_date'] else ''}" for h in p["crew"]["hours"]]
        L += ["", "### Work sequence", ""] + [f"{i}. {s}" for i, s in enumerate(p["crew"]["sequence"], 1)]
        L += ["", "### Likely equipment types", ""] + [f"- {e['type']}: {e['use']}" for e in p["equipment"]]
        L += ["", "### Assumptions", ""] + [f"- {a['basis']}" for a in p["takeoff"]["assumptions"]]
        L += ["", "Excluded: " + "; ".join(p["takeoff"]["exclusions"]) + ".", "", "### Questions for a safety professional", ""]
        L += [f"- {q['topic']}: {q['question']}{' Source: ' + q['url'] if q['url'] else ''}" for q in p["safety_questions"]]
    if run["rejections"]:
        L += ["", "## Rejected agent output", ""] + [f"- {x}" for x in run["rejections"]]
    L += ["", f"Agent tokens used: {run['tokens']['input'] + run['tokens']['output']}."]
    if run["background"]["items"]:
        L += ["", "## Background reading", "", run["background"]["note"]]
        L += [f"- {b['title']}{' by ' + ', '.join(b['authors']) if b.get('authors') else ''} ({b.get('year') or 'year unknown'}): {b['url']}" for b in run["background"]["items"]]
    return "\n".join(" ".join(line.splitlines()) for line in L) + "\n"
