#!/usr/bin/env python3
"""CornerBrief data report. Python 3.8+, no packages or API keys needed.
Run: python data_report.py   Output: docs/data_report.md
"""
import json, os, sys, time, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:  # Use the Windows certificate store when available (pip install truststore)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

PORTAL = os.environ.get("CB_PORTAL", "https://data.cityofnewyork.us")
CATALOG = os.environ.get("CB_CATALOG", "https://api.us.socrata.com")
KNOWN = {"Pedestrian Ramp Locations": "ufzp-rrqu",
         "Pedestrian Ramp Program Progress": "e7gc-ub6z"}
SAMPLE = 1000
NEEDS = {
    "Location (lat/long or geometry)": ["lat", "long", "the_geom", "geom", "point", "location"],
    "Corner or ramp ID": ["corner_id", "cornerid", "ramp_id", "rampid", "cnn", "objectid"],
    "Borough": ["boro", "borough"],
    "Ramp type": ["ramp_type", "ramptype", "type"],
    "Running slope": ["running", "run_slope", "runslope", "slope"],
    "Cross slope": ["cross", "cslope"],
    "Ramp width": ["width"],
    "Landing or turning space": ["landing", "turning"],
    "Curb height or reveal": ["curb_h", "curbh", "reveal", "curb_rev"],
    "Sidewalk width": ["sidewalk_w", "swalk_w", "sw_width"],
    "Street grade": ["grade", "street_slope"],
    "Detectable warning surface": ["dws", "detectable", "warning"],
    "Compliance or review status": ["complian", "status", "review", "infeasib"],
    "Complaint or repair": ["complaint", "repair", "sr_", "service"],
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CornerBriefDataReport/0.1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

def find_complaints():
    q = urllib.parse.urlencode({"domains": "data.cityofnewyork.us", "q": "pedestrian ramp complaints", "limit": 10})
    hits = get(f"{CATALOG}/api/catalog/v1?{q}").get("results", [])
    for h in hits:
        res = h.get("resource", {})
        if res.get("name", "").strip().lower() == "pedestrian ramp complaints":
            return res["id"]
    raise LookupError("no exact name match; candidates: " + ", ".join(
        f"{h['resource'].get('name')} ({h['resource'].get('id')})" for h in hits))

def cell(s):
    if isinstance(s, (dict, list)):
        s = json.dumps(s)
    s = str(s).replace("|", "\\|").replace("\n", " ")
    return s[:100] + "..." if len(s) > 100 else s

def inspect(name, ds_id):
    meta = get(f"{PORTAL}/api/views/{ds_id}.json")
    count = get(f"{PORTAL}/resource/{ds_id}.json?$select=count(*)%20as%20n")[0]["n"]
    rows = get(f"{PORTAL}/resource/{ds_id}.json?$limit={SAMPLE}")
    updated = meta.get("rowsUpdatedAt")
    updated = datetime.fromtimestamp(updated, timezone.utc).date().isoformat() if updated else "not listed"
    cols = [c for c in meta.get("columns", []) if not c.get("fieldName", "").startswith(":")]
    out = [f"## {name}", "", f"- ID: `{ds_id}`", f"- Rows: {int(count):,}", f"- Data last updated: {updated}",
           f"- Rows sampled: {len(rows):,}", "", "### Columns", "",
           "| Field | Type | Filled in sample | Distinct in sample | Example | Description |", "| --- | --- | --- | --- | --- | --- |"]
    for c in cols:
        f = c["fieldName"]
        vals = [r[f] for r in rows if r.get(f) not in (None, "")]
        pct = f"{100 * len(vals) / len(rows):.0f}%" if rows else "no rows"
        distinct = len({json.dumps(v, sort_keys=True) for v in vals})
        out.append(f"| `{f}` | {c.get('dataTypeName', '')} | {pct} | {distinct} | {cell(vals[0]) if vals else ''} | {cell(c.get('description', ''))} |")
    out += ["", "### Value breakdowns (sample)", ""]
    shown = False
    for c in cols:
        f = c["fieldName"]
        vals = [str(r[f]) for r in rows if r.get(f) not in (None, "") and not isinstance(r[f], (dict, list))]
        if vals and 1 < len(set(vals)) <= 12:
            shown = True
            out.append(f"- `{f}`: " + ", ".join(f"{cell(v)} ({n})" for v, n in Counter(vals).most_common()))
    if not shown:
        out.append("None with 12 or fewer distinct values.")
    fields = [(c["fieldName"], (c["fieldName"] + " " + c.get("name", "")).lower()) for c in cols]
    matches = {need: [f for f, text in fields if any(k in text for k in kws)] for need, kws in NEEDS.items()}
    return "\n".join(out), matches

def main():
    sets = dict(KNOWN)
    lines, errors, all_matches = [], [], {}
    try:
        sets["Pedestrian Ramp Complaints"] = find_complaints()
    except Exception as e:
        errors.append(f"Pedestrian Ramp Complaints lookup: {e}")
    for name, ds_id in sets.items():
        print(f"Checking {name} ({ds_id})...")
        try:
            text, all_matches[name] = inspect(name, ds_id)
            lines.append(text)
        except Exception as e:
            errors.append(f"{name} ({ds_id}): {e}")
    head = ["# CornerBrief data report", "", f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.", "",
            "Field matches are keyword guesses. Read the column descriptions before relying on them.", ""]
    if errors:
        head += ["## Errors", ""] + [f"- {e}" for e in errors] + [""]
    head += ["## Coverage of what the demo needs", ""]
    if all_matches:
        head += [f"Datasets checked: {', '.join(all_matches)}.", "", "| Need | Possible fields |", "| --- | --- |"]
        for need in NEEDS:
            found = [f"{n}: `{f}`" for n, m in all_matches.items() for f in m[need]]
            head.append(f"| {need} | {'; '.join(found) if found else 'NOT FOUND'} |")
    else:
        head.append("NOT CHECKED: no dataset could be read, so this says nothing about what the data contains.")
    path = Path("docs/data_report.md")
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(head) + "\n\n" + "\n\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path.resolve()}")
    if errors:
        print("Finished with errors; see the top of the report.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
