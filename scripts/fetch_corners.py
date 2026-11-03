#!/usr/bin/env python3
"""Find real demo corners from NYC Open Data, then save the ones you choose.

List candidates:  python scripts/fetch_corners.py --borough QUEENS --street THOMSON
Save the test:    python scripts/fetch_corners.py --save real_test 1370422
"""
import argparse, hashlib, json, os, sys, time, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
PORTAL = os.environ.get("CB_PORTAL", "https://data.cityofnewyork.us")
LOC, PROG, COMP = "ufzp-rrqu", "e7gc-ub6z", "jagj-gttd"
PLACEHOLDER = {999, 9999, -999}
BOROUGHS = {"MANHATTAN": 1, "BRONX": 2, "BROOKLYN": 3, "QUEENS": 4, "STATEN ISLAND": 5}
REFRESH = {"on": False}
REQUIRED = ["ramp_running_slope_total", "ramp_cross_slope", "ramp_width", "ramp_length", "lnd_width", "lnd_length", "lnd_cross_slope", "curb_reveal"]


def get(url):
    key = hashlib.sha256(url.encode()).hexdigest()
    path = ROOT / "cache" / "nyc" / f"{key}.json"
    if path.exists() and not REFRESH["on"]:
        return json.loads(path.read_text(encoding="utf-8"))
    data = _download(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CornerBriefDemo/0.1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def query(dataset, **params):
    return get(f"{PORTAL}/resource/{dataset}.json?" + urllib.parse.urlencode({f"${k}": v for k, v in params.items()}))


def num(rows):
    for row in rows:
        for k in ("cornerid", "cmt_corner_id", "rampid"):
            if k in row:
                row[k] = int(float(row[k]))
    return rows


def parse(value):
    try:
        return date.fromisoformat(str(value)[:10].replace("/", "-"))
    except ValueError:
        return None


def classify(locations, progress):
    """Sort a corner into a demo role using the same data problems the app checks."""
    built = [parse(r.get("construc_1")) for r in progress]
    built = max([d for d in built if d], default=None)
    survey = max([d for d in (parse(r.get("geocyclora")) for r in locations) if d], default=None)
    placeholder = any(r.get(f) in (None, "") or float(r.get(f)) in PLACEHOLDER for r in locations for f in REQUIRED)
    obstacle = any(r.get(f) not in (None, "None") for r in locations for f in ("obstacles_ramp", "obstacles_landing"))
    complex_ = any("Complex" in str(r.get("construc_2")) for r in progress)
    if placeholder or (built and survey and built > survey):
        return "missing_or_stale"
    if complex_ or obstacle:
        return "constrained"
    return "standard"


def build_where(borough=None, street=None):
    """Build the location filter. Ramp records use borough numbers 1 to 5."""
    parts = ["geocyclora IS NOT NULL"]
    if borough:
        code = BOROUGHS.get(borough.strip().upper())
        if code is None:
            raise ValueError("Borough must be one of: " + ", ".join(BOROUGHS))
        parts.append(f"borough={code}")
    if street:
        safe = street.strip().upper().replace("'", "''")
        parts.append(f"(upper(stname1) like '%{safe}%' OR upper(stname2) like '%{safe}%')")
    return " AND ".join(parts)


def list_candidates(limit, borough=None, street=None):
    rows = num(query(LOC, limit=limit, order="cornerid", where=build_where(borough, street)))
    corners = {}
    for r in rows:
        corners.setdefault(r["cornerid"], []).append(r)
    ids = list(corners)
    progress = {}
    for i in range(0, len(ids), 100):
        where = "cornerid in(" + ",".join(map(str, ids[i:i + 100])) + ")"
        for r in num(query(PROG, where=where, limit=500)):
            progress.setdefault(r["cornerid"], []).append(r)
    found = {"standard": [], "constrained": [], "missing_or_stale": []}
    for cid, locs in corners.items():
        if cid in progress:
            found[classify(locs, progress[cid])].append(dict(cornerid=cid, ramps=len(locs), streets=f"{locs[0].get('stname1')} and {locs[0].get('stname2')}", borough=locs[0].get("borough"), status=progress[cid][0].get("construc_2"), survey=str(locs[0].get("geocyclora"))[:10]))
    return found, len(corners), len(progress)


def save(role, cid):
    locations = num(query(LOC, where=f"cornerid={cid}", limit=20))
    progress = num(query(PROG, where=f"cornerid={cid}", limit=20))
    complaints = num(query(COMP, where=f"cmt_corner_id={cid}", limit=50))
    if not locations:
        sys.exit(f"Corner {cid} has no ramp measurements.")
    first = locations[0]
    corner = dict(label=f"{first.get('stname1')} and {first.get('stname2')}", data_kind="NYC Open Data",
                  retrieved=date.today().isoformat(), sources=[LOC, PROG, COMP],
                  dataset_note="Real test corner. The ramp measurement dataset was last updated in October 2021, so its values may not match the corner today.",
                  context=dict(inside_nyc=True, work_type="corner_ramp_row", road_control="not_recorded"),
                  locations=locations, progress=progress, complaints=complaints)
    out = ROOT / "data" / "live"
    out.mkdir(exist_ok=True, parents=True)
    path = out / f"{role}.json"
    path.write_text(json.dumps(corner, indent=1), encoding="utf-8")
    print(f"Saved {path}. Its current role by the data: {classify(locations, progress)}.")


def attachments():
    meta = get(f"{PORTAL}/api/views/{LOC}.json")
    items = (meta.get("metadata") or {}).get("attachments") or []
    return [dict(name=a.get("name") or a.get("filename"), url=f"{PORTAL}/api/views/{LOC}/files/{a.get('blobId') or a.get('assetId')}?filename={urllib.parse.quote(str(a.get('filename')))}") for a in items]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", nargs=2, metavar=("ROLE", "CORNERID"))
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--borough", help="MANHATTAN, BRONX, BROOKLYN, QUEENS or STATEN ISLAND")
    parser.add_argument("--street", help="Part of a street name, such as THOMSON")
    parser.add_argument("--refresh", action="store_true", help="Ignore saved API responses")
    args = parser.parse_args()
    REFRESH["on"] = args.refresh
    if args.save:
        if args.save[0] != "real_test":
            sys.exit("ROLE must be real_test. The sample corners don't change.")
        save(args.save[0], int(args.save[1]))
        return
    found, total, joined = list_candidates(args.limit, args.borough, args.street)
    lines = ["# Real corner candidates", "", f"Checked {total} corners. {joined} joined to Program Progress.", ""]
    for role, rows in found.items():
        lines += [f"## {role}: {len(rows)} found", "", "| Corner ID | Ramps | Streets | Borough | Status | Survey |", "| --- | --- | --- | --- | --- | --- |"]
        lines += [f"| {r['cornerid']} | {r['ramps']} | {r['streets']} | {r['borough']} | {r['status']} | {r['survey']} |" for r in rows[:15]] + [""]
    lines += ["## Documents attached to the ramp dataset", "", "Use these to confirm units, then update data/data_dictionary.yaml.", ""]
    try:
        files = attachments()
        lines += [f"- [{f['name']}]({f['url']})" for f in files] or ["None listed."]
    except Exception as exc:
        lines.append(f"Couldn't read the attachments: {exc}")
    path = ROOT / "docs" / "candidates.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}.")


if __name__ == "__main__":
    main()
