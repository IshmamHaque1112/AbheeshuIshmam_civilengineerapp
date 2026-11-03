from ..models import RecordsOutput

SYSTEM = """You are the Records agent for a pre-design corner review. Organize the supplied evidence.
Copy each key and label exactly as supplied unless the record proves otherwise. Never guess a missing value.
Write a short plain summary. Do not state rule limits or decide whether data is sufficient."""


def run(client, attempt, payload):
    return client.call("records", attempt, SYSTEM, payload, RecordsOutput, tier="fast")
