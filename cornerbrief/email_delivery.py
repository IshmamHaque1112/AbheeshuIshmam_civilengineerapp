"""Send-only delivery. No inbound mail. Dry run saves the message locally."""
import json, os, re, time
from .paths import OUTBOX


class EmailBlocked(Exception):
    pass


class DryRunProvider:
    def send(self, message: dict) -> str:
        OUTBOX.mkdir(exist_ok=True)
        path = OUTBOX / f"{int(time.time() * 1000)}_{re.sub(r'[^a-z0-9]', '_', message['to'].lower())}.json"
        path.write_text(json.dumps(message, indent=1), encoding="utf-8")
        return f"Saved locally as {path.name}. No email left this computer."


def allowlist() -> set[str]:
    return {a.strip().lower() for a in os.environ.get("EMAIL_ALLOWLIST", "").split(",") if a.strip()}


def send_brief(run: dict, to: str, body: str, provider=None) -> str:
    if not run.get("approval"):
        raise EmailBlocked("A person must approve this brief before it can be emailed.")
    if to.strip().lower() not in allowlist():
        raise EmailBlocked("This address isn't on the test allowlist. Add it to EMAIL_ALLOWLIST.")
    if os.environ.get("EMAIL_ENABLED", "false").lower() == "true" and provider is None:
        raise EmailBlocked("Sending is turned on, but no email service is connected. Set EMAIL_ENABLED=false for a dry run.")
    message = {"to": to.strip(), "subject": f"CornerBrief for review: {run['corner']['label']}", "body": body}
    return (provider or DryRunProvider()).send(message)
