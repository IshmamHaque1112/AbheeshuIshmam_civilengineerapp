# CornerBrief PRD

Version 3 · November 4, 2026 · Owners: Abheeshu Dhungana and Ishmam Haque · Demo: November 12, 2026

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

- **"Probably standard" and "probably custom" labels, and concept plans (3D view, takeoff, labor, equipment).** These stay off by default until the adversarial suite (R28) passes. Reason: Wil's review showed they can appear before the evidence supports them.
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

## 5. Where the code stands (Nov 4)

PR #2 applied PRD v2: named reviewers, the real test corner path, borough and street filters, "allowed" in the blocked words, stricter status and skeptic handling, and dollars, email and reading hidden in the city demo. Against R28:

- Already handled: exceeded limit without obstacles returns "unknown"; an unfinished review returns "unknown" for standard corners; unreviewed rules return "unknown"; undocumented units return "unknown."
- Still to change: `decide_status` returns "probably custom" from complexity or obstacles before it checks whether the review finished, and the standard/custom label still shows by default (R4 v3). Cases 1–3, 9 and 10 need explicit tests.
- `docs/RUN-CHECK.md` (Nov 3) failed on Apple's Python 3.9; the app needs Python 3.10 or newer. A rerun with Homebrew Python 3.12 is in progress.

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

## Sources

- Wil Sheppard's review, Nov 4, 2026 (shared with the team)
- `docs/PRD-evaluation.md` (Helix review of the repo against the Nov 3 PRD)
- [NYC DDC Junior Engineer (Design) posting](https://cityjobs.nyc.gov/job/junior-engineer-design-in-queens-jid-48620)
- [NYC DOT H-1011-1](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-1.pdf)
- [Settlement requiring ramps at every NYC corner](https://www.6sqft.com/settlement-promises-curb-cuts-will-be-installed-or-upgraded-at-every-corner-in-nyc/)
