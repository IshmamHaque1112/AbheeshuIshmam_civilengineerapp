# CornerBrief Round 2 design review

This publishes the available Helix concept images and submitted seven-task plan for Ishmam to review. The latest snapshot is revision **3**, status **ready**, recorded at 2026-11-06T00:07:19.203Z. Images are copied without modification; SHA-256 hashes are in `manifest.json`. Earlier explorations are included for comparison. A historical approval of an earlier revision does not approve the latest one.

**This is a runnable concept gallery, not an implemented Round 2 workflow.** The existing corner investigation and synthetic ramp/landing preview are runnable separately. Publication does not change design approvals, merge an implementation, or bypass evidence and rule gates.

## Run the design gallery

After checking out this PR branch, from the repository root:

```sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory docs/design/round-2
```

Open http://127.0.0.1:8080 . No packages, API keys or external network requests are needed. Click each image for full size. You can also open `index.html` directly.

## Run the current CornerBrief application

Use Python 3.10 or newer. On macOS/Linux, from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
DEMO_MODE=true EMAIL_ENABLED=false SHOW_LABELS_AND_PLANS=false python -m cornerbrief
```

Open http://127.0.0.1:8000 for the investigation app and http://127.0.0.1:8000/preview.html for synthetic 3D exploration. Use the sample corners for offline demo responses. The sample data is fictional; the saved real corner has its own evidence limitations. If port 8000 is occupied, run `DEMO_MODE=true EMAIL_ENABLED=false SHOW_LABELS_AND_PLANS=false python -m uvicorn cornerbrief.app:app --host 127.0.0.1 --port 8766` and use that port instead. See the root README for Windows setup.

## What to review

1. Try the existing investigation flow and 3D preview. Identify useful automation, missing information and confusing interactions.
2. Compare the latest concept images against the proposed six stages: corner evidence, geometry eligibility, quantities and revision, draft work packages, company resources, changes and recalculation.
3. Recommend a concept direction or explain what needs changing; do not assume publishing means the direction was selected.
4. Check that actual, assumed, stale, unresolved and synthetic inputs are easy to distinguish, and that missing company resources stay unknown.
5. Recommend the smallest useful implementation milestone, with an example task an engineer should be able to finish and what would demonstrate success.

Please reply to Abheeshu on Slack with your recommendations. `plan.json` is the actual plan submitted in Helix, not a claim that its tasks are complete. [Proposal #7](https://github.com/IshmamHaque1112/AbheeshuIshmam_civilengineerapp/issues/7) remains the broader product direction. Existing runtime code is unchanged by this publication.
