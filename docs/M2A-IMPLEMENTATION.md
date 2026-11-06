# M2a: measurement readiness and a shared revision

November 5–6, 2026 · Refs [issue #7](https://github.com/IshmamHaque1112/AbheeshuIshmam_civilengineerapp/issues/7) (doesn't close it) · Contract: [`ROUND2-DESIGN.md`](ROUND2-DESIGN.md)

M2a is a backend milestone. It makes each ramp dimension explain its own status and gives the gated planning output a basis and a revision. It doesn't change when planning runs, turn on any concept output, mark any rule reviewed, add any measurement or pick a Round 2 interface concept.

## What changed

| File | Change |
| --- | --- |
| `cornerbrief/revision.py` | New. `MODEL_VERSION` (still 2) and `revision()`, moved from the preview unchanged. |
| `cornerbrief/preview.py` | Uses the shared function. `BASIS_VERSION` is `MODEL_VERSION`. Every revision value is the same as before. |
| `cornerbrief/readiness.py` | New. One row per ramp for ramp width, ramp length, landing width, landing length and running slope. |
| `cornerbrief/planning.py` | The existing eligible output also returns `basis` and `revision`. The permission check is untouched. |
| `tests/test_readiness.py` | 31 new tests. |
| `docs/ROUND2-DESIGN.md` | New. It didn't exist, so it sets out the six-stage contract from `ROADMAP.md`. |

## Requirements and evidence

| Requirement | Where | Test in `tests/test_readiness.py` |
| --- | --- | --- |
| One row per dimension with its own source, date, recorded value, unit, unit-documentation state and reason | `readiness.dimension_rows` | `test_every_ramp_gets_one_row_per_dimension_with_its_record` |
| Only documented `in`/`ft` lengths convert to feet. Slope stays a percentage. | `readiness.TO_MODEL` | `test_slope_stays_a_percentage` |
| One stale dimension leaves the other rows inspectable; the gate stays all or nothing | `readiness.readiness` | `test_one_stale_dimension_leaves_the_others_inspectable`, `test_stale_corner_keeps_every_record_and_stays_stale` |
| Missing, blank, 999 and 9999 are unresolved and never filled in | `_row` | `test_missing_and_placeholder_values_are_unresolved_and_never_filled_in` (4 cases), `test_a_measured_placeholder_is_still_unresolved`, `test_a_dimension_with_no_record_is_unresolved` |
| Undocumented, missing or unsupported units are unresolved | `_row` | `test_undocumented_unit_is_unresolved_and_blocks_like_before`, `test_unsupported_or_missing_unit_is_unresolved` |
| Assumed stays assumed, with the saved corner's own reason | `readiness.STATUS` | `test_saved_real_corner_keeps_its_assumptions_and_their_reasons` (`data/live/real_test.json`, ramps 116256 and 116252) |
| A field measurement keeps who, when and its unit; it doesn't refresh other rows | `_row` | `test_on_site_measurement_keeps_who_when_and_its_unit` |
| Readiness doesn't change the evidence | | `test_readiness_never_changes_the_evidence` |
| Planning basis: every effective input with its record, the assumptions used with their reasons, the model version | `planning.planning_basis` | `test_planning_basis_cites_each_input_and_the_assumptions_used` |
| Identical inputs, identical revision | `revision.revision` | `test_identical_inputs_give_identical_revisions` |
| A changed dimension, assumption or model version changes the revision | | `test_changing_a_planning_dimension_changes_the_revision` (4 cases), `test_changing_an_effective_assumption_changes_the_revision`, `test_model_version_is_part_of_the_planning_revision` |
| Planning is permitted exactly as before | `planning.run_planning` | `test_planning_is_permitted_exactly_as_before`, plus the existing gate tests in `test_flow.py`, `test_bugfixes.py`, `test_v3.py`, `test_p1.py` |
| Preview revisions are unchanged | `preview.build_preview` | `test_preview_revisions_are_unchanged` (5 values recorded from `main` at `c8e0aeb`), `test_preview_and_planning_share_one_model_version`, and all of `tests/test_preview.py` |

### Test results observed

- Against `main` (`c8e0aeb`) with only the new import removed: 26 failed, 5 passed. The 5 passing are the preview-revision pins, which are meant to pass before and after.
- With this change: `tests/test_readiness.py` 31 passed.
- Full suite with this change, including the Playwright browser tests: 464 passed, 0 skipped, 0 failed.
- Inside the sandbox, 26 server and browser tests error with `PermissionError` on binding 127.0.0.1. That's the sandbox's localhost restriction; the same tests pass when binding is allowed. Before this change the sandboxed baseline was 376 passed, 31 skipped, 26 errors, all of them that same bind error.

## Known limits and decisions left to people

- **Readiness isn't on screen yet.** `orchestrator.py` and `cornerbrief/static/app.js` were outside this task's ownership. Showing the rows needs `analyze()` to add `dimension_readiness=readiness(evidence)` to the run, and the packet page to render it. That's the next step below.
- **The gate and readiness can disagree on units.** `parts_kit.checked_ramps` reads any unit other than `in` as feet. Readiness calls an unsupported unit unresolved and sets `gate_note` when the gate still allows it, and the planning basis marks that input unresolved. Today every unit comes from the data dictionaries or `field.UNITS` (`in`, `ft`, `percent`), so this doesn't happen with current data. Tightening the gate needs a reviewed decision, so it's unchanged (`test_unsupported_unit_the_old_gate_accepts_is_reported_not_hidden`).
- **Recalculation flags aren't built.** Nothing yet stores an estimate or sequence against a revision, so nothing is marked "needs recalculation." M1.7 stays partly met.
- **Stop semantics are unchanged.** Whether an unresolved required input stops the whole packet or only the affected checks is still the open PRD §5 question (`docs/P0-REVIEW.md` reads it more strictly). M2a doesn't decide it.
- Planning still runs only when the label is "probably standard," so in the demo, with labels off and rules unreviewed, no corner gets a basis or revision on screen.

## Nov 12 demo readiness (as of Nov 6)

Nothing below is marked done without attributable evidence in the repository.

| Item | Status | Evidence or owner |
| --- | --- | --- |
| Four-corner flow (Queens, Brooklyn, real Thomson Ave corner, Bronx stop) | Built and covered by automated tests on saved data. Not rehearsed by a person for this change. | `tests/test_flow.py`, `tests/test_browser.py` |
| Field measurements, rerun, change report, release with a name | Built and tested on sample corners. No real field measurements exist for the real corner. | `tests/test_flow.py`, `tests/test_web_and_fetch.py`. Field sheet: pending |
| Unresolved inputs: whole-packet stop or per-check stop | **Pending team decision.** Unchanged by M2a. | PRD §5 "Still open", `docs/P0-REVIEW.md` |
| Named rule review | **Pending.** No rule is `verified`, so every limit stays "unknown." | PRD §7, owner Abheeshu |
| R29 with a real junior engineer and a real reviewer | **Pending.** No participant results exist. | `docs/R29-ROLE-TEST.md` |
| Timed manual baseline on 3 Thomson Ave corners | **Pending.** No timings recorded. | PRD §2 and §7, owners both |
| Interview feedback for the contractor persona | **Pending.** None recorded. | PRD §7 |

## Environment notes

- GitHub (`git fetch`, `gh pr list`) and PyPI timed out through the sandbox proxy on Nov 5, so open PRs couldn't be checked remotely. Local `main` at `c8e0aeb` had no readiness or revision work, and the worktree was clean.
- The worktree's own `.venv` (Python 3.12.16) was filled offline from an existing local Python 3.12 install's packages, because PyPI wasn't reachable. It's ignored by git.
- No UI changed, so `.helix/output/` wasn't rebuilt.

## Smallest next milestone (M2b, needs its own approval)

Show the readiness rows in the packet. Own `cornerbrief/orchestrator.py` (add `dimension_readiness` to the run), `cornerbrief/static/app.js` (a dimension table with status, source, date, unit and reason) and `.helix/output/**`, with a browser test that a stale dimension appears next to the documented ones. Work packages, resources and the Round 2 interface stay separate reviewed tasks after that.
