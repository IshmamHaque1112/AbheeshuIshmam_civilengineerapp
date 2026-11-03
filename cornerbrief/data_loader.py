"""Load saved corner records. Saved real corners in data/live replace sample corners with the same key."""
import json
import yaml
from .paths import DATA

KEYS = ["standard", "constrained", "missing_or_stale"]


def load_corner(key: str) -> dict:
    if key not in KEYS:
        raise KeyError(key)
    live = DATA / "live" / f"{key}.json"
    path = live if live.exists() else DATA / "corners" / f"{key}.json"
    corner = json.loads(path.read_text(encoding="utf-8"))
    corner["key"] = key
    return corner


def list_corners() -> list[dict]:
    out = []
    for key in KEYS:
        c = load_corner(key)
        out.append({"key": key, "label": c["label"], "data_kind": c["data_kind"]})
    return out


def load_dictionary(corner: dict) -> dict:
    name = "sample_data_dictionary.yaml" if corner.get("data_kind") == "SAMPLE DATA" else "data_dictionary.yaml"
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))
