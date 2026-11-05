"""Reviewer traces. No environment, transport headers or credentials are recorded."""
import re

SECRET_KEY = re.compile(r"(?i)(api[_-]?key|authorization|password|secret|credential|access[_-]?token|refresh[_-]?token)")
DOLLARS = re.compile(r"\$\s*[-+]?\d[\d,.]*(?:\s*(?:million|billion|thousand))?|\bUSD\s*[-+]?\d[\d,.]*", re.I)

SECRET_TEXT = re.compile(r"(?i)(\bBearer\s+)[^\s\"']+|\b(?:sk-ant-|sk-)[A-Za-z0-9_-]+|((?:api[_-]?key|password|secret|authorization)[\"\']?\s*[=:]\s*[\"\']?)[^\s,;\"']+")


def redact(value, hide_cost=False):
    if isinstance(value, dict):
        # Legacy traces can include a full planning cost object. Keep only the nondollar presentation.
        if hide_cost and "cost" in value and isinstance(value["cost"], dict) and "lines" in value["cost"]:
            from .cost import hide_dollars
            value = {**value, "cost": hide_dollars(value["cost"])}
        return {str(k): "[redacted]" if SECRET_KEY.search(str(k)) else redact(v, hide_cost=hide_cost) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v, hide_cost=hide_cost) for v in value]
    if isinstance(value, str):
        return DOLLARS.sub("[dollar figure withheld]", SECRET_TEXT.sub(lambda m: (m.group(1) or m.group(2) or "") + "[redacted]", value))
    return value


class TracingClient:
    def __init__(self, client):
        self.client, self.calls = client, []
        self.mode = client.mode
        self.runs_review = getattr(client, "runs_review", True)

    def call(self, agent, attempt, system, payload, schema, tier="main"):
        event = dict(agent=agent, attempt=attempt, tier=tier,
                     request=dict(system=system, input=payload, response_schema=schema.model_json_schema()),
                     response=None, usage=None, status="failed")
        self.calls.append(event)
        try:
            output, usage = self.client.call(agent, attempt, system, payload, schema, tier)
            if usage.get("request"):
                event["request"]["provider_request"] = usage["request"]
            event.update(response=usage.get("response_text", output.model_dump()), usage=usage, status="returned")
            return output, usage
        except Exception as exc:
            if getattr(exc, "usage", None) and exc.usage.get("request"):
                event["request"]["provider_request"] = exc.usage["request"]
            event.update(response=getattr(exc, "response_text", None), usage=getattr(exc, "usage", None),
                         error="Agent request or response failed validation.")
            raise
        finally:
            clean = redact(event)
            event.clear()
            event.update(clean)


def public_trace(run):
    calls = run.get("trace_events")
    if calls is None:
        # Old saved runs contain payloads, but not the original full model request.
        calls = [dict(agent=e["agent"], attempt=e["attempt"], request={"input": e["input"], "note": "Legacy trace: system/schema not captured."},
                      response=e["output"], usage=e.get("usage"), error=e.get("error")) for e in run.get("agent_log", [])]
    validations = {(entry["agent"], entry["attempt"]): entry.get("error") for entry in run.get("agent_log", [])}
    result = []
    for call in calls:
        usage = call.get("usage") or {}
        origin = ("saved replay" if usage.get("replayed") else "deterministic offline" if usage.get("offline") else
                  "cached provider response" if usage.get("cached") else "actual provider" if usage.get("provider") else "unreported/client supplied")
        tokens = dict(input=usage.get("input_tokens"), output=usage.get("output_tokens"))
        result.append(redact({**call, "origin": origin, "tokens": tokens,
                              "validation_note": validations.get((call["agent"], call["attempt"])) or "Inspect the packet’s rejected output and review status; raw responses are diagnostic.",
                              "usage_note": "No provider call; zero tokens used by this run." if origin in ("saved replay", "deterministic offline", "cached provider response") else "Counts reported by the provider for this request." if origin == "actual provider" else "Actual provider usage unavailable; do not interpret missing counts as zero."}, hide_cost=True))
    return result
