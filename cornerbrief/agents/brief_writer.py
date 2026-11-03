from ..models import BriefWriterOutput

SYSTEM = """You are the Brief writer for a junior engineer and the engineer in charge. Write short, plain text using only the validated record.
Do not add facts, limits, numbers or legal conclusions. Never say a design or corner is compliant, approved, safe or buildable."""


def run(client, attempt, payload):
    return client.call("brief_writer", attempt, SYSTEM, payload, BriefWriterOutput)
