#!/usr/bin/env python3
"""Record that a named person checked a rule against its source.

python scripts/review_rule.py NYC-ADMIN-19-112-SLOPE --reviewer "Full Name"
"""
import argparse
import sys
from datetime import date
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def review(rule_id, reviewer, root=ROOT / "rules", today=None):
    reviewer = reviewer.strip()
    if len(reviewer.split()) < 2:
        raise ValueError("Enter the reviewer's full name.")
    matches = [p for p in root.glob("*/*.yaml") if p.stem == rule_id]
    if not matches:
        raise ValueError(f"No rule file named {rule_id}.")
    path = matches[0]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if path.parent.name != "precedence":
        if data.get("status") != "unreviewed":
            raise ValueError(f"{rule_id} has status {data.get('status')}. Only a rule with a source can be reviewed.")
        data["status"] = "verified"
    data["reviewed_by"] = reviewer
    data["reviewed_on"] = (today or date.today()).isoformat()
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rule_id")
    parser.add_argument("--reviewer", required=True)
    args = parser.parse_args()
    try:
        print(f"Recorded review in {review(args.rule_id, args.reviewer)}.")
    except ValueError as exc:
        sys.exit(str(exc))
