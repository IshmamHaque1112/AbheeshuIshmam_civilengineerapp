"""Check agent text. Agents cannot add unsupported numbers or claim approval."""
import json, re

FORBIDDEN = re.compile(r"\b(compliant|complies|comply|approved|allowed|safe|buildable|up to code|passes|passed)\b", re.I)
LABEL_CLAIM = re.compile(r"\b(probably (standard|custom)|standard (layout|corner|ramp)|custom (design|layout|ramp))\b", re.I)
NUMBER = re.compile(r"(?<![A-Za-z0-9.-])\d+(?:\.\d+)?")


def _norm(text: str) -> str:
    return f"{float(text):g}"


def allowed_numbers(payload) -> set[str]:
    return {_norm(n) for n in NUMBER.findall(json.dumps(payload, default=str))}


def check_text(text: str, payload, labels_off: bool = False) -> list[str]:
    problems = []
    match = FORBIDDEN.search(text)
    if match:
        problems.append(f'Uses the banned claim "{match.group(0)}".')
    label = LABEL_CLAIM.search(text) if labels_off else None
    if label:
        problems.append(f'Uses the corner label "{label.group(0)}" while labels are off.')
    allowed = allowed_numbers(payload)
    extra = sorted({_norm(n) for n in NUMBER.findall(text)} - allowed)
    if extra:
        problems.append(f"Uses numbers that are not in the validated record: {extra}.")
    return problems
