"""Bounded NYC queries, shared with the existing CLI fetch/cache implementation."""
import hashlib
import json
import os
import re
import urllib.parse
import uuid
from datetime import datetime, timezone
from scripts import fetch_corners as fetch
from .paths import DATA

MAX_SEARCH = 100
CAPS = {fetch.LOC: 20, fetch.PROG: 20, fetch.COMP: 50}


def rows(dataset, limit, where, order=None, select=None):
    params = {"$limit": limit, "$where": where, "$order": order or ("cornerid" if dataset != fetch.COMP else "cmt_corner_id")}
    if select:
        params["$select"] = select
    url = f"{fetch.PORTAL}/resource/{dataset}.json?" + urllib.parse.urlencode(params)
    raw = fetch.get(url)
    if not isinstance(raw, list) or any(not isinstance(r, dict) for r in raw):
        raise RuntimeError("NYC returned an unexpected dataset response. Try again later.")
    cache = fetch.ROOT / "cache" / "nyc" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    timestamp = datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat() if cache.exists() else None
    return fetch.num(raw), dict(dataset=dataset, url=url, retrieved_at=timestamp,
                               note="Cached response when available; retrieval time is the cache file timestamp.")


def search(borough=None, street=None):
    where = fetch.build_where(borough, street)
    if not (borough and borough.strip()) and not (street and street.strip()):
        raise ValueError("Choose a borough or enter a street.")
    locations, source = rows(fetch.LOC, MAX_SEARCH + 1, where)
    found = {}
    for r in locations[:MAX_SEARCH]:
        cid = r.get("cornerid")
        if cid is not None:
            found.setdefault(cid, dict(cornerid=cid, label=f"{r.get('stname1') or 'Street not recorded'} and {r.get('stname2') or 'street not recorded'}", borough=r.get("borough")))
    return dict(corners=list(found.values()), bounded=len(locations) > MAX_SEARCH,
                row_limit=MAX_SEARCH, sources=[source],
                note=("First 100 ramp rows only, not every matching corner. Narrow the street to refine results. " if len(locations) > MAX_SEARCH else "") + "Program and complaint records are fetched on selection; missing matches stay unknown.")


def nearby_records(locations):
    """Add street and permit context. A failed lookup is reported, because it must not read as "nothing found"."""
    found, sources, failed = {}, [], []
    lookups = (("street_segments", "NYC Street Centerline", fetch.CENTERLINE, fetch.centerline_where(locations), "full_street_name,physicalid", fetch.SEGMENT_FIELDS, fetch.SEGMENT_CAP),
               ("permits", "Street Construction Permits", fetch.PERMITS, fetch.permits_where(locations), "issuedworkenddate DESC", fetch.PERMIT_FIELDS, fetch.PERMIT_CAP))
    for key, name, dataset, where, order, select, cap in lookups:
        if not where:
            failed.append(name)
            continue
        try:
            result, source = rows(dataset, cap + 1, where, order=order, select=select)
        except Exception:
            failed.append(name)
            continue
        found[key] = result[:cap]
        if len(result) > cap:
            found[f"{key}_more"] = True
        sources.append(source)
    if failed:
        found["nearby_not_checked"] = failed
    return found, sources


def pull(cid):
    if not re.fullmatch(r"[1-9][0-9]{0,9}", str(cid)):
        raise ValueError("Corner ID must be a positive integer of at most 10 digits.")
    groups, sources = {}, []
    for dataset, cap in CAPS.items():
        field = "cmt_corner_id" if dataset == fetch.COMP else "cornerid"
        result, source = rows(dataset, cap + 1, f"{field}={cid}")
        if len(result) > cap:
            raise ValueError("This corner exceeds the bounded record limit; no partial packet was created.")
        if any(r.get(field) != int(cid) for r in result):
            raise ValueError("NYC returned mismatched corner IDs; no packet was created.")
        groups[dataset] = result
        sources.append(source)
    locations = groups[fetch.LOC]
    if not locations:
        raise ValueError("No ramp records found for this corner. Search again.")
    nearby, nearby_sources = nearby_records(locations)
    sources += nearby_sources
    times = [s["retrieved_at"] for s in sources if s.get("retrieved_at")]
    corner = fetch.assemble_corner(locations, groups[fetch.PROG], groups[fetch.COMP],
                                   retrieved=max(times) if times else None, provenance=sources, nearby=nearby)
    # The name comes from the records alone, so the same records reuse one snapshot and a saved run's inputs never change.
    digest = hashlib.sha256(json.dumps([groups, nearby], sort_keys=True).encode()).hexdigest()[:12]
    key = f"real_{cid}_{digest}"
    path = DATA / "live" / f"{key}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".{uuid.uuid4().hex[:6]}.tmp")
        temporary.write_text(json.dumps(corner, indent=1), encoding="utf-8")
        os.replace(temporary, path)
    return key
