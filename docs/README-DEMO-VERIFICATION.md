# README presentation verification

November 11, 2026. Presentation scope: the latest `README.md`, based on Ishmam's
`main` at `7051b5b`, including the PRD persona update merged in PR #13.
`docs/PRD.md` supplies the requirement IDs; the README's four-step workflow is
the presentation order. This is software verification, not engineer review or
evidence that the promised time savings have been measured.

## Delivered in this branch

- Hardened the documented-dimension gate. Unsupported/missing units, non-finite
  or non-numeric values, booleans, placeholders and nonpositive lengths cannot
  produce geometry, quantities or a draft plan. A slope is a percentage, including
  zero; a signed recorded slope keeps the existing absolute-magnitude convention.
  One invalid dimension still blocks the entire concept. No evidence is promoted.
- Dimension readiness now displays each row's source, evidence date and unit
  documentation alongside its recorded value, status and reason, both in the
  browser and in the released Markdown packet.
- Rebuilt Helix Output from the real application and deterministic Python
  results. It includes all four README demo choices, including the saved real
  Van Dam Street/Thomson Avenue stop case. Real records stay labeled separately
  from sample data. Export uses replay/offline clients explicitly and never a
  paid model, even if live settings exist on the machine.
- Added regressions for rejected geometry inputs and an actual browser journey:
  stale measurement -> one dated replacement -> unrelated measurements remain
  stale -> fresh packet release -> download preserves provenance.

## Present the README's four steps

| Step | What can be shown | Evidence and boundaries |
| --- | --- | --- |
| 1. Find the corner | Four offline choices: Queens sample, Brooklyn sample, real Van Dam/Thomson, Bronx sample. Borough/street search remains available in the local app. | `test_demo_list_shows_the_real_corner_in_order`, search/loading/error and late-response tests in `tests/test_browser.py`. Live NYC availability was not revalidated in this run; tests use saved or scripted responses. Exact-intersection search remains proposed. |
| 2. Investigate the evidence | Sources/dates/labels, individual stopped checks, rule quotes and unreviewed math, site visit list, dated field entries, change reporting, release and download. | `tests/test_flow.py`, `tests/test_v3.py`, `tests/test_web_and_fetch.py`; new `test_dimension_provenance_survives_field_rerun_and_packet_download`. Unreviewed results remain unknown; release is not engineering approval. |
| 3. Develop a 3D concept | Inspect dimension readiness in a packet; then open the explicitly synthetic preview, change dimensions and inspect geometry and quantities. | `tests/test_readiness.py`, `tests/test_preview.py`, preview browser tests. Real packet concepts stay off by default and behind all evidence/review gates. Typed-in synthetic dimensions never become field evidence. |
| 4. Prepare construction planning | Show the existing seven-step draft sequence and missing-resource list in the synthetic preview; change a dimension to show the old draft needs recalculation, then rebuild. | `tests/test_m2.py`, `test_preview_draft_needs_recalculation_until_rebuilt`. Durations, crews and availability remain unknown. Fictional contractor and structures demos remain off by default. |

Suggested rehearsal: Queens supported-checks view -> Brooklyn constraints -> real
Van Dam/Thomson stop and its 2024 permit -> Bronx stale evidence -> a sample field
rerun and release/download -> synthetic preview and draft recalculation.
Explain sample fixtures before using them. A test-entered measurement is a
software demonstration, not an actual field survey. Do not present the synthetic
preview as a design that meets the rules.

## PRD coverage carried forward

These groups identify implemented and exercised software behavior, not blanket
acceptance of professional or human-research requirements.

| Requirements | Verification |
| --- | --- |
| R1–R3, R19–R20, R26–R27: choices, evidence, freshness, units, real search | Core/data/evidence tests, `tests/test_nyc_datasets.py`, HTTP and browser tests. Four saved demo choices work without a key. New gate tests close unsupported-unit and invalid-value paths. |
| R4–R6, R15–R18, R28: outcome, rule applicability, review/retry/adversarial gates | `tests/test_v3.py`, `tests/test_flow.py`, `tests/test_bugfixes.py`, `tests/test_p1.py`. Preserve Ishmam's Nov 10 corner-level outcome plus individual stopped checks. No rule review is invented. |
| R7–R10, R30–R31: packet, release, notices, measurements/photos/rerun | Existing HTTP/browser tests plus new source/date/unit-documentation coverage through rerun and actual download. |
| R11, R21–R25: gated concepts, quantities, resources | Existing planning/gate tests and new invalid-dimension regressions. No switch is enabled by this change. Missing production rates, crews and durations stay unknown. |
| R12–R14: email, reading, traces | Existing allowlist/dry-run/fake SMTP, reading and trace tests. No real email was sent, no live paid agent was called; these optional services stay off. |
| R29: real junior engineer and reviewer role test | Not done by this run. Ishmam's Nov 10 decision defers it until after the presentation. |
| R32–R36: synthetic dimensions, interaction, invalid-input feedback, revisions, separation | Existing preview, M2 and real Chromium browser tests, including edit/orbit/zoom/pan, invalid edits and stale-draft marking. |

## Observed validation

- Fresh Python 3.12 virtual environment, declared requirements and Playwright
  installed; Chromium installed and actually executed.
- Before edits: **517 passed**, including browser tests.
- Geometry regression tests before the fix: **10 failed, 31 passed**. These show
  the unsafe acceptance/crash paths and replace the old test that tolerated an
  unsupported unit reaching a concept model.
- Final full suite: **528 passed in 37.04 seconds**, no skipped tests. Command:
  `.venv/bin/python -m pytest -q -rs`. Localhost and Chromium execution were
  permitted; the sandbox alone otherwise rejects server binds.
- Actual export rebuilt with `.venv/bin/python scripts/export_ui.py` and exercised
  in Chromium without backend calls, including the real saved corner.
- `git diff --check` passed.

## Try it locally

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt playwright
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q -rs
DEMO_MODE=true .venv/bin/python -m uvicorn cornerbrief.app:app --host 127.0.0.1 --port 8008
```

Open `http://127.0.0.1:8008/` for the working application and
`http://127.0.0.1:8008/preview.html` for editable synthetic geometry. The server
runs in the terminal that started it; Ctrl+C stops it. No `.env` or credential
is needed for these saved-data demonstrations.

Helix's `.helix/output/index.html` is the actual static export, not the full
backend. Search, field writes, release/download and synthetic dimension edits
need the local server; their static limitations remain explicit.

## Still owned by people or later milestones

- No named engineer has reviewed the rules. Every unreviewed limit stays unknown.
- Real role testing and measured time savings are not established. Ishmam owns
  the manual timing baseline; this run creates no invented timings or surveys.
- The Manhattan 1 Avenue/East 60 Street example is described in the README but
  is not a saved offline choice in this checkout. It needs a successful real
  lookup/cache before presenting it; the README's four saved choices above are
  the verified offline path.
- Contractor-persona interviews, real company resources/rates, scheduling,
  new proposed design dimensions and structural engineering remain future work.
  This change does not turn fictional demonstrations into supported features.
- Tests do not validate the README's citywide estimates, job-posting facts,
  legal interpretation, live source uptime or professional usability.

Historical reports such as `M2A-IMPLEMENTATION.md` describe earlier snapshots.
Their statements that readiness is not on screen, draft recalculation is absent,
or stop semantics await Ishmam's decision are superseded by the current README,
Nov 10 PRD decisions and this verification.
