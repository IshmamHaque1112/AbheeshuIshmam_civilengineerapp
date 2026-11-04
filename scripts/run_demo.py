#!/usr/bin/env python3
"""Run the demo corners from the command line and print each result."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cornerbrief.config import load_env
from cornerbrief.data_loader import list_corners
from cornerbrief.orchestrator import run_corner


def main():
    load_env()
    for corner in list_corners():
        run = run_corner(corner["key"])
        counts = Counter(o["preview"] or o["result"] for o in run["rule_results"] if o["preview"] or o["result"] == "not applicable")
        print(f"{run['corner']['label']} [{run['corner']['data_kind']}]")
        print(f"  State: {run['state']}. Label: {run['label'] or 'off'}. Retries: {run['retries']}.")
        print(f"  Unreviewed calculations and non-applicable rules: {dict(counts)}. Site visit items: {len(run['site_visit'])}. Tokens: {run['tokens']['input'] + run['tokens']['output']}.")


if __name__ == "__main__":
    main()
