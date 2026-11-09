# CornerBrief

CornerBrief assembles a traceable investigation packet for a NYC street corner, shows which checks the evidence supports, and tells an engineer exactly what evidence is still needed. It is a demo for pre-design investigation. It does not decide compliance, approve a design or represent NYC.

The current product requirements are in [`docs/PRD.md`](docs/PRD.md). The demo is on November 12, 2026.

## User stories

1. As a DDC junior engineer preparing a corner, I need to see every record for that corner in one place, labeled measured, assumed or missing, so that I don't spend time cross-checking three datasets by hand.
2. As a DDC junior engineer, I need a list of exactly what is missing or out of date before I leave the desk, so that I make one site visit instead of finding the gaps on site.
3. As a DDC junior engineer back from the field, I need to add what I measured and rerun the check, so that the brief reflects the corner as it is today.
4. As an Engineer-In-Charge reviewing a brief, I need every supported check tied to its rule, section and source, and a clear "stop" wherever evidence is incomplete, so that I never sign off on a result I can't trace.

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

## Run it on a Mac

Use Python 3.10 or newer, because Apple's Python 3.9 won't run the app. For example, if Homebrew installed Python 3.12, run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m cornerbrief
```

Then open http://127.0.0.1:8000 in your browser.

## Run the tests

`python -m pytest -q` runs every test. Tests ignore your `.env`, so they never call a live service. The browser checks in `tests/test_browser.py` skip unless Playwright and Chromium are installed:

```bash
pip install playwright
python -m playwright install chromium
```

## Run the demo

No API key is needed, and the demo stays in this mode while `DEMO_MODE=true`. The sample corners use made-up records and saved agent responses. Every corner ends in one of two states:

1. **Sample corner A, Queens:** Checks the evidence supports, with the source and math for each calculation.
2. **Sample corner B, Brooklyn:** Checks the evidence supports, with a utility vault and catch basin to review and one Skeptic rework.
3. **Real test corner:** Corner 1024569, Van Dam Street and Thomson Avenue, from NYC Open Data. It uses saved records, so it works offline. It stops because a 2024 pedestrian ramp permit is located at each ramp, after the 2018 survey. Its road owner is assumed, not confirmed.
4. **Sample corner C, Bronx:** Stop: evidence still needed, because it was rebuilt after its survey and has a placeholder value.

Enter a name and select **Release packet** to turn on the download. Releasing is not approval. **Download site visit list** needs no release, because it lists only what to measure or confirm and contains no limit results.

To print the results without the browser, run `python scripts/run_demo.py`.

## Add site measurements and rerun

Under **Add site measurements**, enter who measured, the date and any values you have, with an optional photo for each. **Rerun the check** then shows what changed. Each value is labeled as measured on site. A value measured before the corner's latest construction, before ramp permit work at that ramp could end, or before the survey it replaces stays stale.

Each rerun creates a new packet that needs its own release. The tab keeps showing the newest version when you switch corners or reload, and **Start over from the original records** clears it. A new tab starts from the original records. In demo mode, a rerun still runs every Python check, but the Skeptic review doesn't run, because the saved responses describe the original records. No label or plan can appear until a review finishes.

## 3D preview

Select **3D preview (synthetic)** at the top of the app, or open `/preview.html`. Change the ramp and landing dimensions to update the model and provisional quantities, then drag to rotate, scroll to zoom, and shift-drag or right-drag to pan. These dimensions are made up. They aren't saved, can't reach a packet, label or plan, and get no rule check. If a value is missing or out of range, the model and quantities stay at the last valid revision and are marked **Not updated** until you fix it. The page also lists which inputs are synthetic, which are assumed and what isn't modeled. Where this is headed is in [the roadmap](docs/ROADMAP.md).

## Contractor demonstration and structures sandbox

These are roadmap demonstrations, not part of a corner packet.

- **Contractor demonstration** (`/contractor.html`, roadmap M3): an opportunity brief, capability match, draft logistics, a team and equipment sequence with conflicts, labor-agreement handling and draft paperwork. It uses a corner's real records, synthetic quantities and a fictional company in `data/demo/sample_company.yaml`. Everything is stamped DEMONSTRATION, nothing is saved or submitted, and the contractor persona is unvalidated.
- **Structures sandbox** (`/structures.html`, roadmap M4): parameter-driven Pratt truss, lattice tower, geodesic dome and gear train geometry. There are no loads, member sizes or structural checks, and gear teeth are simplified shapes.

## Background reading

Set `OPEN_LIBRARY_CONTACT` in `.env` to a shared team address, then restart the app. Each packet then shows suggested books on architecture, accessibility, streets and drainage, plus a search box. Results are saved in `cache/open_library` for 30 days to stay within Open Library's limits. Reading can't change a rule, rate or result, and a released packet lists the suggested books already saved. To test the connection, open `http://127.0.0.1:8000/api/reading?q=architecture` while the app is running.

## Labels and concept plans

"Probably standard," "probably custom," likely ramp types and concept plans are off by default. After the adversarial suite passes and you decide to enable them, set `SHOW_LABELS_AND_PLANS=true`, as described in [P1 implementation](docs/P1-IMPLEMENTATION.md). Even then, they appear only with complete evidence, a finished review, every applicable rule and which-rule-applies decision reviewed by a named person, and no exceeded limit. Turning the setting off also hides them on runs saved earlier.

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

The first command writes `docs/candidates.md`. The saved corner is added to the demo list, and the sample corners don't change. Limits stay "unknown" until a named person reviews the rules.

## NYC data

| Dataset | What the app uses it for | Limit |
| --- | --- | --- |
| [Pedestrian Ramp Locations](https://data.cityofnewyork.us/d/ufzp-rrqu) | Ramp measurements | Last updated October 2021. NYC DOT says these measurements don't by themselves show ADA compliance. |
| [Program Progress](https://data.cityofnewyork.us/d/e7gc-ub6z) | Construction status and date | Updated regularly |
| [Complaints](https://data.cityofnewyork.us/d/jagj-gttd) | Ramp complaints and temporary repairs | Updated regularly |
| [Street Centerline](https://data.cityofnewyork.us/d/inkn-q76z) | Streets within 100 m of the ramp and their paved width | Can't confirm the road owner, because its documentation doesn't explain the jurisdiction field |
| [Street Construction Permits](https://data.cityofnewyork.us/d/tqtj-sjs8) and [2013–2021 permits](https://data.cityofnewyork.us/d/c9sj-fmsg) | Permits for the block with work ending after the survey | Shows work was allowed, not that it happened or touched this corner |
| [NYC DOT survey map](https://www.nycpedramps.info/survey) | DOT's status, existing ramp category, defects and obstacles for each ramp | DOT's own record, last edited in December 2020. It stays out of agent inputs and isn't a result from this tool. |
| [NYSDOT Roadway Inventory](https://www.dot.ny.gov/gisapps/roadway-inventory-system-viewer) | Who owns and maintains a road | Lists only some streets. A listed state road stops the corner. A street it doesn't list is assumed city-owned, labeled assumed and added to the site visit. |
| [Planimetric Sidewalk](https://data.cityofnewyork.us/d/52n9-sdep) | Rough paved width near the ramp, from map shapes | A cross-check, not a measurement. Only the estimate is saved. |

The official data dictionary gives lengths in inches and slopes and flares in percent, as recorded in `data/data_dictionary.yaml`.

**Swapped columns:** Open Data's `ramp_length` and `ramp_left_flare` columns are swapped. All 300 ramps sampled on November 5, 2026 matched DOT's survey map only when swapped, so the app reads them corrected. That explains the negative lengths, since negative flares are a direction. If DOT's survey map disagrees for a ramp, the packet says so.

A pedestrian ramp permit after the survey labels that ramp's measurements assumed only when its location ties it to the ramp: its point is within 30 m and its corner note, such as SW, fits. Other permits, including ramp permits that only share the block's street names, add a site-visit item. Permit holder names aren't saved. If a lookup fails, the packet says that dataset wasn't checked. NYC responses are saved in `cache/nyc` for 7 days. With no connection, an older saved response is used, and the packet shows when it was retrieved.

Legal grade and H-1011 ramp type still come from a person. Sidewalk width starts from DOT's approach width, read as inches and labeled assumed, because no document gives its unit. A site measurement replaces it.

## Settings

Each person keeps their own `.env` file in the project folder. Git ignores it, so never add it to a commit or put a key in any other file. To create it, copy `.env.example` to `.env`.

| To do this | Change these settings |
| --- | --- |
| Use live agents | Add `ANTHROPIC_API_KEY`, set `DEMO_MODE=false` and run `pip install anthropic` |
| Send email | Fill in `EMAIL_ALLOWLIST`, `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` and `SMTP_PASSWORD`, then set `EMAIL_ENABLED=true` |
| Show cited background reading | Set `OPEN_LIBRARY_CONTACT` to a shared team address |
| Dollar figures | Always withheld in the city-demo UI, traces and downloads; the legacy switch cannot expose them |
| Show labels and concept plans | Set `SHOW_LABELS_AND_PLANS=true`, subject to the conditions above |

A person must release each packet before it can be emailed, and every recipient must be on the allowlist. The email form stays hidden until `EMAIL_ALLOWLIST` is set.

## How it's organized

| Part | Location |
| --- | --- |
| Rules, one file each | `rules/federal`, `rules/nyc`, `rules/nys` |
| Which-rule-applies decisions | `rules/precedence` |
| Cost and labor rates | `rates` |
| Sample corners and saved agent responses | `data/corners`, `data/replay` |
| Saved real corners | `data/live` |
| Site measurement logic | `cornerbrief/field.py` |
| Tests, including the adversarial suite | `tests`, with the suite in `tests/test_v3.py` |
| Product requirements and reviews | `docs` |
| Run logs, including token use | `runs` (created when you run it) |
| Site photos | `runs/photos` (created when you add one) |
| Email dry runs | `outbox` (created when you use it) |

Regular code handles data checks, rule selection, limit checks, geometry, quantities, cost and labor hours. Agents only organize records, note constraints, propose options, challenge claims and write text. Their output must match a strict format, and checks reject unsupported numbers and claims such as "compliant."

## Known limits

- **Sample data:** The included corners are made up. They are not real NYC locations.
- **Rule review:** No named person has reviewed any of the 45 sourced rules or the which-rule-applies decisions yet.
- **User testing:** No junior engineer or reviewer has tried the app yet, and the manual timing baseline hasn't been recorded.
- **Live agents:** The live API path hasn't been run with a real key. Tests use saved or scripted responses.
- **Real data fetch:** The queries were checked in a browser on November 5, 2026, and the build environment can't reach these services. Run a search on your own computer to confirm the app's connection.
- **Site entries:** The newest version is remembered only in the browser tab where you entered it. Every version stays saved in `runs`.
- **Ramp data age:** The ramp measurement dataset was last updated in October 2021.
- **Open Library:** It's hidden until `OPEN_LIBRARY_CONTACT` is set. Its API and suggested topics were checked from a browser on November 5, 2026, but the app's own connection hasn't been confirmed. It stores citation details only, and no book text or corner details are used.
- **Email:** It defaults to a dry run that saves messages to `outbox`. Sending through SMTP is built and tested against a fake server, but it has never sent a real message. Inbound email isn't supported.
- **Cost and labor:** All rates are placeholders, not market prices.
- **Stack changes:** The app uses Starlette (FastAPI's foundation) and a small built-in 3D renderer instead of FastAPI and three.js, because those packages weren't available during the build.
- **Python version:** Tests ran on Python 3.13, and the app hasn't been run on a Mac since it was updated for Python 3.10 or newer.

## Rules that still need sources

These return "unknown" until a person adds the exact text and limit:

- H-1011 sheets 2 to 9, so case-specific details aren't checked. [`docs/sources/README.md`](docs/sources/README.md) links each sheet.
- 2025 NYS Building Code and Residential Code limits. These don't apply to NYC corners.

H-1011 Table 1 and its general notes come from `docs/sources/H-1011-1.pdf`. Surveyed ramps are compared with its work acceptance limits. Its stricter design limits appear only under "If this corner is rebuilt." The ADA rules quote ada.gov.


## P1 search and review

Use **Find a real NYC corner** to choose a borough, enter a street, or combine both. Search returns at most 100 ramp rows; narrow the street when the query is bounded. Select a corner to load its ramp, program and complaint records. Each source query and retrieval timestamp stays in the packet. Limits remain unknown until a named person reviews the rules. The sample picker remains available during empty/error states.

Expand **Agent trace** to inspect each agent's input, response and token accounting. Saved replay, deterministic offline steps and cached provider responses use zero provider tokens for that run. No live provider calls were made for this implementation's validation; SDK request/response handling is covered by mocked-provider tests. Traces redact credential-like text and dollar figures.

The actual static UI and sample packets can be exported with `python scripts/export_ui.py`. Helix serves `.helix/output/index.html`; search, field mutations and release/download require the local backend. The export makes no API or external resource requests.

Real junior-engineer/reviewer participation is still pending. Follow [the R29 protocol](docs/R29-ROLE-TEST.md) and use `scripts/role_test.py` to create and check result captures. See [P1 coverage and validation](docs/P1-IMPLEMENTATION.md) for exact limits and remaining human work.
