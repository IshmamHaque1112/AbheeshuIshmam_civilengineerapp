import os
from .paths import ROOT


def load_env():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key.strip(), value)


def labels_enabled() -> bool:
    """Standard or custom labels and concept plans stay off until the adversarial suite passes and a person turns them on."""
    return os.environ.get("SHOW_LABELS_AND_PLANS", "false").lower() == "true" and planning_authorized()


PLANNING_RELEASE = ROOT / "docs" / "PLANNING-RELEASE.json"


def planning_authorized() -> bool:
    """A switch alone cannot attest that people reviewed R28. No release is shipped."""
    import json
    import re
    from datetime import date
    try:
        release = json.loads(PLANNING_RELEASE.read_text(encoding="utf-8"))
        if not isinstance(release, dict):
            return False
        return (release.get("decision") == "enable provisional concepts"
                and isinstance(release.get("reviewed_by"), str) and bool(release["reviewed_by"].strip())
                and date.fromisoformat(release["reviewed_on"]) <= date.today()
                and bool(re.fullmatch(r"[a-f0-9]{40}", release.get("tested_commit", "")))
                and release.get("r28_cases") == {str(i): "pass" for i in range(1, 11)}
                and isinstance(release.get("evidence_report"), str)
                and bool(release["evidence_report"].strip()))
    except (OSError, ValueError, TypeError, KeyError):
        return False
