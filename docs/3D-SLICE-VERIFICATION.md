# 3D sandbox slice: recovery and verification

November 5, 2026 · Helix session `session_2bfbe6adcd8845e59048b81823259626` · Branch `helix/cornerbrief-recovery-editable-3d-and-contractor` · Refs [issue #7](https://github.com/IshmamHaque1112/AbheeshuIshmam_civilengineerapp/issues/7)

## Recovery

- Helix reported a stale start at `429c6b4`. The worktree was actually at `541653b`. `git fetch origin` (narrow network access) confirmed that `origin/main` is `541653b`.
- The P1 commit `d1bb494` is already on `origin/main` through merged PR #6 (`73aa095`), followed by `2300690`, `79b4853`, `a82b9e7`, `97446e8`, `75a07c7` and `541653b` ("Add a synthetic 3D corner preview"). Nothing was cherry-picked, so no merged commit is duplicated. The old P1 branch and `main` were not modified.
- `gh pr list --state all` showed PRs #1–#6, all merged, and no open PR. So this branch opens a new draft PR. It builds on the 3D preview already on `main` and supersedes no open PR.

## What this slice changes

1. **Invalid or missing dimensions.** Before this change, the old model and quantities stayed on screen looking current, and each invalid edit logged a `400 (Bad Request)` console error. Now the canvas shows **NOT UPDATED · fix <field> · showing revision <r>**, an alert repeats it, and the quantity table is dimmed. The browser rejects blank or out-of-range values before sending them. The server still validates every value.
2. **Readable labels.** Dimension labels overlapped at some orbit angles. They now move clear of each other, with a leader line, and stay inside the canvas.
3. **Input provenance.** A new "What the model is built from" panel lists synthetic inputs (typed in), assumed values (sample assumptions with units) and what isn't modeled (left unknown).
4. **Revision change.** After an edit, the page names the superseded revision and says that estimates or schedules built on it must be recalculated.
5. **Takeoff bug.** For a ramp shorter than the assumed 2 ft warning-surface depth, the takeoff counted more warning surface than the ramp could hold (10 sf on a 1.5 × 5 ft ramp), even though the model drew 7.5 sf. `parts_kit.build_parts` now caps it at the ramp length, so the model and quantities agree.
6. **Revision basis** (from review). The revision used to hash only the typed dimensions, so a changed sample assumption could change quantities under the same revision. It now hashes the dimensions, the assumptions actually used and `preview.BASIS_VERSION` (now 2, for the warning-surface fix). The revision IDs quoted below were observed before this change, so current IDs differ.
7. **Live Output.** `scripts/export_ui.py` now also writes `.helix/output/preview.html`, the real preview page with its default model built by the app's Python code. Orbit, zoom and pan work there. Editing dimensions is disabled with a note, because each edit needs the local backend.

## Observed verification

Environment: Python 3.12.16 `.venv` inside this worktree, Playwright Chromium (headless), macOS.

| Check | Command | Result |
| --- | --- | --- |
| Baseline on `541653b` before changes | `.venv/bin/python -m pytest -q` | 363 passed, 0 skipped. Inside the sandbox, 26 localhost-socket errors and 27 skips; rerun with local binding allowed. |
| Full suite after changes | `.venv/bin/python -m pytest -q` | 375 passed, 0 skipped. Chromium browser tests executed. |
| Live app | `uvicorn cornerbrief.app:app --host 127.0.0.1 --port 8765` | `GET /preview.html` returned 200 |
| Browser probe, live app | Playwright script driving drag, wheel, right-drag, typing, blank and out-of-range values, and the main-page link | Orbit, zoom and pan each changed the canvas pixels. Labels: 5 placed, 0 overlaps across 12 orbit steps. Width 5 → 9 ft gave slab 55 → 79 sf (+24) and warning surface 10 → 18 sf. Slope 6 → 12% gave rise 4.3 → 8.6 in. A blank length gave "Ramp length must be a number from 1 to 30 ft." with the Not updated state. 45 ft gave the same message. Recovery to 7 ft gave "up to date." **0 console errors or warnings, 0 page errors.** |
| Browser probe, static export | `file://.../.helix/output/index.html` → 3D preview link | Rendered, and orbit changed pixels. Inputs disabled, with the backend-required note. 0 non-file requests and 0 console or page errors. |

Screenshots from the final run are in `docs/evidence/3d-preview/`:
`01-default.png`, `02-orbit.png`, `03-zoom-pan.png`, `04-width9.png`, `05-slope12.png`, `06-missing.png` and `07-static-export.png`.

## Limits

- The renderer is a flat-shaded 2D-canvas projection, chosen for the integrated-GPU limit. It is not WebGL. Interaction quality is below the reference three.js demos, which also load three.js from a CDN that the offline app avoids.
- The model covers one ramp and one landing. Flares, cross slope, gutter, sidewalk edge, utilities and road ownership are not modeled and are listed as unknown.
- No estimates or schedules are saved yet, so "must be recalculated" is a message, not a tracked invalidation (roadmap M2.2).
- Nothing here is a structural, safety, compliance or approval claim. No bridge, tower, dome or gear generation is supported.
- The contractor persona is a hypothesis. No interviews, role tests (R29) or rule reviews took place.
