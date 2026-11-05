# R29 participant protocol

Status: **pending real human participation**. No participant results are supplied. A passing script or agent role-play cannot complete R29.

Recruit one actual junior engineer and one actual engineering reviewer. A facilitator records observations without coaching. Obtain consent to record attributed observations; use participant IDs with a separately retained attribution roster if names cannot be shared. Do not record credentials or private project records. Allow 20–30 minutes per role, and use the same corner for both.

## Setup and capture

1. Run `python -m cornerbrief` (see README for the local app URL). Keep demo mode on. Planning stays disabled and rules stay unreviewed. Do not change rule files to make the exercise pass.
2. In the app search QUEENS / THOMSON, select one actual corner and record its ID, streets, source URLs/retrieval times, dataset labels, application commit and packet run ID. Freeze this packet for both roles. If NYC is unavailable, postpone the real-corner exercise or explicitly record a separate SAMPLE DATA rehearsal using the Queens sample; it does not establish real-corner completeness.
3. Run `python scripts/role_test.py init r29-capture.json`. This exclusively creates a pending capture and refuses to overwrite results. Fill its metadata. Leave human participation false until each actual person participates.
4. Start a stopwatch and record ISO start/end timestamps with timezone for each role, including corrections/rework. Record observed elapsed seconds, not a guessed duration. Use the capture arrays for exact observations; `null` means not recorded, `[]` means explicitly observed none.

## Junior engineer task card (read verbatim)

“Prepare this corner for an Engineer-In-Charge's review. Find its ramp, construction and complaint records. Identify what is measured, assumed, stale or missing, and cite the source and date of one input. Explain which checks can be interpreted and which remain unknown. Prepare the site-visit list. If the facilitator supplied a genuine dated field sheet, enter only those measurements, rerun and explain what changed. Explain the next action you think the packet permits.”

Do not supply invented field measurements for a real corner. If there is no field sheet, the correct action is to leave the gaps. Observe whether the participant notices undocumented real-data units, unknown road control, missing matches/dates, unreviewed rules and the individual evidence stops. Log every correction, assistance request and missed issue, with the affected input/check. Time ends when the participant hands the packet to the reviewer. Release/download requires their own name and is explicitly not approval.

## Reviewer task card (read verbatim)

“Review the same corner packet and any rerun. Trace one calculation to its rule, exact section, quote and URL. Inspect agent inputs, outputs and actual token use. Explain how saved replay, offline logic and a provider response differ. Check the evidence dates, unresolved checks and any changes. Say whether you would return the packet, request a site visit, or take another action, and why. Explain whether releasing/downloading this packet grants permission to build.”

Ask both people, without suggesting the answer: “What can you do next based on this result?” Record the exact words whenever the answer implies permission to proceed. Do not count a disclaimer as proof that it was understood. Record corrections and issues missed against the facilitator's source/packet checklist, including individual evidence stops even when the overall state says “checks the evidence supports.” Record whether either participant mistook sample data, unreviewed math, a saved agent response or a packet release for authority.

## Facilitator reference and completion

Before the test, independently inspect the selected packet and record expected issues in the notes: joins, dates, units, ownership, rule review, field gaps and output restrictions. This is an observation checklist, not an engineering approval. Compare each participant's observations with it after their timed task; record issues they missed. For each correction record the trigger, time spent and outcome. For any permission misread, stop use of that presentation, record a concrete wording/flow fix, and repeat the task after the fix with a real person.

Fill both sessions' attribution, actual-human attestations, timestamps, seconds, corrections, missed issues, permission misreads and notes. Run `python scripts/role_test.py check r29-capture.json`. This validates capture completeness only. The facilitator must inspect/sign the evidence and retain the attribution roster. Store consented results in `docs/role-tests/` for review; do not publish personal information without permission. R29 is pending until these two actual tasks and observations exist. Any nonzero permission misread fails the PRD success target and needs follow-up/retest; script success cannot waive it.
