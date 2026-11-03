"""Load saved corner records. Sample corners never change. A saved real corner is an extra, labeled test."""
import json
import yaml
from .paths import DATA

SAMPLE_KEYS = ["standard", "constrained", "missing_or_stale"]
REAL_KEY = "real_test"
KEYS = SAMPLE_KEYS + [REAL_KEY]


def load_corner(key: str) -> dict:
    if key not in KEYS:
        raise KeyError(key)
    path = DATA / "live" / f"{key}.json" if key == REAL_KEY else DATA / "corners" / f"{key}.json"
    if not path.exists():
        raise KeyError(key)
    corner = json.loads(path.read_text(encoding="utf-8"))
    corner["key"] = key
    return corner


def list_corners() -> list[dict]:
    """Demo order: standard, constrained, the real test if saved, then the stop case."""
    order = ["standard", "constrained"] + ([REAL_KEY] if (DATA / "live" / f"{REAL_KEY}.json").exists() else []) + ["missing_or_stale"]
    out = []
    for key in order:
        c = load_corner(key)
        out.append({"key": key, "label": c["label"], "data_kind": c["data_kind"]})
    return out


def load_dictionary(corner: dict) -> dict:
    name = "sample_data_dictionary.yaml" if corner.get("data_kind") == "SAMPLE DATA" else "data_dictionary.yaml"
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))
