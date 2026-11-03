from ..models import SiteAnalystOutput

SYSTEM = """You are the Site analyst for a pre-design corner review. Propose likely ramp options and constraints using only
the supplied evidence, and cite evidence keys. Do not state rule limits, new measurements or any decision about whether a rule is met.
If a reviewer's challenges are supplied, address them. Never say a design is compliant, approved, safe or buildable."""


def run(client, attempt, payload):
    return client.call("site_analyst", attempt, SYSTEM, payload, SiteAnalystOutput)
