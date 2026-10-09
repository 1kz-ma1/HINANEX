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
