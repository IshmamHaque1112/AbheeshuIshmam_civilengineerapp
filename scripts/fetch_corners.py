#!/usr/bin/env python3
"""Find real demo corners from NYC Open Data, then save the ones you choose.

List candidates:  python scripts/fetch_corners.py --borough QUEENS --street THOMSON
Save the test:    python scripts/fetch_corners.py --save real_test 1370422
"""
import argparse, hashlib, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation
import tempfile
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
PORTAL = os.environ.get("CB_PORTAL", "https://data.cityofnewyork.us")
LOC, PROG, COMP = "ufzp-rrqu", "e7gc-ub6z", "jagj-gttd"
CENTERLINE, PERMITS, OLD_PERMITS, SIDEWALK = "inkn-q76z", "tqtj-sjs8", "c9sj-fmsg", "52n9-sdep"
DOT_SURVEY = "https://services.arcgis.com/wmZOI9vyUBq1zTZx/arcgis/rest/services/CMT_SURVEY_COMPLIANCY_TOLERANCE_PROD/FeatureServer/0/query"
DOT_SURVEY_FIELDS = "RAMPID,RAMP_TYPE,COMPLIANCY_STATUS,RAMP_LENGTH,RAMP_LEFT_FLARE,SDW_APP_WIDTH1,SDW_APP_WIDTH2,OBSTACLES_OTHER,DEFECTIVE_CURB,DEFECTIVE_SIDEWALK"
ROAD_INVENTORY = "https://gisportalny.dot.ny.gov/hostingny/rest/services/Roadways/RoadwayData/MapServer/0/query"
ROAD_INVENTORY_FIELDS = "Roadway_Name,Owning_Jurisdiction,Maintenance_Jurisdiction,Owning_Muni_Name"
NEARBY_METERS = 100
SEGMENT_CAP, PERMIT_CAP = 30, 50
SEGMENT_FIELDS = "physicalid,full_street_name,rw_type,status,streetwidth,trafdir,rwjurisdiction"
# The permit holder's name is left out on purpose, because a permit holder can be a private person.
PERMIT_FIELDS = "permitnumber,permittypedesc,permitstatusshortdesc,permitissuedate,issuedworkstartdate,issuedworkenddate,onstreetname,fromstreetname,tostreetname,sidewalkshortdesc"
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
    # Concurrent browser requests must never read a half-written cache entry.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(data, temporary)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return data


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CornerBriefDemo/0.1"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except Exception:
            if attempt == 1:
                raise
            time.sleep(2 * (attempt + 1))


def query(dataset, **params):
    return get(f"{PORTAL}/resource/{dataset}.json?" + urllib.parse.urlencode({f"${k}": v for k, v in params.items()}))


def num(rows):
    for row in rows:
        for k in ("cornerid", "cmt_corner_id", "rampid"):
            if k in row:
                try:
                    value = Decimal(str(row[k]))
                    row[k] = int(value) if value.is_finite() and 0 < value <= 9999999999 and value == value.to_integral_value() else None
                except (TypeError, ValueError, InvalidOperation):
                    row[k] = None  # The app stops on a missing ID instead of guessing
    return rows


def _placeholder(value):
    try:
        return float(value) in PLACEHOLDER
    except (TypeError, ValueError):
        return True


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
    placeholder = any(_placeholder(r.get(f)) for r in locations for f in REQUIRED)
    obstacle = any(str(r.get(f) or "").strip().lower() not in ("", "none") for r in locations for f in ("obstacles_ramp", "obstacles_landing"))
    complex_ = any("Complex" in str(r.get("construc_2")) for r in progress)
    if placeholder or (built and survey and built > survey):
        return "missing_or_stale"
    if complex_ or obstacle:
        return "constrained"
    return "standard"


def build_where(borough=None, street=None):
    """Build the location filter. Ramp records use borough numbers 1 to 5."""
    parts = ["geocyclora IS NOT NULL"]
    if borough is not None and not isinstance(borough, str):
        raise ValueError("Borough must be text.")
    if borough:
        code = BOROUGHS.get(borough.strip().upper())
        if code is None:
            raise ValueError("Borough must be one of: " + ", ".join(BOROUGHS))
        parts.append(f"borough={code}")
    if street is not None and not isinstance(street, str):
        raise ValueError("Street must be text.")
    if street and (not 2 <= len(street.strip()) <= 80 or not re.fullmatch(r"[\w .'’/-]+", street.strip())):
        raise ValueError("Street must be 2–80 letters, numbers, spaces or street-name punctuation; no wildcards.")
    if street:
        safe = street.strip().upper().replace("'", "''")
        parts.append(f"(upper(stname1) like '%{safe}%' OR upper(stname2) like '%{safe}%')")
    return " AND ".join(parts)


def list_candidates(limit, borough=None, street=None):
    rows = num(query(LOC, limit=limit, order="cornerid", where=build_where(borough, street)))
    corners = {}
    for r in rows:
        if r["cornerid"] is not None:
            corners.setdefault(r["cornerid"], []).append(r)
    ids = list(corners)
    progress = {}
    for i in range(0, len(ids), 100):
        where = "cornerid in(" + ",".join(map(str, ids[i:i + 100])) + ")"
        for r in num(query(PROG, where=where, limit=500)):
            if r.get("cornerid") is not None:
                progress.setdefault(r["cornerid"], []).append(r)
    found = {"standard": [], "constrained": [], "missing_or_stale": []}
    for cid, locs in corners.items():
        if cid in progress:
            found[classify(locs, progress[cid])].append(dict(cornerid=cid, ramps=len(locs), streets=f"{locs[0].get('stname1')} and {locs[0].get('stname2')}", borough=locs[0].get("borough"), status=progress[cid][0].get("construc_2"), survey=str(locs[0].get("geocyclora"))[:10]))
    return found, len(corners), len(progress)


DATASET_NOTE = ("Real NYC Open Data records. The ramp measurement dataset was last updated in October 2021, so its values may not describe today's corner. "
                "NYC DOT says these measurements don't by themselves show ADA compliance, because it also weighs site constraints and technical infeasibility. "
                "Its own assessment is at https://www.nycpedramps.info/survey, and it says some locations may be outside its jurisdiction. "
                "This app corrects the dataset's swapped ramp length and left flare columns to match DOT's survey map.")


def _street(value):
    """Prepare a street name for a text filter. Quotes are doubled, and wildcards can't pass through."""
    return re.sub(r"\s+", " ", str(value or "").replace("%", "").replace("_", " ")).strip().upper().replace("'", "''")


def ramp_point(locations):
    """Return the longitude and latitude of the first ramp with a location."""
    for row in locations:
        point = (row.get("the_geom") or {}).get("coordinates") if isinstance(row.get("the_geom"), dict) else None
        if point and len(point) == 2:
            return float(point[0]), float(point[1])
    return None


def centerline_where(locations):
    """Find street segments near the first ramp with a location. Returns None when no ramp has one."""
    point = ramp_point(locations)
    return f"within_circle(the_geom,{point[1]},{point[0]},{NEARBY_METERS})" if point else None


def sidewalk_where(locations):
    """Find sidewalk shapes that touch a box around the first ramp with a location."""
    point = ramp_point(locations)
    if not point:
        return None
    lon, lat, dx, dy = point[0], point[1], 0.0006, 0.00045
    return f"sub_code='380000' AND intersects(the_geom,'POLYGON(({lon-dx} {lat-dy},{lon+dx} {lat-dy},{lon+dx} {lat+dy},{lon-dx} {lat+dy},{lon-dx} {lat-dy}))')"


def survey_params(locations):
    """Find NYC DOT's survey map records by ramp ID. IDs must be whole numbers."""
    ids = sorted({int(r["rampid"]) for r in locations if str(r.get("rampid") or "").isdigit()})
    return dict(f="json", where=f"RAMPID IN ({','.join(map(str, ids))})", outFields=DOT_SURVEY_FIELDS, returnGeometry="false") if ids else None


def inventory_params(locations):
    """Find roads near the ramp in NYSDOT's Roadway Inventory."""
    point = ramp_point(locations)
    return dict(f="json", geometry=f"{point[0]},{point[1]}", geometryType="esriGeometryPoint", inSR="4326", spatialRel="esriSpatialRelIntersects",
                distance=str(NEARBY_METERS), units="esriSRUnit_Meter", outFields=ROAD_INVENTORY_FIELDS, returnGeometry="false", resultRecordCount="20") if point else None


def permits_where(locations):
    """Find permits for the block that names both streets, with work ending on or after the earliest survey."""
    row = next((r for r in locations if r.get("stname1") and r.get("stname2")), None)
    surveys = sorted(str(r.get("geocyclora"))[:10] for r in locations if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("geocyclora") or "")[:10]))
    names = {str(code): name for name, code in BOROUGHS.items()}
    borough = names.get(str(row.get("borough")), str(row.get("borough") or "").strip().upper()) if row else ""
    first, second = (_street(row.get("stname1")), _street(row.get("stname2"))) if row else ("", "")
    if not (first and second and surveys and borough in BOROUGHS):
        return None
    def on(a, b):
        return f"(upper(onstreetname) like '%{a}%' AND (upper(fromstreetname) like '%{b}%' OR upper(tostreetname) like '%{b}%'))"
    return f"upper(boroughname)='{borough}' AND issuedworkenddate>='{surveys[0]}' AND ({on(first, second)} OR {on(second, first)})"


def assemble_corner(locations, progress, complaints, retrieved=None, provenance=None, nearby=None):
    """One real-record shape for the CLI and application; never infer units or ownership."""
    first = locations[0]
    corner = dict(label=f"{first.get('stname1') or 'Street not recorded'} and {first.get('stname2') or 'street not recorded'}",
                  data_kind="NYC Open Data", retrieved=retrieved or date.today().isoformat(), sources=[LOC, PROG, COMP],
                  dataset_note=DATASET_NOTE,
                  context=dict(inside_nyc=True, work_type="corner_ramp_row", road_control="not_recorded"),
                  locations=locations, progress=progress, complaints=complaints)
    if provenance is not None:
        corner["source_provenance"] = provenance
    corner.update(nearby or {})
    from cornerbrief.evidence import road_owner, road_owner_assumed
    corner["context"]["road_control"] = road_owner(corner) or "not_recorded"
    if road_owner_assumed(corner):
        corner["context"]["road_control_basis"] = "assumed"
    return corner


def save(role, cid):
    locations = num(query(LOC, where=f"cornerid={cid}", limit=20))
    progress = num(query(PROG, where=f"cornerid={cid}", limit=20))
    complaints = num(query(COMP, where=f"cmt_corner_id={cid}", limit=50))
    if not locations:
        raise ValueError("it has no ramp measurements.")
    from cornerbrief.search import nearby_records
    nearby, sources = nearby_records(locations)
    corner = assemble_corner(locations, progress, complaints, provenance=sources, nearby=nearby)
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
        if not args.save[1].isdigit():
            sys.exit(f"Corner ID must be a number, not {args.save[1]}.")
        try:
            save(args.save[0], int(args.save[1]))
        except (ValueError, OSError) as exc:  # Network errors are OSErrors
            sys.exit(f"Couldn't save corner {args.save[1]}: {exc}")
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
