# CornerBrief PRD

Version 3 · November 4, 2026 · Owners: Abheeshu Dhungana and Ishmam Haque · Demo: November 12, 2026

Nov 5 addendum: section 8 and Journey 3 add the product direction from [issue #7](https://github.com/IshmamHaque1112/AbheeshuIshmam_civilengineerapp/issues/7) as a staged roadmap. The promise and the Nov 12 demo scope are unchanged.

This is the current PRD. It replaces `docs/CornerBrief-PRD.txt` and `docs/CornerBrief-PRD.pdf` (the Nov 3 version, kept for history). Version 3 folds in the Nov 3 audit, PRD v2, the Product PRD template work and Wil Sheppard's Nov 4 review.

## The promise

**CornerBrief assembles a traceable corner investigation packet, identifies which checks the evidence supports, and tells an engineer exactly what evidence is still needed.**

It assists an engineer. It does not approve designs, claim compliance or represent NYC.

## 1. Problem

DDC Junior Engineers in the Pedestrian Ramps Program lose time on every corner investigation because the records they need sit in three separate NYC Open Data sets, and the ramp measurements date from October 2021. Gaps surface only on site, so corners get repeat visits and redesigns. That delays accessible ramps for elderly, disabled and everyday pedestrians, and takes time away from the engineering decisions that matter. A 2019 settlement requires a ramp at every NYC corner, so this work repeats across hundreds of thousands of corners.

*Assumption to test:* we have not confirmed with a DDC engineer how long a corner takes today or how often site visits repeat.

### 1a. Opportunity

If the record gathering is done for them, a junior engineer walks into every site visit knowing what is on record, what is missing and what to measure, so one visit is enough.

- **Scale:** 217,679 ramps in Pedestrian Ramp Locations (ufzp-rrqu) and 187,749 corners in Ramp Program Progress (e7gc-ub6z), per `docs/data_report.md`.
- **Why now:** the [2019 settlement](https://www.6sqft.com/settlement-promises-curb-cuts-will-be-installed-or-upgraded-at-every-corner-in-nyc/) requires a ramp at every corner, and a [DDC posting for this role](https://cityjobs.nyc.gov/job/junior-engineer-design-in-queens-jid-48620) is public.

### 1b. Users and needs

- **Primary user:** a Junior Engineer (Design), Pedestrian Ramps Program, NYC DDC Division of Infrastructure, 30-30 Thomson Ave, Queens. Early career, doing "civil engineering tasks of moderate complexity under supervision": research studies, engineering investigations, field surveys and design-related site inspections.
- **Secondary user:** the Engineer-In-Charge, who reviews and signs off and needs every number sourced and every assumption flagged.
- **Not the user:** the public or the city officials at the demo. They are the audience.
- **Hypothesis user (not validated):** an estimator or project engineer at a NYC union contractor. This persona and workflow come from issue #7 and need real-user interviews before anything is built for them. See section 8.

Needs:

- As a junior engineer, I need everything on record for a corner in one place because pulling three datasets by hand takes time I should spend on the design.
- As a junior engineer, I need to know which inputs are measured, assumed or missing because stale or missing data is what sends me back to the site.
- As a junior engineer, I need a site-visit list of exactly what to measure, and a way to add what I measured, because I want one visit per corner.
- As an Engineer-In-Charge, I need every result tied to its rule and source, and I need the tool never to read like permission to proceed, because I sign off on the work.

## 2. Solution

CornerBrief is a web app that prepares a NYC street corner for an engineer's review. The engineer picks a corner, and the system pulls its ramp, construction and complaint records, labels every input as measured, assumed or missing, and checks the measurements against the exact rules that apply. Every corner ends in one of two states: **checks the evidence supports**, with sourced results, or **stop: evidence still needed**, with a site-visit list. The engineer adds field measurements and reruns the check.

### 2a. Value proposition

DDC junior engineers who lose time pulling scattered, outdated corner records use CornerBrief to get one traceable investigation packet per corner. Unlike searching three datasets by hand, it labels what is missing, shows the exact rule behind every supported check and stops instead of guessing, so one site visit counts.

### 2b. MVP value props

- **Vitamin:** every record for a corner in one packet, each input labeled measured, assumed or missing.
- **Painkiller:** a site-visit list of exactly what is missing or stale, and a rerun once it is measured.
- **Steroid:** every supported check shows its rule, section and quote, and the tool says "stop" whenever the evidence, the review or the rule coverage is incomplete.

### 2c. Goals and non-goals

Goals:

- A complete, sourced investigation packet for a corner before any site visit.
- Fewer wasted site visits, by turning missing or stale data into a precise list of what to measure.
- No result an engineer could read as permission to proceed when evidence, review or rule coverage is incomplete.
- The full flow working on four corners at the Nov 12 demo.

Non-goals until Nov 12:

- **"Probably standard" and "probably custom" labels, and concept plans (3D view, takeoff, labor, equipment).** These stay off by default until the adversarial suite (R28) passes. Reason: Wil's review showed they can appear before the evidence supports them. The separate synthetic 3D sandbox (Journey 3) doesn't change this, because it never reads or writes packet evidence.
- Dollar figures or cost estimates. The rates are placeholders.
- Final designs, drawings or compliance decisions. That is the Engineer-In-Charge's job.
- Citywide or batch processing, live AI agents, email and Open Library reading.
- The vacant-lot garden, school features and the LaGuardia garage concept.

### 2d. Success metrics

| Goal | Metric | Target |
| --- | --- | --- |
| Sourced packet | Supported checks showing rule, section, quote and link | 100% |
| Correct behavior | Demo corners ending in the expected state | 4 of 4 |
| Safe failure | Adversarial cases (R28) that end in "unknown" or "stop" | 10 of 10 |
| No overclaiming | Packets containing compliant, approved, allowed or safe | 0 |
| Faster than by hand | Minutes per corner vs. our own timed manual baseline on 3 Thomson Ave corners (week of Nov 3) | Under 2 minutes, covering everything the manual check found |
| One visit is enough | Gaps we hit measuring 3 real corners that the site-visit list had flagged | All |
| Usable by the real roles | Junior engineer + reviewer task (R29): time, corrections, missed issues | Recorded; 0 cases of a result read as permission to proceed |

If we cannot reach an engineer by Nov 12, R29 becomes the first milestone after the demo.

## 3. Rule set

At an NYC street corner the limits come mostly from NYC street rules, NYC DOT drawing H-1011 and the ADA. The NYS Uniform Code does not apply in NYC. PROWAG is reference material, not a starter limit.

- One rule per file, with limit, unit, jurisdiction, authority, edition, effective date, scope and stage (general, design target or work acceptance).
- Each file gives its section, link, short quote and retrieval date.
- Statuses: `verified` (a named person reviewed it, with `reviewed_by` and `reviewed_on`), `unreviewed`, `needs_source` or `superseded`. Only `verified` rules produce a final limit result; an `unreviewed` rule shows its math as an unreviewed calculation and the result stays "unknown."
- Models cannot create, edit or supply limits.
- Result wording: "limit exceeded," "no conflict found," "unknown" or "not applicable."

Starter rules include NYC Admin. Code §19-112 (8% slope, 4 ft width, 5/8 in lip), 34 RCNY §2-09(f)(4)(xi) and (xiv), NYC DOT filing guidelines VIII.F.2 and X.F, H-1011-1 Table 1 (machine-read, awaiting a named reviewer), ADA 2010 §405–406 (to confirm on ada.gov) and the 2025 NYS codes (outside NYC only, needs source). See `rules/`.

## 4. Requirements

IDs R1–R27 match PRD v2. R28–R31 are new in v3.

### Journey 1: Junior engineer preparing a corner for review

Choosing a corner and loading records

- [P0] R1 User can pick a corner from the demo list: three sample corners and one real corner near Thomson Ave.
- [P0] R2 User can see every input labeled measured, assumed or missing, with source and survey date.
- [P0] R19 Placeholder values such as 999 are treated as missing; limits need documented units.
- [P0] R20 Measurements are stale if the corner was rebuilt after the survey; a missing survey date or unmatched record is "unknown."
- [P1] R26 User can pull a real corner by borough or street.

Checking the corner

- [P0] R15 User can see which NYC, state and federal rules apply, and why.
- [P0] R5 Each limit is checked in plain code against one rule file with its exact section.
- [P0] R16 A rule file with no exact source fails to load; any rule not verified by a named reviewer returns "unknown."
- [P0] R17 When rule tiers disagree, both show and the stricter drives the warning.
- [P0] R18 Models cannot create or change limits; agent text cannot say compliant, approved, allowed or safe.
- [P0] R27 Every limit on a real corner stays "unknown" until the dataset's units are documented.

Ending state

- [P0] R3 When data is missing or stale, the corner ends in "stop: evidence still needed" with a site-visit list.
- [P0] R4 *(changed in v3)* Every corner ends in "checks the evidence supports" or "stop: evidence still needed." No standard/custom label appears until R28 passes. Even then, the label is provisional and needs complete evidence, a finished review, verified rules and no exceeded limit.
- [P0] R6 The skeptic challenges weak sources and claims with a retry limit; a malformed reply or exhausted retries counts as an incomplete review and ends in "stop."
- [P1] R11, R21–R25 Concept 3D view, takeoff, labor and equipment are off by default until R28 passes; no dollar figures in the city demo.

Measuring on site and rerunning *(new in v3)*

- [P0] R30 User can enter field measurements and photos for a corner's missing or stale inputs, labeled as measured on site with a date.
- [P0] R31 User can rerun the check with the new measurements and see what changed.

Releasing the packet

- [P0] R7 The packet shows findings, reasoning, unknowns, site checks and sources; the download keeps evidence dates and sample-data labels.
- [P0] R8 A person enters their name to release a packet before download or email. Releasing is not approval.
- [P0] R9, R10 The download states it is pre-design support, not a compliance decision, with no NYC affiliation.
- [P2] R12 Email to allowlisted test addresses only.

### Journey 2: Engineer-In-Charge reviewing a packet

- [P0] R5, R2 User can trace every supported check to its rule, section, quote and link, and see every assumption flagged.
- [P1] R14 User can see each agent's input, output and token use.
- [P2] R13 Cited background reading, kept apart from the checks.

### Journey 3: Exploring a synthetic 3D concept *(new Nov 5, issue #7)*

This journey lives on a separate page. It isn't part of a packet and needs no release.

- [P1] R32 User can edit ramp width, ramp length, landing width and landing length (ft) and running slope (%), and the 3D geometry, dimension labels and provisional quantities change to match.
- [P1] R33 User can orbit, zoom and pan the model with mouse, buttons or keys, and the dimension labels stay readable.
- [P1] R34 A missing or invalid dimension names the field and its valid range. Nothing is invented, and the last valid model is marked "not updated."
- [P1] R35 Every output shows its unit, whether each input is synthetic, assumed or unknown, and a revision. A new revision says that estimates or schedules built on the old one must be recalculated.
- [P0] R36 Synthetic values never become field evidence, never reach a packet, label, plan or rule check, and never show dollars, crew hours or permission words.

### Testing *(new in v3)*

- [P0] **R28 Adversarial suite.** Each case must end in "unknown" or "stop," never a label or plan:
  1. missing survey or construction dates
  2. unknown or unrecorded road ownership
  3. unmatched corner IDs across datasets
  4. undocumented units
  5. an exceeded limit with no recorded obstacle
  6. malformed skeptic output
  7. exhausted retries
  8. unreviewed rules
  9. conflicting evidence between records
  10. rapid switching between corners, with no state leaking from one corner to the next
- [P1] **R29 Role test.** A junior engineer and a reviewer complete one realistic corner. Record time, corrections, missed issues, and any result misread as permission to proceed.

## 5. Where the code stands (Nov 5)

The code now follows this version:

- **R4:** Every corner ends in "checks the evidence supports" or "stop: evidence still needed." Labels, likely ramp types and concept plans are off by default behind `SHOW_LABELS_AND_PLANS`.
- **R6:** A malformed Skeptic reply or exhausted retries ends in "stop," including on complex corners.
- **R28:** All 10 adversarial cases have automated tests in `tests/test_v3.py`, and they pass.
- **R30 and R31:** A person can enter site measurements and photos, rerun the check and see what changed. A rerun needs its own release.

- **R28 follow-up:** Most cases from `docs/P0-REVIEW.md` now have fixes and tests, including the label gate, permission language, unit validation and browser races. Cases run with labels off and on.

- **Synthetic 3D preview (R32–R36, issue #7):** A separate page has editable dimensions, orbit, zoom, pan and provisional quantities. It reads and saves no corner data and can't turn on labels or plans, so the concept plans in the non-goals stay off. A bad dimension now marks the model and quantities "not updated." The page lists which inputs are synthetic, assumed or not modeled, and says which revision a change supersedes. Helix's static copy includes the page with its default model, and editing there needs the local app. The warning-surface takeoff no longer exceeds a ramp shorter than 2 ft, so it now matches the model. This is an optional preview, not a change to the demo's promise. See `docs/3D-SLICE-VERIFICATION.md`.
- **R13:** Open Library search and suggested books are built, off by default and separate from the checks. It remains a P2 non-goal for the demo unless the team changes that.

Still open:

- Queens and Brooklyn reach "checks the evidence supports" with four corner inputs missing, and each affected check shows its own stop. `docs/P0-REVIEW.md` reads the stop wording more strictly, so the team should decide which it wants.
- With no API key, a rerun has no Skeptic review, because the saved responses describe the original records. It can reach "checks the evidence supports," but it says the review wasn't reused, and it can't show a label or plan.
- No named person has reviewed the rules, so every limit result stays "unknown."
- Corner 1024569 (Van Dam Street and Thomson Avenue) is now the demo's real corner, using saved records. Its ramp and program records name different streets, so confirm it's a good choice. R29 and the timing metrics need people.
- `docs/RUN-CHECK.md` (Nov 3) failed on Apple's Python 3.9. The app needs Python 3.10 or newer, and the README has Mac setup steps.

## 6. Demo plan (Nov 12)

1. State the limits: sample corners, no NYC affiliation, an engineer must review the rules.
2. Lead with one supported check against H-1011 Table 1 and §19-112, quote on screen.
3. Queens and Brooklyn sample corners: the packet and the checks the evidence supports.
4. Real corner near Thomson Ave: live records, limits "unknown" until units are documented.
5. One line on how a student could follow the math on a real corner.
6. End on the Bronx stop case: rebuilt after its survey, so the tool stops and writes the site-visit list.

## 7. Open questions and owners

| Question | Owner |
| --- | --- |
| Which real corner near Thomson Ave? | Ishmam (filter), then both |
| What units do the ramp dataset's measurements use? | Abheeshu |
| Which civil engineer reviews the rules and packets before Nov 12? | Abheeshu |
| H-1011 sheets 2–9 and ADA sections on ada.gov | Ishmam |
| Manual-check baseline time | Both, this week |
| R28 adversarial suite and the R4 change | Ishmam (code), to agree |
| Which real estimators or project engineers can test the contractor persona (section 8)? | Abheeshu, to agree |

## 8. Product direction and staged roadmap *(proposal, issue #7)*

Long-term direction: help a construction team turn a job opportunity into a traceable site investigation, an editable 3D concept and a resource-backed execution proposal for professional review. Today's corner packet is the site-investigation step of that workflow. Full milestones and acceptance criteria are in [`docs/ROADMAP.md`](ROADMAP.md).

| Milestone | Scope | Status |
| --- | --- | --- |
| M0 | Current corner investigation demo (sections 2–6) | Built |
| M1 | Synthetic 3D sandbox for corner ramps and landings (Journey 3) | Built, except that saved estimates and schedules to invalidate arrive in M2 |
| M2 | Documented geometry, shared-revision quantities and a draft small-concrete sequence, with missing resources shown as missing | Proposed next |
| M3 | Opportunity brief, capability match, logistics, crew and equipment sequencing, reviewable RFIs, daily reports and payroll checks | Proposed, after validating the contractor persona |
| M4 | Specialist structure modules. The bridge, tower, dome and gear-train demos set the bar for breadth and interaction quality only. | Future research, not a supported domain |

Rules for every milestone:

- The estimator or project engineer persona is a hypothesis until real users are interviewed.
- Union membership doesn't establish access to crews, equipment, bidding authority or credentials. Resources and authority come from company records and the agreements that actually apply.
- Rates and durations are never invented. Missing inputs and conflicts are shown.
- Labor, permit and payroll rules come from the actual contract and jurisdiction, verified and sourced as in section 3. One agreement is never generalized to every union job.
- Bidding, hiring, purchasing, permit submission and payroll submission need their own authorization.
- No output claims structural safety, compliance or approval. The existing evidence and rule gates, the off-by-default concept outputs, the city-demo dollar ban and the placeholder-rate disclosures stay.

## Sources

- Wil Sheppard's review, Nov 4, 2026 (shared with the team)
- [Issue #7: Product direction, editable 3D concepts and contractor logistics](https://github.com/IshmamHaque1112/AbheeshuIshmam_civilengineerapp/issues/7)
- Research starting points for section 8, not yet used for any rule: [NYC project labor agreements](https://www.nyc.gov/site/mocs/regulations/project-labor-agreements.page), [DDC prequalification](https://www.nyc.gov/site/ddc/contracts/rfqpql.page), [DOT street-work permits](https://www.nyc.gov/html/dot/html/infrastructure/permits.shtml), [NYSDOL certified payroll](https://dol.ny.gov/node/64811), [New York 811](https://newyork-811.com/about/how-we-work/)
- `docs/PRD-evaluation.md` (Helix review of the repo against the Nov 3 PRD)
- [NYC DDC Junior Engineer (Design) posting](https://cityjobs.nyc.gov/job/junior-engineer-design-in-queens-jid-48620)
- [NYC DOT H-1011-1](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-1.pdf)
- [Settlement requiring ramps at every NYC corner](https://www.6sqft.com/settlement-promises-curb-cuts-will-be-installed-or-upgraded-at-every-corner-in-nyc/)
