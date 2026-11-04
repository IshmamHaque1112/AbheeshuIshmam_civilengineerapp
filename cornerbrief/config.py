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
    return os.environ.get("SHOW_LABELS_AND_PLANS", "false").lower() == "true"
