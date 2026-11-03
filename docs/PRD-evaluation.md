# CornerBrief PRD evaluation

Review date: 2026-11-03. Review only; the only intended repository change is this report.

## Finding and scope

The repository supports a useful **sample-data pre-design demonstration**, but this review cannot certify PRD coverage or runtime acceptance. Neither requested source, `docs/CornerBrief-PRD.txt` nor `docs/CornerBrief-PRD.pdf`, exists in this checkout. The available `BUILD_PROMPT.md` describes a similar product but contains neither R1–R25 identifiers and priorities nor an explicit PRD open-question list. It is used below as a **secondary comparison baseline**, not silently substituted for the missing PRD. Requirements, priorities, and open questions from the actual PRD remain unverified.

Audience and scope supplied by the requester: NYC DDC/DOT engineers, possibly a city education official; primary user is the NYC DDC Junior Engineer (Design), Pedestrian Ramps Program. Real-data fetch and a vacant-lot garden are later dummy-test concepts, not demo deliverables. This report therefore does not treat an unexecuted real-data fetch or an absent garden feature as a demo failure. `BUILD_PROMPT.md` also excludes urban gardening from the prototype; `README.md` describes a three-corner sample demonstration.

Static inspection shows Python-controlled evidence, applicability, rule math, and release gating, with saved agent responses and three explicitly synthetic corners (`cornerbrief/evidence.py`, `cornerbrief/applicability.py`, `cornerbrief/checker.py`, `cornerbrief/review_export.py`, `cornerbrief/llm.py`, `data/corners/*.json`). The main concerns for this audience are the strength of “probably standard,” unreviewed source authority, freshness/ownership assumptions, and planning presentation. These are described below without asserting any legal interpretation or new rule limit.

## 1. Requirement coverage: R1–R25

**Priority convention:** “unverified” means the PRD priority could not be read; it does not mean low priority. **Status convention:** “can't tell” means the requirement text itself is unavailable. No R-number-to-feature mapping is invented. All 25 requested identifiers are retained so a later review can replace these rows against the actual PRD.

| Requirement | PRD priority | Status | File/test evidence | One-line note |
| --- | --- | --- | --- | --- |
| R1 | unverified | can't tell | `docs/CornerBrief-PRD.txt` and `docs/CornerBrief-PRD.pdf` absent | Text and priority unavailable; no defensible mapping. |
| R2 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R3 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R4 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R5 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R6 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R7 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R8 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R9 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R10 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R11 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R12 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R13 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R14 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R15 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R16 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R17 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R18 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R19 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R20 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R21 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R22 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R23 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R24 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |
| R25 | unverified | can't tell | Same missing PRD paths | Text and priority unavailable; no defensible mapping. |

### Useful coverage against the available build prompt

The following labels are **static implementation assessments against `BUILD_PROMPT.md`**, not numbered PRD verdicts or executed test results.

| Build-prompt feature | Static status | Evidence | Note |
| --- | --- | --- | --- |
| Three synthetic corners and replay mode | met | `data/corners/{standard,constrained,missing_or_stale}.json`, `data/replay/`, `cornerbrief/llm.py` | Explicit sample labels and saved responses; no key required for replay. |
| Placeholder and unit handling | met | `cornerbrief/evidence.py`, `cornerbrief/checker.py`, `data/data_dictionary.yaml`, `data/sample_data_dictionary.yaml` | Placeholders become missing; undocumented units prevent numeric checks. |
| Joins and stale measurements | partly met | `cornerbrief/evidence.py::join_report`, `latest_construction`, `is_stale`, `data_sufficient` | Join warnings exist, but are not a sufficiency gate; freshness checks only later recorded construction. |
| Evidence labels validated in Python | partly met | `cornerbrief/evidence.py::validate_labels`, `build_evidence`, `cornerbrief/orchestrator.py` | Agent labels cannot replace Python labels; computed rise is nevertheless labeled measured. |
| Separate rule files and metadata validation | partly met | `cornerbrief/rules.py`, `rules/federal/`, `rules/nyc/`, `rules/nys/` | Required fields/stages enforced; source-field presence does not prove quote/limit correctness. |
| Applicability, precedence, and conflict explanations | partly met | `cornerbrief/applicability.py`, `rules/precedence/`, `cornerbrief/checker.py::find_conflicts` | Required branches exist, but precedence files have no human reviewer and unknown ownership is assumed city-controlled. |
| Deterministic numeric checks and four results | met | `cornerbrief/checker.py`, `cornerbrief/models.py::RuleResult`, `tests/test_core.py` | Allowed result vocabulary is encoded; test execution unavailable here. |
| Missing/stale stop with site visit list | met | `cornerbrief/orchestrator.py::analyze`, `cornerbrief/site_visit.py`, `tests/test_flow.py::test_missing_or_stale_corner_refuses_design` | Skips analyst and Skeptic and withholds planning; still creates unknown/not-applicable result rows. |
| Four strict-schema agents, retries, logs | partly met | `cornerbrief/models.py`, `cornerbrief/llm.py`, `cornerbrief/orchestrator.py` | Extra schema fields rejected and retries capped; invalid Skeptic output is treated as a pass to exit the loop. |
| Guard against unsupported facts and claims | partly met | `cornerbrief/guards.py`, `cornerbrief/orchestrator.py`, `tests/test_flow.py` | Regex/number membership is narrower than factual validation and does not cover every agent text field. |
| Check proposed options | partly met | `cornerbrief/orchestrator.py`, `cornerbrief/models.py::RampOption`, `cornerbrief/checker.py` | Checks surveyed evidence, not separate proposed-option geometry or case-specific details. |
| Human release gate and brief download | met | `cornerbrief/app.py`, `cornerbrief/review_export.py`, `tests/test_flow.py::test_download_needs_approval` | Name required for release; release explicitly does not approve design. |
| Browser UI and brief contents | partly met | `cornerbrief/static/index.html`, `cornerbrief/static/app.js`, `cornerbrief/review_export.py` | UI and Markdown cover most named sections; export loses some dates, rate provenance, and safety-source links. |
| Concept geometry and takeoff | partly met | `cornerbrief/parts_kit.py`, `cornerbrief/model_3d.py`, `cornerbrief/takeoff.py`, `cornerbrief/planning.py` | Shared input dimensions, but scene and takeoff are independently constructed and curb geometry differs. |
| Cost range, sample rates, unknown cost | partly met | `cornerbrief/cost.py`, `rates/`, `cornerbrief/static/app.js`, `cornerbrief/review_export.py` | Core cost behavior exists; provenance and sample labels do not consistently follow every exported planning value. |
| Crew, equipment, sequence, safety questions | partly met | `cornerbrief/crew_sequence.py`, `cornerbrief/equipment_types.py`, `cornerbrief/safety_questions.py` | Missing crew rates yield partial totals; crew rates have no aging check. |
| Optional library and outbound email | partly met | `cornerbrief/library.py`, `cornerbrief/email_delivery.py`, `tests/test_flow.py`, `README.md` | Citation-only library and guarded send/dry run exist; live services are unverified. |
| Requested framework/viewer stack | partly met | `requirements.txt`, `cornerbrief/app.py`, `cornerbrief/static/app.js`, `README.md` | Starlette and a canvas renderer replace FastAPI and three.js; README discloses this. |

## 2. Acceptance check and test execution

The requested command was attempted with bytecode writes disabled:

```text
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
exit 127: zsh:1: command not found: python

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q
exit 1: /Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest
```

An earlier attempt with `-p no:cacheprovider` encountered the same environment failures. **No tests collected or ran; there is no passing-test count.** The repository declares pytest in `requirements.txt`. No dependency installation, application server, browser session, live API call, email send, or three-corner CLI run was performed. `scripts/run_demo.py` requires application imports and writes run files through `cornerbrief/orchestrator.py`; it was not used as a substitute for a passing suite. `README.md`'s historical Python 3.13 test claim is not a result from this review.

Every acceptance status below is **not tested** because runtime execution was unavailable. Existing assertions are evidence of intended coverage, not proof they pass. Static deficiencies are recorded separately rather than disguised as runtime failures.

### Three corners

| Acceptance case | Result | Existing evidence and its limit |
| --- | --- | --- |
| Standard: likely ramp type and visible math | not tested | `tests/test_flow.py::test_standard_corner` expects probably standard, a C1 option, two sourced slope results with math, and a positive estimate; fixture is `data/corners/standard.json`. No rendered-browser verification. |
| Constrained: probable custom design and named evidence/site check | not tested | `tests/test_flow.py::test_constrained_corner_flags_custom_with_evidence` expects complex status, Utility Vault, one retry, C3 option, an exceeded limit, a site action, and no planning; fixture is `data/corners/constrained.json`. |
| Missing/stale: identify problems and refuse design | not tested | `tests/test_flow.py::test_missing_or_stale_corner_refuses_design` checks no options/planning, no analyst/Skeptic calls, unknown/not-applicable rows, remeasurement actions; fixture is `data/corners/missing_or_stale.json`. |

### Applicability and core safeguards

| Acceptance case | Result | Existing evidence and its limit |
| --- | --- | --- |
| NYC rejects NYS Uniform Code with reason/source | not tested | `tests/test_core.py::test_nyc_rejects_uniform_code_with_reason_and_source`; `rules/precedence/PREC-NYC-VS-NYS.yaml`. |
| Non-NYC selects NYS and flags source gaps | not tested | `tests/test_core.py::test_non_nyc_selects_nys_rules`, `test_non_nyc_nys_rules_return_unknown_until_sourced`; `rules/precedence/PREC-OUTSIDE-NYC.yaml`. |
| Corner ramp does not use building-code limit | not tested | `tests/test_core.py::test_corner_ramp_does_not_use_building_code_limit`. |
| Building route flags section 1104 without invented numeric limit | not tested | `tests/test_core.py::test_building_route_flags_section_1104`; `rules/nyc/NYC-BC-1104-SITE-ROUTE.yaml`. |
| State-controlled road returns unknown | not tested | `tests/test_core.py::test_state_road_returns_unknown`; covers explicit state control, not unconfirmed ownership. |
| Conflicting tiers show both and use stricter warning | not tested | `tests/test_core.py::test_conflicting_tiers_show_both_and_use_stricter`, `test_conflict_warning_uses_stricter_limit`, `test_width_conflict_compares_feet_and_inches`. No legal-authority validation. |
| Rule math, source metadata, missing values, undocumented units | not tested | `tests/test_core.py::test_slope_limit`, `test_width_converts_inches_to_feet`, `test_verified_rule_without_section_fails`, `test_verified_rule_needs_each_source_field`, `test_needs_source_rule_returns_unknown`, `test_missing_value_returns_unknown_not_pass`, `test_undocumented_unit_returns_unknown`. |
| Placeholders, stale evidence, false measured labels | not tested | `tests/test_core.py::test_placeholder_is_missing`, `test_stale_measurements_are_rejected_as_current`, `test_false_measured_label_is_rejected`. Missing dates and unmatched joins need broader coverage; see `cornerbrief/evidence.py`. |
| Agent cannot supply limits/change results; retry cap | not tested | `tests/test_flow.py::test_agent_cannot_supply_a_limit_field`, `test_agent_output_cannot_change_rule_results`, `test_retry_limit`; these do not prove factual correctness of accepted narrative. |
| Acceptance versus design targets separated | not tested | `tests/test_core.py::test_existing_ramps_are_not_failed_on_design_targets`, `test_design_targets_are_not_conflicts`; `tests/test_flow.py::test_standard_corner_shows_design_targets_without_failing_it`, `test_stopped_corner_has_no_design_targets`. |
| Human release and download/email gate | not tested | `tests/test_flow.py::test_download_needs_approval`; `tests/test_web_and_fetch.py::test_review_flow_over_http` covers API responses, not browser rendering or accessibility. |

### Planning add-ons and optional integrations

| Acceptance case | Result | Existing evidence and its limit |
| --- | --- | --- |
| Hand-checked takeoff, cost, labor | not tested | `tests/test_flow.py::test_takeoff_cost_and_labor_hand_checked` checks areas, volume, curb/removal quantities, cost range, and trade hours. It does not compare drawn geometry to takeoff. |
| One dimension change updates every planning result | not tested | `tests/test_flow.py::test_one_dimension_change_updates_every_planning_result` changes ramp length and compares slab area, base cost, crew hours, and scene. It does not exhaust dimensions or all outputs. |
| Sample rates labeled wherever used | not tested | `tests/test_flow.py::test_sample_rates_are_labeled` checks flags and estimate label, not actual browser/export placement; export labor labels are incomplete in `cornerbrief/review_export.py`. |
| Missing rate yields unknown | not tested | `tests/test_flow.py::test_missing_rate_returns_unknown`, `test_export_handles_missing_rate` cover cost only; missing crew rates leave partial trade totals in `cornerbrief/crew_sequence.py`. |
| Rates older than one year flagged | not tested | `tests/test_flow.py::test_old_rate_is_flagged` covers cost; `cornerbrief/crew_sequence.py` has no equivalent age flag. |
| No takeoff/estimate on missing/stale corner | not tested | `tests/test_flow.py::test_missing_or_stale_corner_refuses_design`; `test_undocumented_units_produce_no_planning` also checks unit gating. |
| No crane selection/position or final PPE list | not tested | `tests/test_flow.py::test_no_crane_or_final_ppe_output` scans standard planning JSON; it is not an exhaustive check of every narrative/export. |
| Library cannot influence rules, rates, design | not tested | `tests/test_flow.py::test_open_library_cannot_affect_results`, `test_open_library_stores_citation_details_only`; fake library responses, no live call. |
| Email blocked without approval/allowlist | not tested | `tests/test_flow.py::test_email_blocked_without_approval`, `test_email_blocked_for_address_not_on_allowlist`, `test_smtp_needs_settings_and_is_off_by_default`; sending test uses FakeSMTP. |

## 3. Gaps, drift, and contradictions

These are confirmed differences from `BUILD_PROMPT.md` or `README.md`, or static risks in the code. A contradiction with the missing PRD itself remains **unverified**.

1. **Rule sourcing has advanced beyond the starter instructions.** `BUILD_PROMPT.md` initially requests H-1011 and ADA rules as `needs_source`. Current H-1011 files include separate `*-ACCEPT` and `*-DESIGN` rules plus general notes, with `status: verified` and `reviewed_by: null` (for example `rules/nyc/H1011-T1-RAMP-RUNNING-ACCEPT.yaml`, `rules/nyc/H1011-T1-RAMP-RUNNING-DESIGN.yaml`, `rules/nyc/H1011-N27-28-CASE-SELECTION.yaml`). The supplied drawing is `docs/sources/H-1011-1.pdf`. `README.md` explicitly limits sourcing to sheet 1 and says sheets 2–9 were not reviewed. This is partial H-1011 coverage, not a fully validated design standard. This review did not independently authenticate the PDF or every transcribed quote/limit.

2. **“Verified” does not mean engineer-reviewed.** `README.md` says Claude checked sources and no person reviewed them. ADA YAML identifies a third-party Corada reproduction and requests confirmation on ada.gov (`rules/federal/ADA-2010-405-2-SLOPE.yaml`). `cornerbrief/rules.py::validate_rule` checks required metadata, but does not verify that a stored limit is supported by its quote or that a source is current. All six precedence files also have `reviewed_by: null` (`rules/precedence/*.yaml`), and `load_precedence` does not require reviewer metadata. `cornerbrief/orchestrator.py::rule_review` counts rule review gaps, not precedence review gaps. Treat legal/source correctness as unverified.

3. **Two distinct status vocabularies must remain distinct.** Rule lifecycle statuses are `verified`, `needs_source`, and `superseded` (`cornerbrief/rules.py`); numeric outcomes are `limit exceeded`, `no conflict found`, `unknown`, and `not applicable` (`cornerbrief/models.py`). Corner summaries are `probably standard`, `probably custom`, and `unknown`; internal Skeptic verdicts are `pass` and `rework` (`cornerbrief/models.py`). Neither a `verified` source nor an internal Skeptic `pass` is a compliance outcome. The unavailable PRD's names cannot be reconciled exactly.

4. **Stage distinctions are an implementation extension.** `cornerbrief/rules.py` additionally requires `stage` with general/design/work-acceptance values, beyond the build prompt's listed metadata. `cornerbrief/checker.py` separates work acceptance from design targets, and UI/export label the latter “If this corner is rebuilt” (`cornerbrief/static/app.js`, `cornerbrief/review_export.py`). Existing-ramp readings should not be presented as proposed design checks. Any PRD without these stage distinctions needs reconciliation rather than a mechanical rename.

5. **Framework and rendering stack differ.** `BUILD_PROMPT.md` names FastAPI and three.js; `requirements.txt` and `cornerbrief/app.py` use Starlette, and `cornerbrief/static/app.js::drawModel` projects geometry onto a 2D canvas. `README.md` discloses the substitution. The renderer caps pixel ratio at 1.5 and redraws on interaction/resize, but this is not evidence of three.js or target-device performance testing (`cornerbrief/static/app.js`).

6. **“Probably standard” is not derived from successful rule checks.** `cornerbrief/orchestrator.py::decide_status` accepts `outcomes` but never uses it: after data sufficiency, only program complexity and recorded obstacles determine standard/custom. Missing sidewalk width, legal grade, and existing ramp type remain site questions (`cornerbrief/evidence.py`, `cornerbrief/site_visit.py`). The standard replay suggests C1 even though path width is absent (`data/replay/standard/site_analyst_0.json`, `rules/nyc/H1011-N27-28-CASE-SELECTION.yaml`). Inference: the headline can sound more authoritative than the evidence permits, especially because it also controls whether planning runs.

7. **Option checking is survey checking, not proposed design validation.** `RampOption` has a case name, rationale, and evidence keys, but no proposed dimensions (`cornerbrief/models.py`). `analyze` calls `run_checks` on the same surveyed evidence regardless of option, while `checked_ramps` checks labels and units rather than numeric rule outcomes (`cornerbrief/orchestrator.py`, `cornerbrief/parts_kit.py`). Consequently planning can be generated for an obstacle-free, sufficient corner even if some limits are exceeded. The build prompt's “checks each option” language overstates this implementation (`BUILD_PROMPT.md`).

8. **Freshness and join failures are warnings with gaps.** `is_stale` only compares parseable survey and later construction dates. An absent/unparseable survey date can still leave a numeric value labeled measured; old measurements without a later construction record remain current under this logic. `latest_construction` uses all supplied progress rows without filtering matching IDs, while `join_report` warns separately and `data_sufficient` ignores join notes. This can misclassify freshness or allow an unmatched/missing progress record through the gate (`cornerbrief/evidence.py`). Dataset-wide age is not checked there.

9. **Road ownership is not conservatively resolved when unconfirmed.** Only `road_control == "state"` forces unknown in `cornerbrief/applicability.py`. `road_control == "not_recorded"` creates an assumed city-street evidence item and a site action while normal applicability continues (`cornerbrief/evidence.py`, `cornerbrief/site_visit.py`). The explicit-state test does not cover this distinction (`tests/test_core.py::test_state_road_returns_unknown`). A person must decide whether that assumption is acceptable even for a clearly synthetic demo.

10. **Missing/stale path skips numerical evaluation, not the checker function.** `BUILD_PROMPT.md` says to skip limit checks. `analyze` calls `run_checks(..., [])` to generate unknown/not-applicable rows, with no dimensions to numerically evaluate, and still computes conflict metadata. `tests/test_flow.py::test_missing_or_stale_corner_refuses_design` tests result categories, not that the checker is never invoked. This is a wording/trace distinction, not evidence that missing measurements are numerically checked (`cornerbrief/orchestrator.py`, `cornerbrief/checker.py`).

11. **Agent guardrails are narrower than the README claim.** `README.md` says checks reject unsupported numbers and compliance claims. `check_text` recognizes specific words and whether a numeric token appears anywhere in the payload, not whether that number supports a specific statement (`cornerbrief/guards.py`). Records summary is not text-checked before entering the writer payload, and Skeptic challenge text is displayed without this guard (`cornerbrief/orchestrator.py`, `cornerbrief/static/app.js`, `cornerbrief/review_export.py`). An invalid Skeptic schema sets `verdict = "pass"` and allows subsequent processing. These are gaps despite useful schema/claim tests (`tests/test_flow.py`).

12. **The visual is not the single modeled takeoff described in the build prompt.** `cornerbrief/planning.py` calls `build_scene(ramps)` separately from `build_takeoff(build_parts(ramps))`. In `cornerbrief/model_3d.py`, two drawn curb pieces are each two feet long and ramp rise is capped at a fixed curb height; `cornerbrief/parts_kit.py` counts curb length as ramp width plus the assumed extra length. The renderer also exaggerates vertical coordinates (`cornerbrief/static/app.js`). These are concept illustrations, but model/quantity fidelity and “every result updates” need more than the existing scene-inequality assertion (`tests/test_flow.py::test_one_dimension_change_updates_every_planning_result`).

13. **Rate handling and labels are incomplete across outputs.** `cornerbrief/cost.py` returns unknown for missing cost rates and flags old cost rates. `cornerbrief/crew_sequence.py` instead accumulates available hours and lists `unknown_rates`, with no rate-age flag. UI renders hours with a sample-rate label but does not render missing crew rates; Markdown prints labor hours without their own sample/missing/age disclosure (`cornerbrief/static/app.js`, `cornerbrief/review_export.py`). `test_sample_rates_are_labeled` only checks backend flags. `load_rates` also omits `currency` from required fields despite the build prompt including it (`cornerbrief/rules.py`, `BUILD_PROMPT.md`).

14. **Export drops useful provenance.** The browser evidence table shows dates; the exported evidence table omits `EvidenceItem.date`. The export gives aggregate cost/sample information but no individual rate/source/date table, and safety questions lose the URL links shown in the browser (`cornerbrief/static/app.js`, `cornerbrief/review_export.py`, `cornerbrief/models.py`, `cornerbrief/cost.py`, `cornerbrief/safety_questions.py`). A downloadable brief should carry the same caution and traceability as its on-screen context.

## 4. Risks for a city audience

| Risk | Evidence | Implication for the demonstration |
| --- | --- | --- |
| Headline can be mistaken for design suitability | `cornerbrief/orchestrator.py::decide_status`, `cornerbrief/static/app.js`, `cornerbrief/guards.py` | Keep “probably standard” explicitly provisional and distinguish it from numerical checks; word guards alone do not prevent an implied compliance claim. |
| Perceived NYC affiliation | `cornerbrief/static/index.html`, `README.md`, `cornerbrief/review_export.py` | Header and README disclaim affiliation. Export carries the pre-design/compliance disclaimer but not the same explicit no-affiliation statement; shared briefs can lose that context. |
| Misattributed city statement in synthetic data | `cornerbrief/orchestrator.py::decide_status`, `data/corners/constrained.json`, `cornerbrief/static/app.js` | “The city's program lists this corner as complex” is used for a made-up corner; the sample banner mitigates this, but the sentence should identify a sample program record. |
| Old ramp measurements alongside newer program data | `docs/data_report.md`, `cornerbrief/evidence.py` | The saved report lists ramp dataset last update as **2021-10-27**, versus **2026-11-01** for progress/complaints. These are report snapshots, not dates independently reverified online. Recent program status does not refresh ramp survey measurements. |
| Sample dates can resemble real freshness | `data/corners/standard.json`, `data/corners/constrained.json`, `data/corners/missing_or_stale.json`, `data/sample_data_dictionary.yaml` | Some synthetic surveys are dated 2023, later than the report's ramp-dataset update. That is fine for invented fixtures only if “SAMPLE DATA” remains visible; do not describe them as portal observations. |
| Sample-rate numbers can anchor expectations | `rates/*.yaml`, `cornerbrief/cost.py`, `cornerbrief/crew_sequence.py`, `cornerbrief/review_export.py` | All included rate files say sample/placeholder; dollar ranges and hours need equally visible warnings in exports, not just backend flags. NYC location labels do not make these market rates. |
| “Class 5” sounds calibrated | `cornerbrief/cost.py`, `BUILD_PROMPT.md`, `cornerbrief/static/app.js` | The code states its range is not tested accuracy. The build prompt supplies an external reference, but `build_cost` does not attach it to results and this review has not verified it. Avoid presenting the range as validated tool accuracy. |
| Survey evidence can appear more direct than it is | `cornerbrief/evidence.py::build_evidence`, `cornerbrief/models.py::Label` | Derived ramp rise is labeled measured; assumed road control is separate. Explain derived versus directly observed values to technical and education audiences. |
| Sample statistics can sound citywide | `docs/data_report.md`, `BUILD_PROMPT.md` | The report sampled the first 1,000 records per dataset; the build prompt warns they are not representative. Do not turn its breakdowns into citywide condition rates. |
| Release can be mistaken for engineering approval | `cornerbrief/review_export.py::approve`, `cornerbrief/static/app.js::releasePanel` | Existing wording correctly distinguishes release from design approval. The gate only checks a nonblank name; it is not authenticated engineer sign-off. |

The most appropriate demo story for the supplied Junior Engineer (Design) audience is preparation of evidence, questions, and a review brief. That is consistent with `README.md` and the junior-engineer/engineer-in-charge writer prompt in `cornerbrief/agents/brief_writer.py`. Do not imply that the prototype replaces agency judgment or validates a constructible design; proposed-option dimensions and reviewed case-specific detail checks are absent (`cornerbrief/models.py`, `README.md`). The possible education attendee does not justify adding student features; `BUILD_PROMPT.md` explicitly excludes them.

## 5. Open questions: answered in the repo versus human decisions

**The PRD's exact open questions cannot be enumerated or marked resolved because both PRD files are absent.** The following are reviewer-derived questions, not invented quotations or reconstructed PRD questions. They should be reconciled to the real list when supplied.

| Reviewer-derived question | What the repository already answers | What still needs a person |
| --- | --- | --- |
| What is the two-week demo scope? | `README.md` gives three saved sample corners; `BUILD_PROMPT.md` excludes gardening and other future products. | Confirm the supplied scope in the actual PRD; keep real fetch and garden dummy tests off the demo critical path. |
| Which requirements and priorities are authoritative? | `BUILD_PROMPT.md` says rules and README supersede its starter rule list, but has no R1–R25 mapping. | Supply the missing PRD and approve version/priority mapping. |
| Who reviews source limits and precedence? | Rule and precedence YAML have reviewer fields; `README.md` says human review has not happened. | Assign a qualified reviewer and record reviewed edition, authority, exceptions, and ownership treatment; no source approval can be inferred from `verified`. |
| How much H-1011 is actually supported? | `README.md`, `docs/sources/H-1011-1.pdf`, and `rules/nyc/H1011-*.yaml` cover sheet 1 transcription and separate stages. | Confirm transcription and relevance; decide whether to review sheets 2–9 or explicitly limit the demo to survey screening and questions. |
| What does standard/custom mean? | `cornerbrief/orchestrator.py::decide_status` uses complexity and obstacles; `cornerbrief/models.py` permits five candidate case names. | Engineer/product owner must agree on provisional wording and necessary evidence before recommending a case. |
| What makes evidence current and trustworthy? | `cornerbrief/evidence.py` handles placeholders, relative construction staleness, and join warnings; live units are assumed in `data/data_dictionary.yaml`. | Set policies for absent dates, absolute age, unmatched/missing joins, ownership, and exact unit documentation. |
| Can the 3D view and estimate be relied on together? | `cornerbrief/planning.py`, `cornerbrief/model_3d.py`, `cornerbrief/takeoff.py` share input dimensions but not one geometry representation. | Decide acceptable illustrative fidelity and audit boundaries; validate quantities before treating them as a design takeoff. |
| Which rates and accuracy claims are allowed? | `rates/` is sample-only; `cornerbrief/cost.py` labels a concept range and excludes tested-accuracy claims. | Choose any approved public/licensed replacement data and permitted estimate terminology; retain explicit sample labels for this demo. |
| Is live AI necessary? | `cornerbrief/llm.py` supports replay; `README.md` says the real-key path has not been run. | Decide whether to demonstrate replay only; live-key validation is a separate, controlled milestone if requested. |
| Are library/email operationally ready? | `README.md`, `cornerbrief/library.py`, `cornerbrief/email_delivery.py`, `tests/test_flow.py` describe citation-only lookup, dry runs, and fake-server testing. | Decide whether optional integrations should be visible at all; provide a contact/address/provider and approve recipient policy before live use. |
| Are the stack substitutions acceptable? | `README.md`, `requirements.txt`, `cornerbrief/static/app.js` disclose and implement Starlette/canvas. | Accept the substitution or explicitly schedule migration; no migration is needed merely to rehearse the sample story. |

## 6. Top five next steps for a two-week build

These are recommendations only; this review implements none of them. Ordering favors a credible sample-corner demo for the supplied audience over later concepts.

1. **Days 1–2: recover the PRD, establish traceability, and make validation runnable.** Obtain both missing PRD sources, replace the unverified R1–R25 rows with exact text/priorities, assign an engineer/product reviewer, and run the declared suite in an isolated supported environment. Record the actual result before claiming acceptance. Establish the three replay corners as the demo baseline (`BUILD_PROMPT.md`, `README.md`, `requirements.txt`, `tests/test_core.py`, `tests/test_flow.py`, `tests/test_web_and_fetch.py`).

2. **Days 2–4: review rule authority and make uncertainty gates explicit.** Have an engineer review H-1011 sheet 1 transcriptions, ADA source provenance, and precedence, including the acceptance/design split. Resolve behavior for unconfirmed ownership, missing dates, and join failures; preserve unknown instead of silently treating missing context as current/city-controlled. Add focused checks for those decisions (`rules/nyc/H1011-*.yaml`, `rules/federal/ADA-*.yaml`, `rules/precedence/`, `cornerbrief/evidence.py`, `cornerbrief/applicability.py`, `cornerbrief/checker.py`).

3. **Days 4–6: tighten the demo's status, narrative, and exported evidence.** Agree on a provisional status definition, prevent source-record findings from sounding like a checked proposed design, guard all agent text that reaches users, and treat absent Skeptic review as incomplete review. Put sample/no-affiliation notices, evidence dates, and rate/safety provenance into the released brief. Test adversarial narrative and standard-looking corners with exceeded limits (`cornerbrief/orchestrator.py`, `cornerbrief/guards.py`, `cornerbrief/models.py`, `cornerbrief/static/app.js`, `cornerbrief/review_export.py`, `tests/test_flow.py`).

4. **Days 6–8: reconcile the concept model and planning outputs, or narrow their demo claim.** Align the drawn curb/rise with the modeled parts/takeoff, propagate a dimension change through dependent calculations, mark missing crew rates unknown, and show sample/age/provenance warnings beside labor and money in UI and export. Retain the explicit exclusions and concept-only label; do not add live rates or a garden feature (`cornerbrief/model_3d.py`, `cornerbrief/parts_kit.py`, `cornerbrief/planning.py`, `cornerbrief/takeoff.py`, `cornerbrief/cost.py`, `cornerbrief/crew_sequence.py`, `cornerbrief/static/app.js`, `cornerbrief/review_export.py`, `rates/`, `tests/test_flow.py`).

5. **Days 8–10: rehearse and record the actual engineer workflow.** Run the full suite and the three saved-corner demonstrations, verify browser math/source/unknown displays, keyboard navigation, model behavior, release/download, and exported warnings on the demo machine. Record pass/fail evidence and limitations; rehearse explaining the 2021 dataset snapshot and fictional fixtures to both engineers and a nontechnical attendee. Keep real fetch, garden dummy tests, and live external integrations outside this rehearsal (`README.md`, `scripts/run_demo.py`, `cornerbrief/static/index.html`, `cornerbrief/static/app.js`, `docs/data_report.md`, `tests/test_web_and_fetch.py`).

### UI/export ownership if these recommendations become an orchestrated build

Assign **exactly one UI task, “Demo UI and Output owner,” sole ownership of `.helix/output/**`** in that future build plan. That task should own the browser presentation changes in `cornerbrief/static/**`; dependent backend/export/planning tasks must coordinate their response contracts and UI needs through it. No other worker may edit `.helix/output/**`. This is proposed task ownership, not a worker assignment or authorization to edit during this review.

The present app requires Python endpoints for listing/running corners, release, download, and email (`cornerbrief/app.py`, `cornerbrief/static/app.js`); its HTML also uses absolute asset URLs and external fonts (`cornerbrief/static/index.html`). Merely copying these assets into a backend-free preview will not yield a working demo. No compiled static-export command is supplied in `README.md` or `requirements.txt`. The future UI owner must either obtain an approved way to export the actual application's functionality, using relative asset URLs and no unsupported backend dependency, or report that limitation. It must not fabricate a separate imitation. **This review creates no Output artifact and starts no server**, consistent with the single-file review scope.
