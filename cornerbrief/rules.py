"""Load and validate rule, precedence and rate files. Models never write to these files."""
from pathlib import Path
import yaml
from .paths import RULES, RATES

REQUIRED = ["id", "title", "jurisdiction", "authority_type", "applies_to", "parameter", "operator",
            "limit", "unit", "stage", "source_document", "edition", "effective_date", "section", "url",
            "quote", "retrieved_on", "status", "reviewed_by", "notes"]
STATUSES = {"verified", "needs_source", "superseded"}
STAGES = {"general", "design", "work_acceptance"}
OPERATORS = {"max", "min", "range", "reference", "needs_source"}


class RuleError(ValueError):
    pass


def validate_rule(rule: dict, name: str = "") -> dict:
    label = rule.get("id") or name
    missing = [k for k in REQUIRED if k not in rule]
    if missing:
        raise RuleError(f"{label}: missing fields {missing}")
    if rule["status"] not in STATUSES:
        raise RuleError(f"{label}: bad status {rule['status']}")
    if rule["stage"] not in STAGES:
        raise RuleError(f"{label}: bad stage {rule['stage']}")
    if rule["operator"] not in OPERATORS:
        raise RuleError(f"{label}: bad operator {rule['operator']}")
    if rule["status"] == "verified":
        for key in ("section", "url", "quote", "edition"):
            if not rule.get(key):
                raise RuleError(f"{label}: a verified rule needs an exact {key}")
        if rule["operator"] in ("max", "min", "range") and rule.get("limit") is None:
            raise RuleError(f"{label}: a verified numeric rule needs a limit")
    if rule["status"] == "needs_source" and rule.get("limit") is not None:
        raise RuleError(f"{label}: a needs_source rule cannot hold a limit")
    return rule


def load_rules(root: Path = RULES) -> list[dict]:
    rules, seen = [], set()
    for folder in ("federal", "nyc", "nys"):
        for path in sorted((root / folder).glob("*.yaml")):
            rule = validate_rule(yaml.safe_load(path.read_text(encoding="utf-8")), path.name)
            if rule["id"] in seen:
                raise RuleError(f"Duplicate rule id {rule['id']}")
            seen.add(rule["id"])
            rules.append(rule)
    return rules


def load_precedence(root: Path = RULES) -> dict[str, dict]:
    out = {}
    for path in sorted((root / "precedence").glob("*.yaml")):
        item = yaml.safe_load(path.read_text(encoding="utf-8"))
        for key in ("id", "question", "decision", "reason", "source_section", "url"):
            if key not in item:
                raise RuleError(f"{path.name}: missing {key}")
        out[item["id"]] = item
    return out


def load_rates(root: Path = RATES) -> dict[str, dict]:
    out = {}
    for path in sorted(root.glob("*.yaml")):
        rate = yaml.safe_load(path.read_text(encoding="utf-8"))
        for key in ("id", "item", "unit", "value", "source", "source_date", "location", "status", "notes"):
            if key not in rate:
                raise RuleError(f"{path.name}: missing {key}")
        if rate["status"] not in {"sample", "public", "licensed"}:
            raise RuleError(f"{path.name}: bad status")
        out[rate["id"]] = rate
    return out
