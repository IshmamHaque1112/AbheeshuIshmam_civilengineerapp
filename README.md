# CornerBrief

CornerBrief assembles a traceable investigation packet for a NYC street corner, shows which checks the evidence supports, and tells an engineer exactly what evidence is still needed. It is a demo for pre-design investigation. It does not decide compliance, approve a design or represent NYC.

The product requirements are in [`docs/PRD.md`](docs/PRD.md) and the staged direction is in [`docs/ROADMAP.md`](docs/ROADMAP.md). The demo is on November 12, 2026.

## The problem

New York City has about 217,000 pedestrian ramps across roughly 134,000 street corners. Before any one of them is redesigned, an engineer has to answer basic questions: which corner is this, which ramps are on it, what do they measure, has anything been built since they were measured, who owns the road, and which rules apply.

Today those answers are spread across at least eight public sources that don't link to each other:

- **Records are scattered.** Ramp measurements, construction history, permits, complaints, street centerlines, sidewalk outlines, DOT's own survey map and the state road inventory each live in a different dataset or map service, with different identifiers, units and coordinate systems.
- **Records go out of date without saying so.** DOT's ramp measurements were last updated in October 2021. A ramp rebuilt or permitted since then still shows its old numbers. By our estimate, about 62% of corners citywide stop for evidence in CornerBrief, most often because construction or permits since the survey may have changed them.
- **The data has errors.** Two columns in the ramp dataset, ramp length and left flare, are swapped. One sidewalk width field has no documented unit. Nothing in the data warns a reader about either.
- **The rules overlap.** A single corner ramp can fall under the federal ADA Standards, the NYC Administrative Code, the Rules of the City of New York and DOT's H-1011 standard drawings. They set different limits for the same measurement, in different units, and some apply only to particular ramp designs.
- **Gaps are found too late.** Missing or outdated information is often discovered on site or in review, which means a second site visit, rework, or a design built on numbers that were never true.

The result is hours of manual cross-checking per corner, and a real risk that a design starts from the wrong corner or stale evidence. Every later step, from the 3D concept to quantities and construction planning, inherits that error.

## The solution

CornerBrief does the groundwork in one traceable packet and is honest about what it can't establish:

1. **Find the right corner** by borough and street, and see which ramps and records exist for it.
2. **Bring the evidence together** from nine public sources, correct known data errors, and label every value **measured**, **assumed**, **missing** or **stale**, with its source and retrieval time.
3. **Check what the evidence supports** against 52 cited rules, with the math shown. When the evidence isn't good enough, the packet says **"Stop: evidence still needed"** and explains why, rather than guessing.
4. **Hand the engineer a site visit list** of exactly what to measure or confirm, and rerun the check with site measurements when they come back.
5. **Show how documented dimensions could carry forward** into a 3D concept, quantities and a draft work sequence, keeping synthetic examples visibly separate from real evidence.

The decision stays with people. CornerBrief never says a corner is "compliant," never fills a gap with a guess, and never turns an unreviewed rule into a pass or fail.

### Who it's for

| User | What they need from CornerBrief |
| --- | --- |
| **DDC junior engineer** scoping a corner | One place with every record, labeled by how far it can be trusted, and a list of what to check before leaving the desk |
| **Junior engineer back from the field** | A way to add site measurements and see what changes |
| **Engineer-In-Charge** reviewing a brief | Every supported check tied to its rule, section and source, and a clear stop wherever evidence is incomplete |

As user stories:

1. As a DDC junior engineer preparing a corner, I need to see every record for that corner in one place, labeled measured, assumed or missing, so that I don't spend time cross-checking datasets by hand.
2. As a DDC junior engineer, I need a list of exactly what is missing or out of date before I leave the desk, so that I make one site visit instead of finding the gaps on site.
3. As a DDC junior engineer back from the field, I need to add what I measured and rerun the check, so that the brief reflects the corner as it is today.
4. As an Engineer-In-Charge reviewing a brief, I need every supported check tied to its rule, section and source, and a clear "stop" wherever evidence is incomplete, so that I never sign off on a result I can't trace.

## The workflow, and what is built today

The four steps connect. Choosing the correct corner and checking its evidence decides whether anything after it can be trusted.

| Step | Built and working | Synthetic or fictional demonstration | Proposed or gated |
| --- | --- | --- | --- |
| **1. Find the corner** | Search NYC records by borough and street name, choose the corner, see its ramps and which records were found, each with its query and retrieval time | Sample corners A, B and C use made-up records | Search by exact intersection |
| **2. Investigate the evidence** | Records joined from nine sources; every value labeled measured, assumed, missing or stale; cited rule checks with math; "stop" with reasons; site visit list; site measurements and rerun; release and download | Sample corners and saved agent responses | Rule results become pass or fail only after a named reviewer verifies each rule |
| **3. Develop a 3D concept** | Each ramp dimension shown as documented, assumed, unresolved or stale with its record; a 3D sandbox that turns dimensions into geometry and provisional quantities | The sandbox uses typed-in dimensions and is labeled synthetic | The packet's own concept model, built from surveyed dimensions, appears only when labels and plans are turned on and the corner has complete evidence, a finished review, verified rules and no exceeded limit |
| **4. Prepare construction planning** | A draft concrete work sequence (sawcut to restoration) whose durations and crews stay "unknown" and that is flagged for recalculation when its inputs change | Contractor logistics with a fictional company, off by default | Real durations, crews, costs and scheduling, after interviews with estimators and a professional review |

The 3D concept is not a proposed design. It draws the existing ramp as surveyed, or dimensions typed into the sandbox, to show how documented dimensions could inform geometry and quantities. Proposing new dimensions that meet the rules is future work that needs verified rules and a licensed reviewer.

## How a corner is checked

Regular Python code makes every decision about data, rules and numbers. Four AI agents only organize and write.

1. **Load the records** for the chosen corner and nearby streets, permits, sidewalk shapes, DOT's survey map and the state road inventory.
2. **Label the evidence.** A measurement is stale if construction, a ramp permit located at that ramp, or a later survey came after it. A value with no documented unit, or a road owner the records don't confirm, is labeled assumed.
3. **Decide which rules apply** using six written precedence decisions, for example that a corner ramp in the public right-of-way uses ADA, the NYC Administrative Code, the Highway Rules and H-1011, not building code limits.
4. **Gate on evidence.** If required evidence is missing, stale, assumed or in conflict, the corner stops with the reasons.
5. **Compare each measurement with each applicable rule,** converting units first. Where rules disagree, all of them are shown and the strictest is used for the warning, with the choice left to an engineer.
6. **Write the packet.** The agents run:
   - **Records agent:** organizes the evidence and copies its labels. Labels that disagree with the code's are rejected.
   - **Site analyst:** notes site constraints and options. Runs only when the evidence passes.
   - **Skeptic:** challenges claims and sends work back. Runs only when the evidence passes.
   - **Brief writer:** turns the results into plain English.

   A checker rejects any agent text that states unsupported numbers or claims such as "compliant."

### What the results mean

| You see | It means |
| --- | --- |
| **Checks the evidence supports** | The records are complete and current enough to calculate. It is not permission to proceed. |
| **Stop: evidence still needed** | Evidence is missing, out of date, unconfirmed or in conflict, or a calculated value is above a limit with no recorded constraint to explain it. The packet lists what to check. |
| **Unknown**, tagged **"Calculation within limit, unreviewed"** or **"Calculation above limit, unreviewed"** | The math ran, but no named person has reviewed the rule yet, so it can't produce a result. |
| **Unknown** with no math | The value is assumed, missing or stale, or its unit isn't documented, so no limit was checked. |
| **No conflict found** or **Limit exceeded** | Appears only for a rule a named person has verified. No rule is verified yet. |

A rule counts as verified only after a named person checks it against its source. To record a review, run:

```powershell
python scripts/review_rule.py NYC-ADMIN-19-112-SLOPE --reviewer "Full Name"
```

## Run it on Windows

Open PowerShell in this folder, then run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
python -m cornerbrief
```

Open http://127.0.0.1:8000 in your browser. If PowerShell blocks the activate script, run `Set-ExecutionPolicy -Scope Process RemoteSigned` and try again, or skip activation and call `.venv\Scripts\python` directly, for example `.venv\Scripts\python -m cornerbrief`.

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

No API key is needed, and the demo stays in this mode while `DEMO_MODE=true`. The corners at the top of the app work offline:

1. **Sample corner A, Queens:** Checks the evidence supports, with the source and math for each calculation.
2. **Sample corner B, Brooklyn:** Checks the evidence supports, with a utility vault and catch basin to review and one Skeptic rework.
3. **Real test corner:** Corner 1024569, Van Dam Street and Thomson Avenue, from NYC Open Data. It stops because a 2024 pedestrian ramp permit is located at each ramp, after the 2018 survey. Its road owner is assumed, not confirmed.
4. **Sample corner C, Bronx:** Stop: evidence still needed, because it was rebuilt after its survey and has a placeholder value.

Enter a name and select **Release packet** to turn on the download. Releasing is not approval. **Download site visit list** needs no release, because it lists only what to measure or confirm and contains no limit results.

To print the results without the browser, run `python scripts/run_demo.py`.

## Find a real NYC corner

Use **Find a real NYC corner** to choose a borough, enter a street name, or both. Search returns at most 100 ramp rows, so narrow the street if the results say they're bounded. Select a corner to load its records. Each source query and retrieval time stays in the packet.

Real corners checked on November 10, 2026 that make good examples:

| Result | Corner | Borough | Search for |
| --- | --- | --- | --- |
| Checks the evidence supports | 1 Avenue and East 60 Street | Manhattan | `1 AVENUE` |
| Checks the evidence supports | 3 Avenue and 19 Street | Brooklyn | `19 STREET` |
| Checks the evidence supports | Billiou Street and Luten Avenue | Staten Island | `BILLIOU` |
| Stop: ramp permit after the survey | Van Dam Street and Thomson Avenue | Queens | `THOMSON` |
| Stop: rebuilt after the survey | West Tremont Avenue and University Avenue | Bronx | `TREMONT` |

City records change, so check a corner shortly before showing it. NYC responses are saved in `cache/nyc` for 7 days, and with no connection an older saved response is used, so a corner searched before a demo still works offline.

## Add site measurements and rerun

Under **Add site measurements**, enter who measured, the date and any values you have, with an optional photo for each. **Rerun the check** then shows what changed. Each value is labeled as measured on site. A value measured before the corner's latest construction, before ramp permit work at that ramp could end, or before the survey it replaces stays stale.

Each rerun creates a new packet that needs its own release. The tab keeps showing the newest version when you switch corners or reload, and **Start over from the original records** clears it. A new tab starts from the original records. In demo mode, a rerun still runs every Python check, but the Skeptic review doesn't run, because the saved responses describe the original records. No label or plan can appear until a review finishes.

## 3D preview

Select **3D preview (synthetic)** at the top of the app, or open `/preview.html`. Change the ramp and landing dimensions to update the model, the provisional quantities and the draft work sequence, then drag to rotate, scroll to zoom, and shift-drag or right-drag to pan. **Show height at 3×** makes slopes visible.

These dimensions are made up. They aren't saved, can't reach a packet, label or plan, and get no rule check. If a value is missing or out of range, the model and quantities stay at the last valid revision and are marked **Not updated** until you fix it. The page lists which inputs are synthetic, which are assumed and what isn't modeled, such as sidewalk width, cross slopes, flares, utilities and road ownership.

## Contractor demonstration and structures sandbox

These are roadmap demonstrations, not part of a corner packet. They're off by default. Set `SHOW_ROADMAP_DEMOS=true` in `.env` and restart to show them; otherwise their pages and links don't exist. Leave them off for the city demo.

- **Contractor demonstration** (`/demo/contractor.html`, roadmap M3): an opportunity brief, capability match, draft logistics, a team and equipment sequence with conflicts, labor-agreement handling and draft paperwork. It uses a corner's real records, synthetic quantities and a fictional company in `data/demo/sample_company.yaml`. Every section is stamped DEMONSTRATION, and every value is labeled Real record, Synthetic, Fictional or Unknown. Nothing is saved or submitted, and the contractor persona is unvalidated.
- **Structures sandbox** (`/demo/structures.html`, roadmap M4): parameter-driven Pratt truss, lattice tower, geodesic dome and gear train geometry. There are no loads, member sizes or structural checks, and gear teeth are simplified shapes.

Tests keep fiction and reality apart: demonstration code can't import anything that saves, releases or emails a packet; no real packet may contain a fictional company value; the fictional register must start with `fictional: true`; and packets can't load files from `data/demo/`.

## Labels and concept plans

"Probably standard," "probably custom," likely ramp types and concept plans are off by default. After the adversarial suite passes and you decide to enable them, set `SHOW_LABELS_AND_PLANS=true`, as described in [P1 implementation](docs/P1-IMPLEMENTATION.md). Even then, they appear only with complete evidence, a finished review, every applicable rule and which-rule-applies decision reviewed by a named person, and no exceeded limit. Turning the setting off also hides them on runs saved earlier.

## Background reading

Set `OPEN_LIBRARY_CONTACT` in `.env` to a shared team address, then restart the app. Each packet then shows suggested books on architecture, accessibility, streets and drainage, plus a search box. Only citation details are kept: title, authors, year and link. The app never reads book text, and no corner details are sent. Results are saved in `cache/open_library` for 30 days to stay within Open Library's limits. Reading can't change a rule, rate or result. To test the connection, open `http://127.0.0.1:8000/api/reading?q=architecture` while the app is running.

## Data sources

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
| [Open Library](https://openlibrary.org) (optional) | Background reading | Citations only. Never affects a result. |

The official data dictionary gives lengths in inches and slopes and flares in percent, as recorded in `data/data_dictionary.yaml`.

**Swapped columns:** Open Data's `ramp_length` and `ramp_left_flare` columns are swapped. All 300 ramps sampled on November 5, 2026 matched DOT's survey map only when swapped, so the app reads them corrected. That explains the negative lengths, since negative flares are a direction. If DOT's survey map disagrees for a ramp, the packet says so.

**Permits:** A pedestrian ramp permit after the survey labels that ramp's measurements assumed only when its location ties it to the ramp: its point is within 30 m and its corner note, such as SW, fits. Other permits, including ramp permits that only share the block's street names, add a site-visit item. Permit holder names aren't saved. If a lookup fails, the packet says that dataset wasn't checked.

**Still from a person:** Legal grade and the H-1011 ramp type aren't in any dataset used here. Sidewalk width starts from DOT's approach width, read as inches and labeled assumed, because no document gives its unit. A site measurement replaces it.

## Rules

There are 52 rules, one file each, and 6 which-rule-applies decisions. 49 rules are unreviewed and 3 still need a source. None is verified yet.

| Source | Rules | Covers |
| --- | --- | --- |
| 2010 ADA Standards for Accessible Design, §405 and §406 | 7 | Running and cross slope, width, counter slope, flares, landing |
| NYC DOT Standard Details H-1011-1 (Table 1 and general notes) | 24 | Design targets and work acceptance limits for slopes, width, rise, landings and level changes |
| NYC DOT Standard Details H-1011-2 to H-1011-9 | 5 | Case selection, C4 and C5 approval, gutter minimum, detectable warning surfaces, and one placeholder that still needs a source |
| NYC Administrative Code §19-112 | 3 | Ramp slope, width, lip at the roadway |
| Rules of the City of New York, Title 34 §2-09 | 2 | Corner ramps follow H-1011; sidewalk cross slope |
| NYC DOT Pedestrian Ramp Program brochure | 4 | General slope and width requirements |
| NYC DOT filing guidelines | 2 | Sidewalk cross slope, gutter slope |
| NYC DOT Technical Instruction TI 22-001 | 1 | Technical infeasibility on steep streets |
| NYC Street Design Manual | 1 | Design margin below acceptance limits |
| NYC Building Code §1104 | 1 | Routes into buildings, flagged rather than checked |
| 2025 NYS Building and Residential Codes | 2 | Placeholders for locations outside NYC, still needing sources |

H-1011 Table 1 and its general notes come from `docs/sources/H-1011-1.pdf`. Surveyed ramps are compared with its work acceptance limits, and its stricter design limits appear only under "If this corner is rebuilt." The ADA rules quote ada.gov.

Sheets 2 to 9 are saved in `docs/sources` and transcribed in [`docs/sources/H-1011-sheets-2-9.md`](docs/sources/H-1011-sheets-2-9.md). The transcription was made by Claude and re-read at high resolution, but no person has checked it yet, and case-specific details aren't checked as numbers because the data doesn't say which case a corner follows.

## Settings

Each person keeps their own `.env` file in the project folder. Git ignores it, so never add it to a commit or put a key in any other file. To create it, copy `.env.example` to `.env`.

| To do this | Change these settings |
| --- | --- |
| Use live agents | Add `ANTHROPIC_API_KEY`, set `DEMO_MODE=false` and run `pip install anthropic` |
| Send email | Fill in `EMAIL_ALLOWLIST`, `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` and `SMTP_PASSWORD`, then set `EMAIL_ENABLED=true` |
| Show cited background reading | Set `OPEN_LIBRARY_CONTACT` to a shared team address |
| Dollar figures | Always withheld in the city-demo UI, traces and downloads; the legacy switch cannot expose them |
| Show labels and concept plans | Set `SHOW_LABELS_AND_PLANS=true`, subject to the conditions above |
| Show the roadmap demonstrations | Set `SHOW_ROADMAP_DEMOS=true`. Leave it off for the city demo. |

**Live agents and cost:** results are the same in demo and live mode, because code makes every decision; only the agents' wording changes. In live mode, the Records agent and Brief writer run on every corner, including corners that stop, and the Site analyst and Skeptic run only when the evidence passes. On November 10, 2026, a stopped corner used about 25,000 to 30,000 tokens and a passing corner about 90,000 to 130,000. Repeat runs with identical inputs reuse saved responses from `cache/agents` and use none. Keep `DEMO_MODE=true` for the city demo so it needs no network or key.

A person must release each packet before it can be emailed, and every recipient must be on the allowlist. The email form stays hidden until `EMAIL_ALLOWLIST` is set.

Expand **Agent trace** in a packet to see each agent's input, response and token use. Traces redact credential-like text and dollar figures.

## Tech stack

| Layer | What we used | Why |
| --- | --- | --- |
| Language | Python 3.10 or newer | One language for data, rules, checks and the server |
| Web server | [Starlette](https://www.starlette.io) on [Uvicorn](https://www.uvicorn.org) | A small async web framework, the foundation FastAPI is built on |
| Data models | [Pydantic](https://docs.pydantic.dev) v2 | Strict shapes for evidence, rule results and agent output, so malformed agent responses are rejected |
| Rules and settings | YAML files read with [PyYAML](https://pyyaml.org) | One readable, reviewable file per rule, decision and rate |
| Front end | Plain HTML, CSS and JavaScript, no framework | Runs anywhere with no build step |
| 3D | A small built-in renderer drawing on an HTML canvas | No outside 3D library was available during the build |
| AI agents | [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) (optional), with Claude Sonnet 5.5 and Claude Haiku 5.5 | Live agent wording; demo mode uses saved responses and needs no key |
| City and state data | NYC Open Data's Socrata API, NYC DOT's and NYSDOT's ArcGIS REST services, through Python's built-in `urllib` | Public sources, queried directly and cached as JSON |
| Background reading | [Open Library](https://openlibrary.org/developers/api) search API (optional) | Citations only |
| Certificates on Windows | [truststore](https://github.com/sethmlarson/truststore) | Lets Python use the Windows certificate store, which NYC data needed |
| Email | Python's built-in `smtplib` | Dry run by default, sends only to allowlisted addresses |
| Storage | JSON files in `runs`, `cache` and `data` | No database to install or run |
| Tests | [pytest](https://pytest.org), Starlette's test client (with `httpx2`), and [Playwright](https://playwright.dev) with Chromium for browser checks | 517 tests, including an adversarial suite; browser checks skip without Playwright |

Everything runs locally on one computer. There is no cloud service, database or front-end build step, and the only network calls are to the public data sources, Open Library when it's turned on, and the Claude API in live mode.

## How it's organized

| Part | Location |
| --- | --- |
| Rules, one file each | `rules/federal`, `rules/nyc`, `rules/nys` |
| Which-rule-applies decisions | `rules/precedence` |
| Rule sources and transcriptions | `docs/sources` |
| Cost and labor rates (placeholders) | `rates` |
| Sample corners and saved agent responses | `data/corners`, `data/replay` |
| Saved real corners | `data/live` |
| Fictional demonstration data | `data/demo` |
| Site measurement logic | `cornerbrief/field.py` |
| Tests, including the adversarial suite | `tests`, with the suite in `tests/test_v3.py` |
| Product requirements, roadmap and reviews | `docs` |
| Run logs, including token use | `runs` (created when you run it) |
| Site photos | `runs/photos` (created when you add one) |
| Email dry runs | `outbox` (created when you use it) |

To add a saved real corner to the demo list:

```powershell
pip install truststore
python scripts/fetch_corners.py --borough QUEENS --street THOMSON
python scripts/fetch_corners.py --save real_test CORNER_ID
```

The first command writes `docs/candidates.md`. The saved corner is added to the demo list, and the sample corners don't change.

The static UI and sample packets can be exported with `python scripts/export_ui.py`. Search, site measurements and release need the local app.

## Known limits

**Evidence and data**

- **Ramp data age:** The ramp measurement dataset was last updated in October 2021, so many corners stop because later work makes their measurements stale.
- **Not in any dataset:** Legal grade, the existing ramp type in H-1011 terms, sidewalk cross slope, warning surface size, and utilities and vaults must be measured or confirmed on site.
- **Assumed values:** Unlisted roads are assumed city-owned, and DOT's sidewalk approach width is read as inches. Both are labeled assumed.
- **Permits:** A permit shows work was allowed, not that it happened, and matching it to a ramp can miss or mis-tie a permit.
- **Search:** It finds corners by borough and one street name, not by exact intersection, and returns at most 100 ramp rows.
- **Sample data:** Sample corners A, B and C are made up. They are not real NYC locations.

**Rules**

- **Rule review:** No named person has reviewed any rule or which-rule-applies decision, so every limit result is "unknown."
- **H-1011 sheets 2 to 9:** The transcription hasn't been checked by a person, and case-specific details aren't checked as numbers.
- **Rule updates:** If a standard changes, someone must edit its rule file.
- **Compliance:** The app doesn't decide compliance. DOT also weighs site constraints and technical infeasibility.

**Design and planning**

- **3D concept:** It shows existing surveyed dimensions or typed-in synthetic ones. It is not a proposed or constructible design.
- **Cost and labor:** All rates are placeholders, not market prices. Durations and crews stay "unknown," and dollars are hidden.
- **Roadmap demonstrations:** The contractor demonstration uses a fictional company and an unvalidated persona. The structures sandbox has no loads or checks.

**Testing and operation**

- **User testing:** No junior engineer or reviewer has tried the app yet, and the manual timing baseline hasn't been recorded. Follow [the R29 protocol](docs/R29-ROLE-TEST.md) and use `scripts/role_test.py` to record a session.
- **Live agents:** Live mode was run 12 times with a real key on November 10, 2026. Tests use saved or scripted responses.
- **Real data:** Searches and corner loads have run against live NYC services from a Windows laptop. The build environment can't reach them.
- **Site entries:** The newest version is remembered only in the browser tab where you entered it. Every version stays saved in `runs`.
- **Email:** It defaults to a dry run that saves messages to `outbox`. Sending through SMTP is tested against a fake server, but it has never sent a real message. Inbound email isn't supported.
- **Python version:** Tests run on Python 3.13. Python 3.14 hasn't been tested, and the app hasn't been run on a Mac since it was updated for Python 3.10 or newer.
- **Stack changes:** The app uses Starlette (FastAPI's foundation) and a small built-in 3D renderer instead of FastAPI and three.js, because those packages weren't available during the build.
