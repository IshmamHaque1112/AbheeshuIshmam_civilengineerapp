"""Roadmap M3 as a labeled demonstration. No AI here.

It joins a real or sample corner's evidence with synthetic preview dimensions and a fictional company register
(data/demo/sample_company.yaml). Every output is stamped DEMONSTRATION. Nothing is saved, nothing reaches a
run, packet, label, plan, rule check, field measurement, release, download or email, and nothing is submitted.
The contractor persona is still a hypothesis until real estimators or project engineers are interviewed.
"""
import math
from datetime import date, timedelta

import yaml

from .data_loader import load_corner
from .evidence import input_name, parse_date
from .llm import OfflineClient
from .orchestrator import analyze
from .paths import DATA
from .preview import build_preview, defaults as preview_defaults
from .takeoff import qty

STAMP = "DEMONSTRATION"
NOTICE = ("Demonstration only. The company, its teams, equipment, production history, agreement and payroll are fictional. "
          "Quantities come from synthetic dimensions. Nothing here is saved, submitted or used by a corner packet.")
# Research starting points named in docs/ROADMAP.md. They are links to read, not verified requirements for any job.
LINKS = {
    "permits": "https://www.nyc.gov/html/dot/html/infrastructure/permits.shtml",
    "811": "https://newyork-811.com/about/how-we-work/",
    "pla": "https://www.nyc.gov/site/mocs/regulations/project-labor-agreements.page",
    "ddc": "https://www.nyc.gov/site/ddc/contracts/rfqpql.page",
    "payroll": "https://dol.ny.gov/node/64811",
}
STEP_NEEDS = {"sawcut": ["Concrete saw"], "demolition": ["Compact excavator or skid steer", "Dump truck"], "forming": ["Plate compactor"],
              "pour": [], "cure": [], "warning_surface": [], "restoration": []}
TRAFFIC = {"FT": "one-way", "TF": "one-way", "TW": "two-way", "NV": "non-vehicular"}


def load_company() -> dict:
    return yaml.safe_load((DATA / "demo" / "sample_company.yaml").read_text(encoding="utf-8"))


def _source(corner: dict, dataset: str) -> str | None:
    return next((s["url"] for s in corner.get("source_provenance", []) if s.get("dataset") == dataset), None)


def opportunity_brief(corner: dict, run: dict) -> list[dict]:
    """M3.1: each line tied to its source page, or marked unknown."""
    rows = corner.get("locations", [])
    streets = sorted({str(r.get(f)).strip() for r in rows for f in ("stname1", "stname2") if r.get(f)}) or [corner["label"]]
    ramp_source = _source(corner, "ufzp-rrqu") or "https://data.cityofnewyork.us/d/ufzp-rrqu"
    return [
        dict(item="Location", value=" and ".join(streets), source=ramp_source),
        dict(item="Scope", value=f"Replace {len({r.get('rampid') for r in rows})} pedestrian ramp(s) and landings at this corner, per the draft sequence below", source="This corner's packet"),
        dict(item="Deadline", value="unknown", source=None, note="No solicitation is attached to this demonstration."),
        dict(item="Required qualifications", value="unknown", source=LINKS["ddc"], note="Check the actual solicitation and DDC's prequalified lists."),
        dict(item="Documents", value="Corner packet, site visit list, H-1011 sheets", source="https://www.nycstreetdesign.info/specifications?keysspec=&field_specification_name_value=Pedestrian+Ramps"),
        dict(item="Open questions", value=f"{len(run['site_visit'])} site visit items from the packet", source="This corner's packet"),
    ]


def capability_match(company: dict, steps: list[dict]) -> list[dict]:
    """M3.2: verified records only. A missing or unverified record is unknown, never assumed."""
    caps = {c["id"]: c for c in company["capabilities"]}
    out = []
    for s in steps:
        c = caps.get(s["id"])
        if c and c.get("verified") and c.get("record"):
            out.append(dict(step=s["name"], status="matched", record=c["record"]))
        else:
            out.append(dict(step=s["name"], status="unknown", record=None, note="No verified company record for this capability."))
    for p in company.get("prequalification", []):
        out.append(dict(step=p["list"], status="matched" if p.get("record") else "unknown", record=p.get("record"), note=None if p.get("record") else "No prequalification record in the register.", url=p.get("url")))
    return out


def logistics(corner: dict, run: dict, preview: dict, company: dict, start: date) -> list[dict]:
    """M3.3: each item linked to its source or marked unknown."""
    removal = qty(dict(items=preview["quantities"]), "removal_area")
    width = next((e for e in run["evidence"] if e["field"] == "sidewalk_width"), None)
    streets = {}
    for s in corner.get("street_segments") or []:
        streets.setdefault(str(s.get("full_street_name") or "").strip(), set()).add((s.get("streetwidth"), TRAFFIC.get(s.get("trafdir"), "direction not listed")))
    access = "; ".join(f"{n}: {', '.join(f'{w} ft paved, {d}' for w, d in sorted(v, key=str))}" for n, v in sorted(streets.items())) or "unknown"
    suppliers = {s["material"]: s for s in company.get("suppliers", [])}
    active = [p for p in corner.get("permits") or [] if (parse_date(p.get("issuedworkenddate")) or date.min) >= start]
    return [
        dict(item="Staging area", value=f"unknown. The packet's sidewalk width is {width['value']} {width['unit']} ({width['label']})" if width and width.get("value") is not None else "unknown",
             source=None, status="unknown"),
        dict(item="Delivery access", value=access, source=_source(corner, "inkn-q76z"), status="from records" if streets else "unknown"),
        dict(item="Concrete lead time", value="unknown", source=None, status="unknown", note="No supplier record." if not (suppliers.get("Slab concrete") or {}).get("record") else None),
        dict(item="Warning surface lead time", value="unknown", source=None, status="unknown", note="The supplier record has no lead time."),
        dict(item="Pedestrian access during work", value="unknown. A detour or protected path needs a plan.", source=LINKS["permits"], status="unknown"),
        dict(item="Demolition and waste removal", value=f"{removal} sf of existing surface to remove; hauler unknown", source="Draft sequence quantities", status="partly known"),
        dict(item="Street work permits", value="unknown. None applied for in this demonstration.", source=LINKS["permits"], status="unknown"),
        dict(item="Other active permits on the block", value="; ".join(f"{p['permitnumber']} {p.get('permittypedesc')}, work through {str(p['issuedworkenddate'])[:10]}" for p in active) or "none found in the saved records",
             source=_source(corner, "tqtj-sjs8"), status="conflict" if active else "from records"),
        dict(item="Utility markout", value="unknown. Request a markout before any excavation.", source=LINKS["811"], status="unknown"),
    ]


def _available(windows: list[dict], day: date) -> bool:
    return any(parse_date(w["from"]) <= day <= parse_date(w["to"]) for w in windows)


def sequence(steps: list[dict], preview: dict, company: dict, start: date, active_permits: list[dict]) -> dict:
    """M3.4: place steps in order from sample records. Conflicts are listed, never resolved silently.
    A step with no production record has an unknown duration, and every later date is unknown too."""
    history = {h["step"]: h for h in company.get("production_history", [])}
    teams, equipment = company.get("teams", []), {e["type"]: e for e in company.get("equipment", [])}
    items = {i["id"]: i for i in preview["quantities"]}
    day, rows, conflicts = start, [], []
    for s in steps:
        team = next((t for t in teams if s["id"] in t["qualified_for"]), None)
        row = dict(step=s["name"], team=team["name"] if team else "unknown", equipment=[], start=None, finish=None, duration_days=None, duration_basis="unknown")
        if day is not None:
            row["start"] = day.isoformat()
            if not team:
                conflicts.append(f"{s['name']}: no team in the register is qualified for this step.")
            elif not _available(team["available"], day):
                conflicts.append(f"{s['name']}: {team['name']} isn't available on {day.isoformat()}.")
            for need in STEP_NEEDS.get(s["id"], []):
                e = equipment.get(need)
                ok = bool(e and _available(e["available"], day))
                row["equipment"].append(dict(type=need, record=e["record"] if e else None, available=ok))
                if not ok:
                    conflicts.append(f"{s['name']}: {need} {'has no record' if not e else 'has no availability'} on {day.isoformat()}.")
            for p in active_permits:
                if (parse_date(p.get("issuedworkstartdate")) or date.min) <= day <= (parse_date(p.get("issuedworkenddate")) or date.min):
                    conflicts.append(f"{s['name']}: permit {p['permitnumber']} ({p.get('permittypedesc')}) is active on the block on {day.isoformat()}.")
        h = history.get(s["id"])
        if h and h.get("quantity") in items and h.get("per_day"):
            days = max(1, math.ceil(items[h["quantity"]]["qty"] / h["per_day"]))
            row.update(duration_days=days, duration_basis=f"Sample record {h['record']}: {h['per_day']} {h['unit']} per day")
            if day is not None:
                row["finish"] = (day + timedelta(days=days - 1)).isoformat()
                day = day + timedelta(days=days)
        else:
            if day is not None:
                conflicts.append(f"{s['name']}: no production record, so its duration and every later date are unknown.")
            day = None
        rows.append(row)
    return dict(rows=rows, conflicts=conflicts)


def labor_rules(company: dict) -> dict:
    """M3.5: an agreement applies only when the register ties it to this job. One agreement is never applied to every job."""
    job = company.get("job_id")
    found = [a for a in company.get("agreements", []) if job in a.get("jobs", [])]
    return dict(job=job, agreement=found[0]["name"] if found else None, status="recorded" if found else "unknown",
                note="Labor rules come from this job's own contract and agreement. "
                     + ("" if found else f"No agreement in the register names {job}, so none is applied. ") + "Wages and work rules aren't shown in this demonstration.",
                source=LINKS["pla"])


def drafts(run: dict, preview: dict, company: dict, corner_label: str) -> dict:
    """M3.6: drafts for a person. Nothing is sent or submitted from here."""
    rfis = [dict(number=f"RFI-DRAFT-{i:02d}", question=f"{v['where']}: {v['action']}", reason=v["why"], status="Draft, not sent")
            for i, v in enumerate(run["site_visit"][:8], 1)]
    items = {i["id"]: i for i in preview["quantities"]}
    material = [dict(material="Slab concrete", quantity=items["concrete_volume"]["qty"], unit="cy", supplier="unknown"),
                dict(material="Detectable warning surface", quantity=items["dws_area"]["qty"], unit="sf", supplier="SAMPLE-SUP-02 (fictional)")]
    report, payroll = company.get("daily_report", {}), company.get("payroll", {})
    reported = {e["person"]: e["hours"] for e in report.get("entries", [])}
    paid = {e["person"]: e["hours"] for e in payroll.get("entries", [])}
    issues = []
    for person in sorted(set(reported) | set(paid)):
        a, b = reported.get(person), paid.get(person)
        if a is None:
            issues.append(f"{person} is on payroll for {b} hours but not on the daily report.")
        elif b is None:
            issues.append(f"{person} is on the daily report for {a} hours but not on payroll.")
        elif a != b:
            issues.append(f"{person}: daily report {a} hours, payroll {b} hours.")
    return dict(rfis=rfis, material_request=dict(items=material, status="Draft, not sent"),
                daily_report=dict(date=report.get("date"), location=corner_label, entries=report.get("entries", []), status="Draft, not filed"),
                payroll_check=dict(date=payroll.get("date"), issues=issues, status="Draft check for a person to review; nothing is submitted", source=LINKS["payroll"]))


def build(corner_key: str, start: str | None = None, dimensions: dict | None = None) -> dict:
    """Build the whole demonstration. Raises KeyError for an unknown corner and ValueError for bad inputs."""
    start_day = parse_date(start) if start else date(2026, 11, 16)
    if start_day is None:
        raise ValueError("The start date must look like 2026-11-16.")
    dims = dimensions or {f["id"]: f["default"] for f in preview_defaults()["fields"]}
    preview = build_preview(dims)
    corner = load_corner(corner_key)
    run = analyze(corner, client=OfflineClient(), save=False)
    company = load_company()
    steps = preview["work_plan"]["steps"]
    active = [p for p in corner.get("permits") or [] if (parse_date(p.get("issuedworkenddate")) or date.min) >= start_day]
    return dict(stamp=STAMP, notice=NOTICE, persona_note="The estimator or project engineer persona is a hypothesis until real users are interviewed.",
                company=company["company"], corner=dict(key=corner_key, label=corner["label"], state=run["state"]),
                revision=preview["revision"], dimensions=preview["inputs"], quantities=preview["quantities"],
                brief=opportunity_brief(corner, run), capabilities=capability_match(company, steps),
                logistics=logistics(corner, run, preview, company, start_day), sequence=sequence(steps, preview, company, start_day, active),
                labor_rules=labor_rules(company), drafts=drafts(run, preview, company, corner["label"]),
                authorization="Bidding, hiring, purchasing, permit submission and payroll submission each need their own authorization. This page can't do any of them.")
