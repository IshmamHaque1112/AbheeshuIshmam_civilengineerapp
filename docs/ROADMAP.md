# CornerBrief staged roadmap

November 5, 2026 · From [issue #7](https://github.com/IshmamHaque1112/AbheeshuIshmam_civilengineerapp/issues/7) · Companion to [`docs/PRD.md`](PRD.md) section 8

This roadmap records a proposed product direction. It does not claim the features exist, that the new persona is validated, or that any engineering domain beyond small concrete corner work is supported. Each milestone below says what is **built now**, what is **next** and what is **proposed for later**.

## Direction

CornerBrief could help a construction team turn a job opportunity into a traceable site investigation, an editable 3D concept and a resource-backed execution proposal, all for professional review.

The milestones keep the current promise intact. Evidence and rule gates, the "stop: evidence still needed" state, the off-by-default concept outputs (R4, R11, R21–R25), the city-demo ban on dollar figures and the placeholder-rate disclosures all stay as they are. Nothing in this roadmap lets a model, a synthetic value or a schedule override them.

## Users

| User | Status |
| --- | --- |
| DDC Junior Engineer (Design), Pedestrian Ramps Program | Current primary user (PRD §1b). Not yet tested with a real engineer (R29 pending). |
| Engineer-In-Charge / reviewer | Current secondary user. Signs off; the tool never reads as permission. |
| Estimator or project engineer at a NYC union contractor | **Hypothesis.** Not validated by customer research. Interviews and a role test are needed before any milestone below M2 is built for them. |

The proposed "phantom bot engineer" is a digital project-engineering assistant that helps assess jobs and coordinate resources. It prepares drafts for people. It does not bid, hire, purchase, file permits, submit payroll or approve engineering.

Union membership does not by itself give access to crews, equipment, bidding authority or professional credentials. Availability, qualifications, work rules and authority must come from the company's actual records and the agreements that actually apply to the job.

## Proposed workflow (target, not built)

1. **Opportunity brief.** Extract location, scope, deadline, required qualifications, documents and open questions. Compare them against the company's verified capabilities and prequalification status.
2. **Site investigation.** Gather site records and produce the list of missing or stale evidence and the field measurements needed. *This is today's CornerBrief for street corners.*
3. **Editable 3D concept.** Build parameter-driven, dimensioned geometry from documented measurements, with unknown, assumed and synthetic inputs visibly separated.
4. **Quantities and draft logistics.** Provisional quantities and work packages, candidate equipment, staging, delivery access, material lead times, pedestrian access, demolition and waste removal, permits and utility coordination.
5. **Crew, equipment and delivery sequence.** Use actual availability, trade qualifications, applicable labor rules and company production history. Expose missing inputs and schedule conflicts instead of inventing rates or durations.
6. **Reviewable paperwork.** Draft RFIs, material requests, daily reports and payroll discrepancy checks.

External bidding, hiring, purchasing, permit submission and payroll submission each need their own explicit authorization. None of them follows automatically from this workflow.

### The core connection

The 3D model and the logistics plan should eventually share one versioned parameter and quantity basis. Changing a dimension recalculates the affected quantities and marks dependent estimates and schedules for recalculation. A sequence preview must come from an explicit proposed work plan. A rotating model alone does not show that anything can be engineered or built.

## Milestones

### M0: Current demo (built, Nov 12 scope)

Corner investigation packet, evidence labels, rule results, site-visit list, field measurements and rerun, release, P1 search and traces, R28 adversarial suite. Concept plans stay off by default. See PRD §4–§5.

### M1: Synthetic 3D sandbox for corners, ramps and landings (built in this slice)

A separate page, `/preview.html`, offers an editable, parameter-driven ramp and landing model. It is a sandbox. It is not part of any evidence packet.

| # | Acceptance criterion (user-observable) | Status | Evidence |
| --- | --- | --- | --- |
| M1.1 | Ramp width, ramp length, landing width, landing length (ft) and running slope (%) are editable with number fields and sliders, and every label shows its unit. | Met | `tests/test_browser.py::test_preview_slider_updates_the_model`, screenshots in `docs/evidence/3d-preview/` |
| M1.2 | A valid edit visibly changes the geometry, the dimension labels and the provisional quantities, and the quantities table shows the change. | Met | `test_preview_edit_updates_model_and_quantities`; `tests/test_preview.py::test_each_dimension_moves_its_own_quantities` (hand-checked) |
| M1.3 | Drag orbits, scroll zooms, and shift-drag or right-drag pans. Buttons and keys do the same, and Reset view restores the start. | Met | `test_preview_orbit_zoom_and_pan_change_the_view`, Chromium probe in `docs/3D-SLICE-VERIFICATION.md` |
| M1.4 | Dimension labels stay readable and don't overlap while orbiting. | Met | `test_preview_dimension_labels_stay_readable_while_orbiting` |
| M1.5 | A missing, out-of-range or non-numeric value names the field and its valid range. No geometry or quantity is invented. The last valid model stays, marked **Not updated** on the canvas, in an alert and on dimmed quantities. No console errors. | Met | `test_preview_invalid_dimension_keeps_the_last_model_and_explains`, `test_bad_dimensions_give_feedback_and_no_model`, `test_missing_dimension_isnt_filled_in` |
| M1.6 | Every output shows its unit, its input provenance (synthetic, assumed, unknown/not modeled) and a revision. The revision covers the dimensions, the assumptions actually used and a basis version for the geometry and takeoff math, so changing any of them gives a new revision. | Met | `test_input_basis_separates_synthetic_assumed_and_unknown`, `test_changed_assumption_changes_quantities_and_revision`, `test_basis_version_is_part_of_the_revision`, `test_every_output_states_its_units_and_source` |
| M1.7 | Changing a dimension tells the user which earlier revision is superseded and that estimates or schedules built on it must be recalculated. | Met Nov 9, through the draft sequence (M2.2). | `test_preview_revision_change_flags_dependent_estimates` |
| M1.8 | Synthetic values never reach a packet, label, plan, rule check or field measurement, and the page makes no other API call. | Met | `test_preview_cant_touch_packets`, `test_preview_makes_no_packet_requests_and_main_page_links_to_it` |
| M1.9 | No dollar figures, crew hours, rule results or permission words appear in the sandbox. | Met | `test_preview_has_no_dollars_crew_rule_results_or_permission` |
| M1.10 | The concept 3D view inside real evidence packets stays off by default and gated (R4, R11, R25). | Met (unchanged) | `tests/test_v3.py`, `tests/test_p1.py`, `tests/test_bugfixes.py` |

Known limits of M1: the renderer is a lightweight 2D-canvas projection with flat shading (to respect the integrated-GPU limit in `BUILD_PROMPT.md`), not WebGL. It models one ramp and one landing, with no flares, cross slope, gutter or sidewalk edge. Height is drawn at 3× by default (toggleable) so slopes are visible.

### M2: Documented geometry → quantities → draft small-concrete sequence (next)

| # | Acceptance criterion | Status |
| --- | --- | --- |
| M2.1 | For a real packet whose evidence passes the existing gates, the concept model is built only from measured, current, unit-documented values, and each dimension label cites its record. | Met Nov 9: each label on the concept model shows its value and recorded value, and the full citation is listed under the plan and in downloads. `tests/test_m2.py` |
| M2.2 | Geometry, quantities and any draft plan carry one shared revision. Editing a dimension recalculates quantities and marks the dependent draft estimate and sequence "needs recalculation" until rerun. | Met Nov 9: the preview's draft stays on its revision and says "Needs recalculation" until rebuilt; a packet rerun notes a changed revision. `tests/test_m2.py`, `test_preview_draft_needs_recalculation_until_rebuilt` |
| M2.3 | A draft small-concrete work sequence (sawcut, demolition, forming, pour, cure, warning surface, restoration) is shown only as an explicit proposed plan with every unknown duration and resource marked unknown. | Met Nov 9: `cornerbrief/work_plan.py`, on the preview page and in gated concept plans |
| M2.4 | Missing crews, equipment, rates or durations are listed as missing inputs. Nothing is filled from generic trade data. | Met Nov 9. The draft sequence lists them, and labor hours are now unknown while only placeholder sample rates exist. |
| M2.5 | The city demo still shows no dollar figures, and placeholder rates stay labeled. | Met (unchanged) |

### M3: Contractor workflow (later, after validating the persona)

Only after interviews and a role test with real estimators or project engineers. As of Nov 9, `/demo/contractor.html` (off unless `SHOW_ROADMAP_DEMOS=true`) demonstrates every criterion with a fictional sample company (`data/demo/sample_company.yaml`), synthetic quantities and a real corner's records. It's stamped DEMONSTRATION, saves nothing and submits nothing, so none of these criteria is met with real company data yet.

| # | Acceptance criterion | Status |
| --- | --- | --- |
| M3.1 | An opportunity brief lists location, scope, deadline, qualifications, documents and open questions, each tied to its source page. | Demonstrated: each brief line links its source or says unknown (`tests/test_m3_m4.py`) |
| M3.2 | Capability and prequalification match uses the company's verified records only, and shows "unknown" where a record is missing. | Demonstrated: only verified sample records match; the rest stay unknown (`tests/test_m3_m4.py`) |
| M3.3 | A draft logistics plan covers staging, delivery access, lead times, pedestrian access, demolition, waste removal, permits and utility coordination (for example New York 811), with each item linked to its source or marked unknown. | Demonstrated, including active block permits and New York 811 (`tests/test_m3_m4.py`) |
| M3.4 | Crew and equipment sequencing uses actual availability and production history, and shows conflicts instead of resolving them silently. | Demonstrated: sample availability and production records; conflicts listed, never resolved (`tests/test_m3_m4.py`) |
| M3.5 | Labor rules come from the specific contract and agreement for the job. One project labor agreement is never applied to every union job. | Demonstrated: an agreement applies only to a job it names (`tests/test_m3_m4.py`) |
| M3.6 | RFIs, material requests, daily reports and payroll discrepancy checks are drafts for a person. Submitting any of them is a separate, authorized action. | Demonstrated: drafts only, with a payroll versus daily-report hours check (`tests/test_m3_m4.py`) |

### M4: Specialist structure modules (future, research only)

The four earlier interactive demos (Pratt truss bridge, lattice transmission tower, geodesic dome and animated gear train) set the long-term bar for **breadth and interaction quality**: procedural geometry from named parameters, smooth orbit, zoom and pan, and readable structure.

As of Nov 9, `/demo/structures.html` (off unless `SHOW_ROADMAP_DEMOS=true`) is a geometry-only sandbox for all four: Pratt truss, lattice tower, geodesic dome and a three-gear train, with named parameters, orbit, zoom and pan. It draws shapes only. They are not supported engineering domains. Each would need its own feasibility research, a qualified engineer, domain rules and validation before any work starts. CornerBrief does not design bridges, towers, domes or mechanisms. The sandbox applies no loads or checks, and CornerBrief makes no claim about structural safety, compliance or approval for anything it draws.

## Research references to follow up

These are starting points for discovery. Before any rule is implemented, verify the actual contract, jurisdiction and current requirement, and record the source the way `rules/` does.

- NYC project labor agreements (MOCS): https://www.nyc.gov/site/mocs/regulations/project-labor-agreements.page
- NYC DDC prequalified lists (RFQ/PQL): https://www.nyc.gov/site/ddc/contracts/rfqpql.page
- NYC DOT street-work permits: https://www.nyc.gov/html/dot/html/infrastructure/permits.shtml
- NYSDOL certified payroll, including NYC submission routing: https://dol.ny.gov/node/64811
- New York 811 coordination process: https://newyork-811.com/about/how-we-work/

None of these was used to write a rule, limit, rate or duration in this slice.
