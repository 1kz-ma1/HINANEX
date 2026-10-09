# B Consumer — Flood Scenario Contract Guard (2026-10-09)

## Current implementation and scope

- Main already renders D's optional `RegionExport.scenarios[]` as a read-only raw evidence panel.
- Legacy exports omitting `scenarios` do not display this panel.
- This increment strengthens only `frontend/**` validation; no D evaluation, contract schema, official data, GIS or deployment packaging is changed.
- Issue #48 remains open: current Niigata municipality marker-to-ODS-column semantics are **unconfirmed**; never infer safety, facility opening or eligibility from `○/×/－/usable_floor_raw`.

## Guard and display contract

- Malformed `scenarios`, duplicate `flood_shelter_selection` scenarios, invalid scenario statuses, conflicting region codes, or malformed `facility_results` must show an explicit **unsupported Contract** notice. No partially accepted facility rows should appear.
- Facility IDs must be non-empty, unique within the Scenario, and match `fact.facility_id` exactly. No fuzzy joining.
- Facility status is strictly `CANDIDATE | EXCLUDED | UNKNOWN`; its value is copied from D and **never re-evaluated** by B.
- Join status is `DIRECT_SAME_SOURCE | UNVERIFIED`. Coordinates may be absent; non-finite or stringified coordinates are rejected, never inferred.
- Raw official text remains text, HTTPS sources remain the only clickable links, `UNKNOWN` remains neither safe nor unsafe.
- Good Scenario payloads preserve the current panel's data fields, paging, and display. No unrelated UI redesign in this increment.

## Follow-up from old PR #83

This is a **partial** migration from stale #83, not a replacement for its broader UX proposal. After this guard reaches main, separately rebase/redesign loading, empty-state, coverage labels, source panel, accessibility and responsive presentation on a short-lived main-based branch. Avoid overwriting current #106/#108 frontend/deploy integration.

## UI presentation increment (2026-10-09, follow-up to #110)

**Required UI states and non-claims**
- Region auto-load, manual file read, and demo load render a visible `loading` notice in the Scenario panel without retaining the previous municipality's records. The parent region summary remains the primary fetch status.
- Fetch/file errors render `error` in the Scenario panel with a safe retry path; malformed optional Contract remains `unsupported` and displays no facility rows. A legacy RegionExport with no `scenarios[]` continues to hide this optional panel.
- A valid Scenario with `facility_results=[]` displays the D status and caveat, and a separate zero-row message. No pagination for zero rows. **Zero exported results does not mean no shelters or no safe/unsafe shelters exist.**
- D Scenario `FULL` means coverage of evaluation, not that all shelters are eligible. D discovery `AVAILABLE` means raw-source acquisition, not evaluation readiness or facility opening. Label mapping changes display copy only and never edits D statuses or their counts.
- The safety/non-opening caveat remains visible. Per-facility reason and D status remain visible while raw markers, trace and source URL live inside a keyboard-operable native `details` disclosure.
- Mobile 620px or narrower uses vertically stacked evidence fields, flexible paging buttons and visible focus styling.

**Verification**
- Frontend unit tests for the view model and static UI semantics, plus whole-repo CI, must pass before merge.
- Real mobile Safari/Edge visual checks and human acceptance of wording are separate manual checks; automated tests do not certify emergency suitability.

**Remaining after this increment**
- Do not wholesale merge stale #83. Review only independently useful accessible UI enhancements against current main, and close old PR only after verifying scope coverage.
