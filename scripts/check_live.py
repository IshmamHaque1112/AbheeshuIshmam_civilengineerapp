#!/usr/bin/env python3
"""Attempt a bounded public NYC fetch; report network failure separately from mocked tests."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cornerbrief.search import search, pull
from cornerbrief.data_loader import load_corner
from cornerbrief.orchestrator import analyze
from cornerbrief.llm import OfflineClient


def main():
    result = dict(attempted_at=datetime.now(timezone.utc).isoformat(), filter=dict(borough="QUEENS", street="THOMSON"), status="network pending")
    try:
        found = search("QUEENS", "THOMSON")
        result.update(search=found)
        if not found["corners"]:
            result.update(status="live empty result", note="No corner invented or saved.")
        else:
            key = pull(found["corners"][0]["cornerid"])
            corner = load_corner(key)
            run = analyze(corner, client=OfflineClient(), save=False)
            assert run["planning"] is None and all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])
            result.update(status="live fetch passed", corner_key=key, sources=corner["source_provenance"],
                          counts={k: len(corner[k]) for k in ("locations", "progress", "complaints")},
                          state=run["state"], all_limits_unknown=True, mode=run["mode"])
    except Exception as exc:
        result.update(status="live fetch unavailable", error_type=type(exc).__name__, note="Network/API failure, not a passing mocked fetch. Retry with network access and check TLS/API availability.")
    Path("docs/P1-LIVE-FETCH.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "live fetch passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
