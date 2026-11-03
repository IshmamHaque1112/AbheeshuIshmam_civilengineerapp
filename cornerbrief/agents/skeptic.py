from ..models import SkepticOutput

SYSTEM = """You are the Skeptic for a pre-design corner review. Challenge weak sources, data conflicts and claims the evidence does not support.
Use severity "rework" and verdict "rework" only when the options must change. You cannot change a Python rule result or applicability decision."""


def run(client, attempt, payload):
    return client.call("skeptic", attempt, SYSTEM, payload, SkepticOutput)
