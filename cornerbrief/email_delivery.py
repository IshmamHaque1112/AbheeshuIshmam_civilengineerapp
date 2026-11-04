"""Send-only delivery. No inbound mail. Dry run saves the message locally."""
import json, os, re, smtplib, ssl, time
from email.message import EmailMessage
from .paths import OUTBOX

SETTINGS = ["EMAIL_FROM", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]


class EmailBlocked(Exception):
    pass


class DryRunProvider:
    def send(self, message: dict) -> str:
        OUTBOX.mkdir(exist_ok=True)
        path = OUTBOX / f"{int(time.time() * 1000)}_{re.sub(r'[^a-z0-9]', '_', message['to'].lower())}.json"
        path.write_text(json.dumps(message, indent=1), encoding="utf-8")
        return f"Saved locally as {path.name}. No email left this computer."


class SmtpProvider:
    """Works with email services that offer SMTP. Settings come only from the environment."""

    def __init__(self):
        missing = [k for k in SETTINGS if not os.environ.get(k)]
        if missing:
            raise EmailBlocked("Sending is turned on, but these settings are missing: " + ", ".join(missing) + ". Set EMAIL_ENABLED=false for a dry run.")

    def send(self, message: dict) -> str:
        mail = EmailMessage()
        mail["From"], mail["To"], mail["Subject"] = os.environ["EMAIL_FROM"], message["to"], message["subject"]
        mail.set_content(message["body"])
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            server.send_message(mail)
        return f"Sent to {message['to']}."


def allowlist() -> set[str]:
    return {a.strip().lower() for a in os.environ.get("EMAIL_ALLOWLIST", "").split(",") if a.strip()}


def send_brief(run: dict, to: str, body: str, provider=None) -> str:
    if not run.get("approval"):
        raise EmailBlocked("A person must release this packet before it can be emailed.")
    if not isinstance(to, str) or to.strip().lower() not in allowlist():
        raise EmailBlocked("This address isn't on the test allowlist. Add it to EMAIL_ALLOWLIST.")
    if provider is None:
        enabled = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
        provider = SmtpProvider() if enabled else DryRunProvider()
    message = {"to": to.strip(), "subject": f"CornerBrief for review: {run['corner']['label']}", "body": body}
    return provider.send(message)
