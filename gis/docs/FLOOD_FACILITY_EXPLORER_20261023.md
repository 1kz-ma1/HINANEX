# HINANEX #301 — GIS facility exploration / comparison (Draft specification)

**Status:** E-only proposal, synthetic validation. Main/Render, real-data safety acceptance and route guidance remain out of scope.

## UX decision (2026-10-23)
- Browse all returned facility records in bounded pages of 20; query by name/address and filter by D's existing CANDIDATE / EXCLUDED / UNKNOWN classification.
- Detailed comparison is **two facilities only**. The viewer can choose one of those two as a personal **follow-up / information-check target**, not an officially recommended or safe evacuation destination.
- Reuse the existing Edogawa comparison *card styling*. Preserve the original presenter-driven A/B map-popup demo and GSI source-specific comparison, which remain separate.
- No map pins are added by this flow, even if the D location row has coordinates. Coordinates and Source URL equality are NOT position approval. Unknown coordinates remain browseable in text.
- Full totals and UNKNOWN counts are not reduced when a query/filter hides rows. No-data / no-match / no-scenario / no-dataset / corrupt input must have different explanations.
- Clear query/selection and personal choice when region, input snapshot, filter, or query changes. The choice is temporary browser state; no persistent write.
- Official source time freshness is not established by these display adapters. Display this limitation rather than using `normalized_at` or `evaluated_at` as an official publication timestamp.

## Existing code reuse / contracts
- Producer: `pipeline/src/hinanex/flood_scenario.py` -> existing `RegionExport.scenarios[]`.
- Consumer: `gis/gis/js/d_region_adapter.js` already makes an exact-ID `floodScenario.byId` Map. E does not reinterpret source marks, and does not add fields to RegionExport.
- `gis/gis/js/facility_explore.js` provides an in-browser, read-only selection state. `gis/gis/js/facility_explore_ui.js` implements presentation.
- D Draft #302 is an **independent pre-export integrity helper**. Its source URL pin / timestamp consistency boundary is NOT available as a public consumer API and must not be claimed as checked by this E UI. A/C and formal shared contract review are required before treating any real flood designation or physical location as independently accepted.
- GSI verified reference sites are a **different source family** and must not be joined to these D facility records by name, proximity, or data order.

## Safety / test gates
- UNKNOWN is never promoted, silently dropped, or interpreted as unsafe/safe.
- A CANDIDATE/EXCLUDED source status is displayed as a D classification only; it does not signify safety, opening, accessibility, or a route.
- D raw ○/× and combined `洪水・内水` never become independent decisions at the GIS consumer.
- Fail closed on invalid/mismatched IDs, source URLs, non-UNKNOWN rows without directly joined flood facts, invalid statuses.
- Node fixture regression is required in the existing GIS CI runner through `facility_list.test.js`. No official data or geographic browser coordinates are invented.
- Required before merge: all CI checks green against latest base, desktop/mobile actual-browser acceptance, source/identity acceptance as applicable, Merge Captain decision. Draft may stack on #300.

## Follow-up
1. Review source provenance and exact dataset pinning with D/C; decide whether to promote the internal #302 helper via independently reviewed output or only run it upstream.
2. Run physical/mobile browser tests for text panel and compare actions.
3. After human approval of actual source semantics and position, consider context-aware reference route as a distinct phase with consent/terms/fallback review. No implicit automatic recommendation.

## Automated real-browser acceptance

The existing E Chromium wheel job now also invokes `gis/tests/facility_explore_browser.js` before zoom gestures. It exercises actual generated D RegionExport records in desktop (Edogawa) and 390px mobile (Nagoya) contexts: list, pair comparison, personal choice, filter-reset, empty search, DOM text rendering, viewport bounds, and absence of any new map pin logic. Reports and screenshots are browser-only CI evidence, **not** official municipality meaning approval or a physical Safari test.
