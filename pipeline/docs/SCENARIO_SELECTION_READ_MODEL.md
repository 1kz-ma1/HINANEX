# Issue #301 / Flood Scenario selection: D-only read model (Draft)

## Scope

A pure, offline selection helper in src/hinanex/scenario_selection.py. It **does not** interpret the municipal raw marks, join otherwise unrelated sources, fetch new records, change the RegionExport or ScenarioResult contract, classify safety, authorize locations for GIS, or publish live hazard information.

Inputs: an existing ScenarioResult and shelter_location NormalizedDataset, a selected region and flood hazard, exact scenario **evaluation** timestamp, a per-facility map of expected official source URLs obtained **independently of** the scenario's facts, and optional status filters.

The function fails closed when region/hazard/scenario or location IDs disagree, there are duplicate or missing IDs, the source URL pins differ, a source URL is unsafe, counts disagree, the evaluation timestamp is stale, coordinates conflict, or a non-UNKNOWN status lacks a direct same-source flood fact. UNKNOWN values from mixed or unverified hazard sources remain UNKNOWN and are never silently promoted or excluded. In this first narrow implementation, decisive statuses must be supported by exact 災害種別_洪水 source scope; supporting additional official flood scopes requires separately accepted semantics.

Output: stable ID-sorted rows carrying **only the existing** CANDIDATE / EXCLUDED / UNKNOWN statuses, reasons, raw value, source references, and a coordinate-*presence* flag (no coordinates). Full-set counts remain available even when the display filter hides some rows; HAS_ROWS, NO_MATCH, and NO_DATA distinguish a filtered-out set from an empty input.

## Safety boundaries and blockers

- The caller-supplied source URL pins are a snapshot consistency check, **not** proof of source authenticity, version, human review, or C acceptance. The caller must not produce pins by copying the scenario's untrusted fact URLs.
- evaluated_at only identifies the computation snapshot; it is **not** an official publication/update time and does not establish source freshness. Such evidence and approvals must be verified externally before real-data acceptance.
- Neither the status names nor the presence of coordinates establishes physical position approval, safety, opening status, route passability, or evacuation suitability.
- This D-only helper does not become a B/E API automatically. B/E consumer adoption and any shared contract extensions require separate design review / PR, preserving AGENTS.md scope guard.
- Name/identity cross-source matching is out of scope. Exact IDs are checked only against the already normalized location dataset; human/source acceptance remains a separate gate.

## Verification

cd pipeline && python -m unittest tests/test_scenario_selection.py -v

Synthetic fixtures cover status preservation and order invariance, filtering, empty-vs-no-match, combined scope UNKNOWN, source pin errors, wrong hazard/region/instant, bad IDs/joins, mismatched counts, invalid coordinates, and malformed status filters. CI full pipeline tests and verify_d_mvp.py are separate required checks; the tests do not exercise official data, live APIs, a physical device, or human source review.

Next PR: reuse the existing GIS two-site comparison and B flood display adapters with a separately reviewed consumer-facing data feed, keeping this helper internal until the evidence/contract boundary is approved. No new UI or route features are included here.
