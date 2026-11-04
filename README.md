# CornerBrief

CornerBrief prepares a NYC street corner for an engineer's review. It shows what is known, what is missing and what to check on site. It is a demo for pre-design investigation. It does not decide compliance, approve a design or represent NYC.

## Run it on Windows

Open PowerShell in this folder, then run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
python -m cornerbrief
```

Open http://127.0.0.1:8000 in your browser. If PowerShell blocks the activate script, run `Set-ExecutionPolicy -Scope Process RemoteSigned` and try again.

On a Mac, use Python 3.10 or newer. For example, if Homebrew installed Python 3.12, run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m cornerbrief
```

## Run the demo

No API key is needed. The sample corners use made-up records and saved agent responses. Every corner ends in one of two states:

1. **Sample corner A, Queens:** Checks the evidence supports, with the source and math for each calculation.
2. **Sample corner B, Brooklyn:** Checks the evidence supports, with a utility vault and catch basin to review and one Skeptic rework.
3. **Real test corner:** Appears only after you save one. It runs offline and stops until its units and road owner are confirmed.
4. **Sample corner C, Bronx:** Stop: evidence still needed, because it was rebuilt after its survey and has a placeholder value.

Enter a name and select **Release packet** to turn on the download. Releasing is not approval.

To print the results without the browser, run `python scripts/run_demo.py`.

## Add site measurements and rerun

Under **Add site measurements**, enter who measured, the date and any values you have, with an optional photo for each. **Rerun the check** then shows what changed. Each value is labeled as measured on site. A value measured before the corner's latest construction stays stale.

Each rerun creates a new packet that needs its own release. Choosing a corner again starts from its original records. Without an API key, a rerun still runs every Python check, but the Skeptic review doesn't run, because the saved responses describe the original records. No label or plan can appear until a review finishes.

## Labels and concept plans

"Probably standard," "probably custom," likely ramp types and concept plans are off by default. Set `SHOW_LABELS_AND_PLANS=true` only after the adversarial suite in `tests/test_v3.py` passes and you've decided to turn them on. Even then, they appear only with complete evidence, a finished review, verified rules and no exceeded limit.

## Why results say "unknown"

A rule counts as verified only after a named person checks it against its source. No one has yet, so every limit result is "unknown," with the math shown as an "unreviewed calculation." To record a review, run:

```powershell
python scripts/review_rule.py NYC-ADMIN-19-112-SLOPE --reviewer "Full Name"
```

That rule can then return "limit exceeded" or "no conflict found." A calculated value above a limit stops the check unless the record shows a constraint that explains it.

## Add a real test corner

```powershell
pip install truststore
python scripts/fetch_corners.py --borough QUEENS --street THOMSON
python scripts/fetch_corners.py --save real_test CORNER_ID
```

The first command writes `docs/candidates.md`. The saved corner is added to the demo list, and the sample corners don't change. Limits stay "unknown" until its measurement units are documented in `data/data_dictionary.yaml` and its road owner is confirmed.

## Connect live agents or email later

- **Live agents:** Copy `.env.example` to `.env`, add your API key, set `DEMO_MODE=false` and run `pip install anthropic`.
- **Email:** Create the address and an email service account, then fill in `EMAIL_ALLOWLIST`, `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` and `SMTP_PASSWORD` in `.env`. Set `EMAIL_ENABLED=true` to send. A person must release each packet, and every recipient must be on the allowlist. The email form stays hidden until `EMAIL_ALLOWLIST` is set.
- **Dollar figures:** They are hidden by default for the city demo. Set `SHOW_DOLLARS=true` to show them.

## How it's organized

| Part | Location |
| --- | --- |
| Rules, one file each | `rules/federal`, `rules/nyc`, `rules/nys` |
| Which-rule-applies decisions | `rules/precedence` |
| Cost and labor rates | `rates` |
| Sample corners and saved agent responses | `data/corners`, `data/replay` |
| Saved real corners | `data/live` |
| Run logs, including token use | `runs` (created when you run it) |
| Email dry runs | `outbox` (created when you use it) |

Regular code handles data checks, rule selection, limit checks, geometry, quantities, cost and labor hours. Agents only organize records, propose options, challenge claims and write text. Their output must match a strict format, and checks reject unsupported numbers and claims such as "compliant."

## Known limits

- **Sample data:** The included corners are made up. They are not real NYC locations.
- **Rule review:** No named person has reviewed any rule or which-rule-applies decision yet.
- **Live agents:** The live API path hasn't been run with a real key. Tests use saved or scripted responses.
- **Real data fetch:** `scripts/fetch_corners.py` hasn't run against the NYC portal, because the build environment blocks it. Its filter and sorting logic are tested.
- **Ramp data age:** The ramp measurement dataset was last updated in October 2021.
- **Open Library:** It hasn't been called live, and it's hidden until `OPEN_LIBRARY_CONTACT` is set. It stores citation details only and sends no book text to a model.
- **Email:** It defaults to a dry run that saves messages to `outbox`. Sending through SMTP is built and tested against a fake server, but it has never sent a real message. Inbound email isn't supported.
- **Cost and labor:** All rates are placeholders, not market prices.
- **Stack changes:** The app uses Starlette (FastAPI's foundation) and a small built-in 3D renderer instead of FastAPI and three.js, because those packages weren't available during the build.
- **Python version:** Tests ran on Python 3.13. Use Python 3.10 or newer.

## Rules that still need sources

These return "unknown" until a person adds the exact text and limit:

- H-1011 sheets 2 to 9, so case-specific details aren't checked.
- 2025 NYS Building Code and Residential Code limits. These don't apply to NYC corners.

H-1011 Table 1 and its general notes come from `docs/sources/H-1011-1.pdf`. Surveyed ramps are compared with its work acceptance limits. Its stricter design limits appear only under "If this corner is rebuilt." The ADA rules use a third-party reproduction of the text, so confirm them on ada.gov.
