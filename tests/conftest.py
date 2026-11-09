import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.dont_write_bytecode = True

# A person's .env must not change test results or let tests call a live service.
import cornerbrief.app  # noqa: E402,F401  Loads .env first, so the settings below win
for name in ("ANTHROPIC_API_KEY", "SHOW_DOLLARS", "SHOW_LABELS_AND_PLANS", "SHOW_ROADMAP_DEMOS", "OPEN_LIBRARY_CONTACT", "EMAIL_ENABLED", "EMAIL_ALLOWLIST",
             "EMAIL_FROM", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_PORT"):
    os.environ.pop(name, None)
os.environ["DEMO_MODE"] = "true"


def pytest_configure(config):
    config.addinivalue_line("markers", "demos_off: run with the roadmap demonstrations turned off")
