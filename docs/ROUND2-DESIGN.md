# Round 2 shared data contract

November 5, 2026 · Refs [issue #7](https://github.com/IshmamHaque1112/AbheeshuIshmam_civilengineerapp/issues/7) · Companion to [`ROADMAP.md`](ROADMAP.md)

This file didn't exist when M2a started, so it sets down the data contract the six roadmap stages share. It's taken from the workflow in `ROADMAP.md` and the gates in `PRD.md`. No separate Helix plan is stored in the repository, so nothing here goes beyond those two documents.

This is a backend contract. It doesn't choose a Round 2 interface concept. The latest Round 2 concepts still need a separate human selection, and nothing here approves one or depends on which is picked.

## Stages

| # | Stage | Produces | Status |
| --- | --- | --- | --- |
| 1 | Opportunity brief | Location, scope, deadline, qualifications, documents, open questions, each tied to a source page | Proposed (M3) |
| 2 | Site investigation | Evidence items with labels, rule results, site-visit list, field measurements and reruns | Built (M0) |
| 3 | Editable 3D concept | Geometry from dimension inputs, with each input's status | Synthetic sandbox built (M1). Documented-input readiness built in M2a. |
| 4 | Quantities and draft logistics | Provisional quantities, then work packages | Quantities built behind the existing gates. Work packages proposed (M2). |
| 5 | Crew, equipment and delivery sequence | Sequence from company records, with missing inputs listed | Proposed (M2/M3) |
| 6 | Reviewable paperwork | Draft RFIs, material requests, daily reports, payroll checks | Proposed (M3) |

## Input status

Every input a later stage reads carries exactly one of these, plus its own source, date, recorded value, recorded unit, unit-documentation state and reason.

| Status | Meaning | May feed geometry? |
| --- | --- | --- |
| documented | Measured, current, with a documented unit the model can convert | Yes, through the existing gate |
| assumed | Labeled assumed by the evidence step, for example a later ramp permit at the ramp | No |
| stale | Measured before the latest construction | No |
| unresolved | Missing, a placeholder such as 999, an unreadable number, no unit, an undocumented unit or a unit the model can't use | No |

Statuses only move toward documented through a new record or a field measurement and a rerun. No stage fills a gap, converts an unsupported unit or promotes an assumed or synthetic value.

Unit rules: lengths are converted only from `in` or `ft`, to feet. Slopes stay percentages and are never converted to a length.

## Revision

Stages 3 and 4 share one revision, from `cornerbrief/revision.py`. It hashes:

- the dimension values the geometry actually used,
- the assumptions the takeoff actually used, and
- the model version (`MODEL_VERSION`), which changes whenever the geometry or takeoff math does.

Same basis, same revision. A changed dimension, assumption or model version gives a new revision. Where a value came from (source, date) is recorded in the basis but doesn't change the revision, because it doesn't change the geometry.

Later stages (work packages, sequences, paperwork) must record the revision they were built from, and mark themselves "needs recalculation" when the current revision differs. That marking isn't built yet.

## Gates that every stage keeps

- The evidence gate (`parts_kit.checked_ramps`) stays all or nothing. Readiness explains it and doesn't loosen it.
- Rule review: only rules a named person verified give a final limit result.
- Concept outputs (R4, R11, R21–R25) stay off by default and need complete evidence, a finished review, verified rules and no exceeded limit.
- Packet release needs a person's name and is never approval.
- City demo: no dollar figures, and placeholder rates stay labeled.
- No stage invents a rate, duration, crew or resource.
