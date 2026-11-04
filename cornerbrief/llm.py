"""Agent model calls. Demo mode replays saved responses, so it makes no API calls."""
import hashlib, json, os
from pydantic import ValidationError
from .paths import CACHE, DATA


class AgentOutputError(Exception):
    pass


def parse_output(text: str, schema):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return schema.model_validate_json(text)
    except ValidationError as exc:
        raise AgentOutputError(str(exc)) from exc


class ReplayClient:
    mode = "demo replay"

    def __init__(self, corner_key: str):
        self.dir = DATA / "replay" / corner_key

    def call(self, agent, attempt, system, payload, schema, tier="main"):
        path = self.dir / f"{agent}_{attempt}.json"
        if not path.exists():
            path = self.dir / f"{agent}_0.json"
        if not path.exists():
            raise AgentOutputError(f"No saved response for the {agent} agent.")
        text = path.read_text(encoding="utf-8")
        return parse_output(text, schema), {"input_tokens": 0, "output_tokens": 0, "replayed": True}


class OfflineClient:
    """Runs with no API key when no saved responses fit the inputs. It writes no analysis, so only checked results appear."""
    mode = "offline, no agents"
    runs_review = False

    def call(self, agent, attempt, system, payload, schema, tier="main"):
        usage = {"input_tokens": 0, "output_tokens": 0, "offline": True}
        if agent == "records":
            labels = [{"key": e["key"], "label": e["label"], "note": ""} for e in payload["evidence"]]
            return schema(summary="Loaded from saved records. No agent analysis was run.", labels=labels), usage
        return schema(summary="No agent analysis was run for this version of the packet.",
                      findings_narrative="The records are shown with their labels. See the sections below for what is unknown.",
                      engineer_note="Use the site visit list to see what still needs to be measured or confirmed."), usage


class LiveClient:
    mode = "live"

    def __init__(self):
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("Install the anthropic package to use live agents.") from exc
        self.client = anthropic.Anthropic()

    def call(self, agent, attempt, system, payload, schema, tier="main"):
        model = os.environ.get("FAST_MODEL" if tier == "fast" else "MAIN_MODEL")
        if not model:
            raise RuntimeError("Set FAST_MODEL and MAIN_MODEL in .env.")
        content = json.dumps(payload, sort_keys=True, default=str)
        key = hashlib.sha256(f"{model}|{agent}|{attempt}|{system}|{content}".encode()).hexdigest()
        path = CACHE / "agents" / f"{key}.json"
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            return parse_output(saved["text"], schema), {"input_tokens": 0, "output_tokens": 0, "cached": True}
        schema_text = json.dumps(schema.model_json_schema())
        try:
            response = self.client.messages.create(
                model=model, max_tokens=4000,
                system=f"{system}\nReturn only JSON matching this schema, with no other fields:\n{schema_text}",
                messages=[{"role": "user", "content": content}])
        except Exception as exc:  # A failed call counts as an unfinished review, not a crash
            raise AgentOutputError(f"The call to the {agent} agent failed ({type(exc).__name__}).") from exc
        text = "".join(b.text for b in response.content if b.type == "text")
        output = parse_output(text, schema)  # Only valid output is saved, so a bad reply can be retried
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"text": text}), encoding="utf-8")
        return output, {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}


def get_client(corner: dict, inputs_changed: bool = False):
    """Saved responses describe a corner's original records, so they aren't reused once its inputs change."""
    demo = os.environ.get("DEMO_MODE", "true").lower() != "false" or not os.environ.get("ANTHROPIC_API_KEY")
    if not demo:
        return LiveClient()
    if inputs_changed or corner.get("data_kind") != "SAMPLE DATA":
        return OfflineClient()
    return ReplayClient(corner["key"])
