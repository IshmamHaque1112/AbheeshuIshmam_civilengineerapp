"""Check agent text. Agents cannot add unsupported numbers or claim approval."""
import json, re

FORBIDDEN = re.compile(r"\b(compliant|complies|comply|conforms?|approved|allowed|permitted|permissible|acceptable|safe|buildable|up to code|passes|passed"
                       r"|proceed\w*|go ahead|ready (to|for) (build|construct)\w*|cleared?( to| for)?|signed? off"
                       r"|meets? (the |all )?(code|rule|limit|requirement|standard)s?)\b", re.I)
LABEL_CLAIM = re.compile(r"\b(probably (standard|custom)|standard (layout|corner|ramp)|custom (design|layout|ramp))\b", re.I)
NUMBER = re.compile(r"(?<![A-Za-z0-9.-])\d+(?:\.\d+)?")


def _norm(text: str) -> str:
    return f"{float(text):g}"


def allowed_numbers(payload) -> set[str]:
    return {_norm(n) for n in NUMBER.findall(json.dumps(payload, default=str))}


def check_text(text: str, payload, labels_off: bool = False) -> list[str]:
    problems = []
    if FORBIDDEN.search(text):
        problems.append("Uses a banned approval or permission word. Describe the evidence instead.")
    if labels_off and LABEL_CLAIM.search(text):
        problems.append("States a corner label that the checks haven't supported.")
    allowed = allowed_numbers(payload)
    extra = sorted({_norm(n) for n in NUMBER.findall(text)} - allowed)
    if extra:
        problems.append(f"Uses numbers that are not in the validated record: {extra}.")
    return problems
