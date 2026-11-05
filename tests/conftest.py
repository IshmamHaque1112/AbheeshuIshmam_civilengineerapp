import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.dont_write_bytecode = True

# A person's .env must not change test results or let tests call a live service.
import cornerbrief.app  # noqa: E402,F401  Loads .env first, so the settings below win
for name in ("ANTHROPIC_API_KEY", "SHOW_DOLLARS", "SHOW_LABELS_AND_PLANS", "OPEN_LIBRARY_CONTACT", "EMAIL_ENABLED", "EMAIL_ALLOWLIST",
             "EMAIL_FROM", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_PORT"):
    os.environ.pop(name, None)
os.environ["DEMO_MODE"] = "true"


import pytest

@pytest.fixture
def planning_release(tmp_path, monkeypatch):
    import json
    import cornerbrief.config as config
    release = tmp_path / "test-only-planning-release.json"
    release.write_text(json.dumps(dict(decision="enable provisional concepts", reviewed_by="Test fixture only",
        reviewed_on="2026-01-01", tested_commit="0" * 40, evidence_report="Synthetic test evidence only",
        r28_cases={str(i): "pass" for i in range(1, 11)})))
    monkeypatch.setattr(config, "PLANNING_RELEASE", release)
    return release
