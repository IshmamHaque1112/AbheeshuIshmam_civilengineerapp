# CornerBrief Mac run check

Checked November 3, 2026 on Darwin 27.0.0, arm64.

**Result: CornerBrief does not run in the environment created by the requested commands on this Mac.** Dependency installation succeeded, but Python 3.9.6 prevents test collection, demo execution, and web startup. No app code, rules, data, or tests were changed.

## Environment and installation

- `python3 --version`: `Python 3.9.6` (Apple Command Line Tools Python).
- `python3 -m venv .venv`: exit 0.
- `.venv/bin/python --version`: `Python 3.9.6`.
- `.gitignore` already contains `.venv/`; `git check-ignore .venv/bin/python` confirmed it is ignored. No edit was needed.
- `.venv/bin/pip install -r requirements.txt`: initial sandbox attempt exited 1 because network name resolution failed. Retried with approved network access; exit 0.
- Installed direct requirements: Starlette 0.49.3, Uvicorn 0.39.0, Pydantic 2.13.5, PyYAML 6.0.3, pytest 8.4.2, plus their dependencies.

The initial install reported:

```text
Failed to establish a new connection: [Errno 8] nodename nor servname provided, or not known
ERROR: Could not find a version that satisfies the requirement starlette>=0.37 (from versions: none)
ERROR: No matching distribution found for starlette>=0.37
```

Cause: sandbox network restrictions, resolved by retrying with network access. The first attempt also warned that the pip cache directory was not writable and disabled caching. The successful attempt warned that pip 21.2.4 was older than available pip 26.0.1; this did not prevent installation.

## Tests

Command: `.venv/bin/python -m pytest -q`

Exit code: **2**. Counts: **0 passed, 0 failed, 1 collection error; no tests executed**. This is an unsuccessful test run, not a passing suite.

```text
_____________________ ERROR collecting tests/test_flow.py ______________________
tests/test_flow.py:7: in <module>
    from cornerbrief.cost import build_cost
cornerbrief/cost.py:10: in <module>
    def build_cost(takeoff: dict, rates: dict, today: date | None = None) -> dict:
E   TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.22s
```

## Three-corner demo

Command: `.venv/bin/python scripts/run_demo.py`

Exit code: **1**. The script stopped during imports, before processing any corner:

```text
scripts/run_demo.py:10 -> cornerbrief/orchestrator.py:14
-> cornerbrief/planning.py:2 -> cornerbrief/cost.py:10
    def build_cost(takeoff: dict, rates: dict, today: date | None = None) -> dict:
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

| Corner | Required behavior | Observed result |
| --- | --- | --- |
| Standard | Suggest a likely ramp type | Not confirmed: import failure before any corner output. |
| Constrained | Flag `probably custom` | Not confirmed: import failure before any corner output. |
| Missing/stale | Refuse a design and produce a site-visit list | Not confirmed: import failure before any corner output. |

These behaviors remain unverified at runtime; expected behavior from source or documentation is not counted as a successful demo.

## Web check

Started `.venv/bin/python -m cornerbrief` in the background with its output redirected to a temporary log, waited **3 seconds**, then requested `http://127.0.0.1:8000/` using curl with a 10-second timeout and header/body capture. Repeated outside the sandbox to rule out sandbox restrictions.

- Server exited **1** during startup, before listening.
- Curl exited **7**, reporting HTTP status **000**, not HTTP 200.
- No page HTML was received.

```text
curl: (7) Failed to connect to 127.0.0.1 port 8000 after 0 ms: Couldn't connect to server
```

Server traceback ends at:

```text
cornerbrief/app.py:11 -> cornerbrief/orchestrator.py:14
-> cornerbrief/planning.py:2 -> cornerbrief/cost.py:10
    def build_cost(takeoff: dict, rates: dict, today: date | None = None) -> dict:
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

The initial sandbox background launch also printed `zsh:1: nice(5) failed: operation not permitted`; the approved retry outside the sandbox removed that warning but reproduced the Python error. Both server processes had already exited when cleanup ran. A final `lsof -nP -iTCP:8000 -sTCP:LISTEN` returned no listener (exit 1); no server was left running.

## Cause and likely fix

`cornerbrief/cost.py:10` evaluates the `date | None` type annotation at import time. That union syntax requires Python 3.10 or newer; Python 3.9.6 raises the exact TypeError above. All three runtime checks are blocked by this same incompatibility. README.md already specifies Python 3.10 or newer.

`/opt/homebrew/bin/python3.12 --version` returns **Python 3.12.16**, so a suitable interpreter is already available on this Mac. The likely fix is to recreate `.venv` explicitly with `/opt/homebrew/bin/python3.12 -m venv .venv`, reinstall requirements, and repeat the tests, demo, and web check. Move aside or remove the existing Python 3.9 virtual environment first to ensure a clean environment. This fix was not applied; the requested failing run is recorded here without patching code. Successful checks on Python 3.12 are not claimed.

No visual changes or preview export were made: this check concerns a backend Python application, and the requested edit scope permits only docs and a necessary `.gitignore` change. A static browser export would not validate this backend runtime.
