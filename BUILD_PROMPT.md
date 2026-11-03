# CornerBrief initial prototype: build prompt

Build the initial prototype of CornerBrief, a multi-agent web app for NYC street corners. It produces a review-ready brief for an engineer showing what is known, what is missing and what to check on site.

CornerBrief is a demo for pre-design investigation. It must never claim that a corner or design is compliant, approved, buildable or safe, or imply any affiliation with NYC. Use only these rule results: "limit exceeded," "no conflict found," "unknown" and "not applicable."

## Existing files
This folder already contains data_report.py and docs/data_report.md. Read the report first. It covers column details and only the first 1,000 rows of each dataset, so those rows are not a representative sample.

## Future ideas
Urban gardening site briefs, an architectural concept visualizer, and a separate book-grounded design and estimate tool for larger projects such as the LaGuardia garage are future ideas. Do not build them or add placeholders, datasets or agents for them. Do not add phone, calendar, Slack, student or inbound email features.

## Stack
- Backend: Python, FastAPI, Pydantic and the Anthropic Python SDK
- Frontend: a simple browser UI with a three.js viewer
- Storage: YAML rule and rate files, plus JSON for saved data, API caching and run logs
- Tests: pytest
- Hardware limit: integrated GPU only. Do not use local LLMs, local image or 3D generation, ray tracing or post-processing. Use simple materials and one light, redraw only when the camera moves, and cap the pixel ratio at 1.5.

## Modules
Build one Python module per component, with clear inputs and outputs and no hidden shared state.

Core, required for the prototype:
- data_loader: load saved ramp, progress and complaint records
- evidence: handle placeholders, units, joins, stale data and evidence labels
- rules: load and validate rule and precedence files
- applicability: decide which rules apply and record why
- agents/records, agents/site_analyst, agents/skeptic and agents/brief_writer
- checker: run limits and return only the four allowed results
- site_visit: list missing inputs and what to measure
- review_export: require approval and offer a download
- orchestrator: run the required flow
- web UI: choose a corner, view the brief, approve and download it

Add-on 1, after the core tests pass:
- parts_kit and model_3d: simple ramp, landing and curb geometry from checked dimensions, labeled as a concept
- takeoff: measure modeled area, volume, length and counts

Add-on 2, after add-on 1 tests pass:
- cost: quantities x dated rates, shown as a concept range
- crew_sequence: labor hours by trade and an ordered work sequence
- equipment_types: likely equipment types only; no crane selection or crane position
- safety_questions: questions for a professional on silica, traffic and training; not a safety plan or final PPE list

Add-on 3, if time remains:
- library: public-domain background reading from Open Library
- email: send-only delivery after approval

## Required flow
1. The user selects one of three demo corners.
2. Python loads its saved records.
3. Python cleans the data. Treat placeholder values such as 999 as missing. Do not run a limit check on a field until its unit is documented in data_dictionary.yaml.
4. Python joins the datasets by corner ID, reports join failures, and compares the survey date with the construction completion date. If construction finished after the survey, mark the measurements stale.
5. The Records agent organizes the records and labels each input as measured, assumed or missing, with its source and date.
6. Python validates those labels. A value can be "measured" only if it exists in a cited source record and is not stale.
7. Python decides which rules apply and records the reason.
8. Python decides whether the required data is present. An agent must not make this decision.
9. If data is missing or stale, skip the Site analyst, limit checks and planning add-ons. Generate a site visit list, then send it to the Brief writer.
10. If data is present, the Site analyst proposes likely ramp options and constraints.
11. Python checks each option against the applicable rule files.
12. The Skeptic reviews weak sources, conflicts and unsupported claims. It may send work back to the Site analyst, with a maximum of 2 retries. It cannot override a Python result or applicability decision.
13. If built, the add-ons run only from checked dimensions.
14. The Brief writer creates the brief using only validated results. It may not add facts, limits, numbers or legal conclusions.
15. A person reviews the brief. Only after approval can it be downloaded or emailed.

## Agents
Create four agents: Records, Site analyst, Skeptic and Brief writer. Validate every response with a Pydantic schema. Log each agent's input, output and token use. Regular code must handle data fetching, math, applicability, rule checks, geometry, takeoff, cost, crew hours and sending. No agent may create, change or supply a rule limit, rate or calculated number.

## Data
Use these NYC Open Data datasets:
- Pedestrian Ramp Locations: ufzp-rrqu
- Pedestrian Ramp Program Progress: e7gc-ub6z
- Pedestrian Ramp Complaints: jagj-gttd

Key fields:
- Locations: the_geom, cornerid, rampid, geocyclora, borough, curb_reveal, ramp_running_slope_total, dws_conditions, gutter_slope, lnd_width, lnd_length, lnd_cross_slope, counter_slope, ramp_width, ramp_right_flare, ramp_left_flare, ramp_length, ramp_cross_slope, ponding, obstacles_ramp, obstacles_landing
- Progress: the_geom, cornerid, borough, constructi, construc_1, construc_2
- Complaints: cmt_corner_id, borough, complaint_id, complaint_date, temp_repair_feasible, temp_repair_date, temp_repair_type

The report found no sidewalk width, legal grade or ramp type. Do not infer them. Mark them missing and add them to the site visit list when needed.

Write a script to query and save the raw records for candidate corners, then validate the join and field quality before choosing the fixtures. Do not invent real-world data. Label any necessary sample data SAMPLE DATA in the file and UI. Choose three corners:
- standard: enough current data for a likely ramp type
- constrained: evidence such as a complex construction status or recorded obstacle
- missing_or_stale: missing a required input or measured before a later rebuild, so no design is proposed

Keep live and sample data visibly separate. Cache all API responses.

## Rule set
Each rule must live in its own file:

rules/federal/
rules/nyc/
rules/nys/
rules/precedence/

Each rule file must include: id, title, jurisdiction, authority_type, applies_to, parameter, operator, limit, unit, source_document, edition, effective_date, section, url, quote, retrieved_on, status, reviewed_by and notes.

Allowed status values: verified, needs_source, superseded.

Validation rules:
- A verified rule file missing its exact section, URL, quote or edition must fail validation.
- A verified file must contain a limit only if that limit appears in its cited source.
- A needs_source rule must have no limit and must return "unknown."
- Do not write any limit from model memory. If a source is unavailable, create a needs_source file.

Create these starter rule files, then confirm each against the linked text before setting its status to verified:
- NYC Admin. Code section 19-112, curb ramp slope: 8% maximum. https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-204666
- NYC Admin. Code section 19-112, curb ramp width: 4 feet minimum. Same URL.
- NYC Admin. Code section 19-112, roadway lip: 5/8 inch maximum where a common level is not possible. Same URL.
- 34 RCNY section 2-09(f)(4)(xi), sidewalk transverse slope: 1 to 3 inches in 5 feet. https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCrules/0-0-0-62402
- 34 RCNY section 2-09(f)(4)(xiv), corner ramps must follow the latest H-1011. Same URL.
- NYC DOT filing guidelines VIII.F.2, recommended sidewalk slope: 0.50% minimum; 2.1% maximum for at least 5 feet of width and 5% for the remainder. https://www.nycstreetdesign.info/sites/default/files/2026-09/SCARA_instfilingplan.pdf
- NYC DOT filing guidelines X.F, gutter slope: 0.50% minimum. Same URL.
- NYC Street Design Manual, design ramp elements at least 0.5% below H-1011's maximum work acceptance slopes. https://www.nycstreetdesign.info/node/582

Create these as needs_source:
- Current H-1011 running slope, cross slope and landing limits
- Current H-1011 flare limits. A 2021 presentation shows 9.5% next to a pedestrian path, but do not use it as the current limit: https://www.nycpedramps.info/sites/default/files/2021-11/PedRampDesignGuidance.pdf
- 2010 ADA Standards curb ramp limits
- 2025 NYS Building Code and Residential Code limits

Do not use PROWAG as a limit. It may appear only as reference material unless an engineer or agency confirms otherwise. USDOT adopted it for transit stops, and a February 2026 congressional letter says DOJ had not adopted it.

## Applicability and conflicts
Create a Python resolver and reviewed precedence files. Each precedence file must include the question, decision, reason, source section and URL.

Required decisions:
- NYC location, building code: NYC Construction Codes apply; NYS Uniform Code does not. Source: https://dos.ny.gov/legal-memorandum-lg07-uniform-code-and-local-authority
- Non-NYC location: select NYS rule files and report that local additions need checking.
- Corner ramp in the public right-of-way: use ADA, NYC Administrative Code, Highway Rules and H-1011.
- Route from a sidewalk to a building: flag NYC Building Code section 1104 for engineer review; do not use it as a corner ramp limit. Confirm the edition: https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-174859
- State-controlled road in NYC: return "unknown" until ownership is confirmed.
- Different limits across tiers: show both rules, use the stricter for the warning, explain why, and leave the decision to an engineer.

## Planning add-ons
All planning results must come from one takeoff generated from the checked model. A dimension change must update every result.

Store each cost and crew rate in its own file under rates/ with: id, item, unit, value, currency, source, source_date, location, status and notes. Allowed status values: sample, public, licensed. Do not add licensed data without permission. A missing rate must return "unknown," not a number. Create only a small starter set and mark it sample. Flag any rate older than one year.

Label planning results "Class 5 concept estimate, not a bid." If you show a range, use -50% to +100% as the widest published Class 5 range, and state that it is not this tool's tested accuracy. Source: https://commons.lbl.gov/x/ZJYUCQ

List exclusions, including anything not modeled, such as utilities, drainage, traffic control and permit costs. Show likely trades, labor hours, equipment types and a work sequence. Do not output crane selection, crane position, a contract schedule, a site safety plan or a final PPE list.

Safety questions should tell the reader what a professional needs to check:
- Silica: OSHA Table 1 covers only listed tasks, and controls can depend on the task, location and duration. https://www.osha.gov/Publications/OSHA3681.pdf
- NYC training: requirements depend on the site and role. Return "unknown" if the site type is unclear. https://www.nyc.gov/assets/buildings/pdf/LL196_OnePager.pdf
- Traffic and pedestrian access during work

## Brief contents
Show these sections:
- Status: probably standard, probably custom or unknown
- Applicable rules: each rule considered, whether it applies, why, and its exact source
- Evidence table: measured, assumed, missing and stale inputs
- Findings and rule check results, with the math shown
- Rule conflicts for engineer review
- Unknowns and skeptic notes
- Site visit list
- Concept plan, if built: quantities, cost range, labor hours, equipment types, work sequence, assumptions and exclusions
- Questions for a safety professional, if built
- Sources
- Background reading, if built
- A visible notice that this is pre-design support and not a compliance decision

## Add-on 3 details
- Library: Search for street, pavement, drainage and accessibility design books. Add short, cited results to Background reading only. Process only public-domain text. Do not send borrowed in-copyright book text to a model. Results must not reach rule checks, rates or design values. Read a shared contact address from an environment variable and send it in the User-Agent header.
- Email: Add a send-only provider interface for the app's dedicated address. Default to dry-run mode, which saves the message locally. Sending requires human approval, EMAIL_ENABLED=true and an allowlisted recipient. Keep credentials in environment variables. Do not read inbound email.

## Configuration and cost
Provide .env.example with ANTHROPIC_API_KEY, FAST_MODEL, MAIN_MODEL, OPEN_LIBRARY_CONTACT, EMAIL_ENABLED and EMAIL_ALLOWLIST. Never commit secrets. Show token use for each run. Add a demo mode that replays cached agent responses, so the demo and UI tests can run without new API calls.

## Tests
Core tests:
- Rule math, using hand-calculated expected values
- A verified rule missing its exact source failing validation
- A needs_source rule returning "unknown"
- Unknown values and undocumented units returning "unknown"
- A placeholder value such as 999 being treated as missing
- Stale measurements being rejected as current evidence
- A false "measured" label being rejected
- An agent being unable to change or supply a limit
- An NYC location rejecting the NYS Uniform Code with its reason and source
- A non-NYC location selecting NYS rules
- A corner ramp not using a building code limit
- Conflicting tiers showing both rules and flagging engineer review
- The missing_or_stale corner skipping the Site analyst and limit checks
- The retry limit
- All three demo corners matching these expected results:
  - standard: suggests a likely ramp type and shows the math
  - constrained: flags a probable custom design and names its evidence or required site check
  - missing_or_stale: lists the data problem and refuses to propose a design

Add-on tests, for whatever is built:
- Hand-checked takeoff, cost and labor calculations
- One dimension change updating every planning result
- Sample rates being labeled wherever they affect a result
- A missing rate returning "unknown"
- No takeoff or estimate for the missing_or_stale corner
- No crane selection, crane position or final PPE list in the output
- Open Library results being unable to affect rule checks, rates or design values
- Email being blocked without approval or an allowlisted recipient

## How to work
Work in this order, and report what you tested after each milestone:
1. Inspect the folder and report, then write a short implementation plan.
2. Build the data dictionary, cleaning and join checks.
3. Build the rule schema, rule files, precedence files and validator.
4. Build the applicability resolver and checker and test them with no AI.
5. Save the three demo corners.
6. Add the agents and orchestration.
7. Build the UI and human review step.
8. Stop and confirm that the core tests and three-corner demo pass.
9. Add each add-on in order, only if the previous stage passes.
10. Write the README with setup, demo steps, known limits and rules still needing sources.

If time runs short, drop add-ons before cutting core features or tests. Before stopping, run the test suite and the three-corner demo, then report the results. Do not claim something works unless you ran it. If a requirement conflicts with what the data or sources support, keep the safety limits, explain the conflict and choose the smallest workable change.
