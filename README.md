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

## Run the three-corner demo

No API key is needed. These corners use made-up sample records and saved agent responses.

1. **Sample corner A:** Shows a likely standard layout, rule math, the concept model and the estimate.
2. **Sample corner B:** Shows a probable custom design, recorded obstacles and one Skeptic rework.
3. **Sample corner C:** Stops because of stale and placeholder data, then produces a site visit list.

Enter a name and select **Release brief** to turn on the download. Releasing a brief doesn't approve a design.

To print all three results without the browser, run `python scripts/run_demo.py`.

## Connect the app's email later

Create the address and an email service account, then fill in `EMAIL_ALLOWLIST`, `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` and `SMTP_PASSWORD` in `.env`. Set `EMAIL_ENABLED=true` to send. A person must still release each brief, and every recipient must be on the allowlist.

## Use real NYC corners

```powershell
pip install truststore
python scripts/fetch_corners.py
python scripts/fetch_corners.py --save standard CORNER_ID
```

The first command writes `docs/candidates.md`. Repeat the save command for `constrained` and `missing_or_stale`. To go back to a sample corner, delete its file from `data/live`.

Real corners need live agents:

1. Copy `.env.example` to `.env`.
2. Add your API key and set `DEMO_MODE=false`.
3. Run `pip install anthropic`.

Real corners show limit results as "unknown" until you confirm units. Find the dataset's documentation, then change each confirmed field in `data/data_dictionary.yaml` to `unit_status: documented`.

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
- **Live agents:** The live API path hasn't been run with a real key. Tests use saved or scripted responses.
- **Real data fetch:** `scripts/fetch_corners.py` hasn't run against the NYC portal, because the build environment blocks it. Its sorting logic is tested.
- **Open Library:** It hasn't been called live. A test uses a fake response. It stores citation details only and sends no book text to a model.
- **Email:** It defaults to a dry run that saves messages to `outbox`, because the app's address doesn't exist yet. Sending through a service's SMTP settings is built and tested against a fake server, but it has never sent a real message. Inbound email isn't supported.
- **Cost and labor:** All rates are placeholders, not market prices.
- **Stack changes:** The app uses Starlette (FastAPI's foundation) and a small built-in 3D renderer instead of FastAPI and three.js, because those packages weren't available during the build.
- **Python version:** Tests ran on Python 3.13. Use Python 3.10 or newer.

## Rules that still need sources

These return "unknown" until a person adds the exact text and limit:

- H-1011 ramp slopes, landing limits and flare limits. The current sheet is [H-1011-1](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-1.pdf), which the build environment couldn't open. Save it as `docs/sources/H-1011-1.pdf` so its values can be added.
- 2025 NYS Building Code and Residential Code limits. These don't apply to NYC corners.

Rules marked `verified` were checked against linked text through a web fetch on November 3, 2026. No person has reviewed them yet, so `reviewed_by` is empty, and the ADA rules use a third-party reproduction of the text. An engineer should review the rules and precedence decisions before anyone relies on them.
