#!/usr/bin/env python3
"""Create a pending R29 capture or validate participant-reported results; never simulate participants."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROLES = ("junior_engineer", "reviewer")


def template():
    return dict(protocol="docs/R29-ROLE-TEST.md", status="pending human participation", corner_id=None,
                packet_run_id=None, app_commit=None, data_kind=None, source_urls=[], facilitator=None,
                sessions=[dict(role=role, participant=None, actual_human=False, started_at=None, ended_at=None,
                               elapsed_seconds=None, corrections=None, missed_issues=None, permission_misreads=None,
                               notes=None) for role in ROLES], follow_up=None)


def validate(result):
    problems = []
    for key in ("corner_id", "packet_run_id", "app_commit", "data_kind", "facilitator"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            problems.append(f"Record {key}.")
    if not isinstance(result.get("source_urls"), list) or not result["source_urls"]:
        problems.append("Record the corner's source URLs.")
    sessions = result.get("sessions")
    if not isinstance(sessions, list) or len(sessions) != 2 or {s.get("role") for s in sessions if isinstance(s, dict)} != set(ROLES):
        return problems + ["Record exactly one junior engineer and one reviewer session."]
    for session in sessions:
        role = session["role"]
        if session.get("actual_human") is not True or not isinstance(session.get("participant"), str) or not session["participant"].strip():
            problems.append(f"{role}: actual human participation and attribution are pending.")
        try:
            start = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))  # Python 3.10 doesn't read a Z suffix
            end = datetime.fromisoformat(session["ended_at"].replace("Z", "+00:00"))
            duration = session["elapsed_seconds"]
            if not start.tzinfo or not end.tzinfo or end < start or end > datetime.now(timezone.utc) or isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0 or abs((end - start).total_seconds() - duration) > 2:
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError):
            problems.append(f"{role}: record valid dated start/end times with timezone and matching elapsed seconds.")
        for metric in ("corrections", "missed_issues", "permission_misreads"):
            values = session.get(metric)
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                problems.append(f"{role}: record {metric} as descriptions; use [] only if none were observed.")
        if not isinstance(session.get("notes"), str) or not session["notes"].strip():
            problems.append(f"{role}: record observations, including the participant's interpretation of the ending state.")
    if any(s.get("permission_misreads") for s in sessions) and not result.get("follow_up"):
        problems.append("Record follow-up for every interpretation as permission to proceed; stop the demo and retest.")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "check"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.action == "init":
        with args.path.open("x", encoding="utf-8") as output:
            json.dump(template(), output, indent=2)
        print("Created pending capture. Two actual human participants are still required.")
        return
    try:
        result = json.loads(args.path.read_text(encoding="utf-8"))
        problems = validate(result) if isinstance(result, dict) else ["Capture must be an object."]
    except (OSError, ValueError):
        problems = ["Capture could not be read as JSON."]
    if problems:
        print("Incomplete capture:\n" + "\n".join(problems))
        raise SystemExit(1)
    print("Capture fields are complete. This check does not verify human participation or grant engineering permission. Have the facilitator review and sign the observations.")


if __name__ == "__main__":
    main()
