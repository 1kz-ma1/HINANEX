# C — Historical Replay as-of Input Gate v0.1 (Proposal / Not Safety Approved)

**Status (2026-10-13):** Code + synthetic regression tests proposed. Real historical C-approved source versions: **0**. Validated real MATCH/MISMATCH cases: **0**.

Related: [Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142), [C design PR #143](https://github.com/1kz-ma1/HINANEX/pull/143), [A source feasibility PR #144](https://github.com/1kz-ma1/HINANEX/pull/144), [C raw audit PR #147](https://github.com/1kz-ma1/HINANEX/pull/147).

## Purpose

The previously implemented original-byte archive + C audit proves that the **currently served** Tokyo press releases have traceable source bytes and the extracted 48 / 73 / 98 facility counts. Those numbers **do not** mean that the same web page bytes existed at 2019-10-12 12:00 / 15:00 / 13th 00:00. Even the press release's printed 2019 publication timestamp is not itself proof of the current HTML revision's historical state.

This new *preflight* refuses to make a time-frozen INPUT set if an independent C review is missing or if INPUT is derived from post-event TRUTH. A pass means only the **given** manifests satisfy structural consistency rules; authenticity of C review records still requires independent human verification. No historical replay or model is implemented.

## Separate schemas

The `--case` JSON uses `hinanex.historical_replay_case.v0.1`, with `case_id`, `as_of_jst` (ISO 8601 with explicit JST +09:00), and `sources[]`: `source_id`, `role` = `INPUT` / `TRUTH` / `CONTEXT`, `published_at_jst`, `archive_sha256` (original bytes only), optional `depends_on[]` (source IDs) and `post_event_report`. Observation time and publication time must be **distinct**; observation time must never be used as publication evidence.

The *separate independent-review* JSON uses `hinanex.c.historical_input_reviews.v0.1` with `case_id`, `approved_input_sources[]`: `source_id`, `review_state=C_APPROVED`, `original_sha256`, `historical_version_verified=true`, `verified_public_at_jst`, `approval_ref`. This ledger is a cross-check against the input archive hash. It is **not a digital signature or a substitute for C human review**; forged approval data alone must not be accepted as a valid real-world proof of publication.

**No runtime Contract/RegionExport changes.** This is C-only internal input validation, not a shared API for D/B/E until reviewed separately.

## Hard rules

1. Reject missing C approval, missing/mismatched SHA256, no exact publication timestamp, future publication, an unverified or late independent public-availability timestamp, or `post_event_report=true`.
2. Reject input with any TRUTH lineage, non-input dependency, missing/cyclic dependency, or any non-prechecked upstream source. Nothing downstream can launder an unapproved parent.
3. Do not treat *date only* (e.g. “2019-10-11”) as midnight, a modern `Last-Modified` as 2019 proof, or an archived retrospective timeline as event-time INPUT. Such candidates use `published_at_jst=null` until time evidence is approved, and will remain `BLOCKED`.
4. Keep TRUTH separated from INPUT in the report and exclude from `safe_input_source_ids`. An `INPUT` source that includes post-event observation derived from TRUTH fails; not merely hidden in B/E.
5. Report `PRECHECK_PASSED__HUMAN_REVIEW_REQUIRED` only for structurally valid manifests with independent recorded approvals. This is **not** final authorization to replay; C still must authenticate approvals and source bytes before a real test. Rejection outputs `BLOCKED` and reasons; CLI exit 2; malformed/tampered input exit 1.
6. Historical suitability, safety, opening forecasts, matching to contemporary Edogawa `shelter_location`, and the full T1/T2 performance metrics remain out of scope.

## First real candidate sources and current evidence

- **JMA 2019-10-09, 10 and 11 announcements**:
  - https://www.jma.go.jp/jma/press/1910/09a/201910091400.html
  - https://www.jma.go.jp/jma/press/1910/10c/201910101400.html
  - https://www.jma.go.jp/jma/press/1910/11b/201910111100.html
  These are original-day, public-facing forecasts of Typhoon 19, with pages currently still available. They identify 2019 *reporting dates*; the exact first-publication instant of each stored page revision is **not independently validated**. The URLs' numbers are not accepted as precise timestamps.
- **Tokyo 2019-10-12 reports**: 16:00 #23 (12:00 observed 48) and 21:00 #36 (15:00 observed 73), then 2019-10-13 02:00 #49 (00:00 observed 98). A/C rechecked original bytes, but the current web HTML's historical version is not approved. **The number 48 was not published at 12:00 merely because that is its observation time.**
- **Edogawa 2019-05 flood hazard map**: https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/n_hazardmap.html — listed as issued May 2019, but modern published page may include later corrections; the historical 2019 exact PDF version and usable location records require A archival review.
- **2019-10-12 09:45 evacuation recommendation and 13:40 school shelter opening completion** are described in a **post-event** Edogawa school-operations document (https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf). This evidence is retrospective TRUTH/context, not timestamp-approved live inputs.
- **Modern 2026 lists/GSI features** are not 2019-as-of facility masters. Exact facility IDs and event-time open/closed states are not confirmed.

## Validation

Use synthetic fixture tests (no internet):
```bash
python -m unittest discover -s validation/validation -p 'test_historical_replay_asof_gate.py' -v
```

Run manually only with independent reviewed manifests:
```bash
python validation/validation/historical_replay_asof_gate.py --case /secure/case.json \
    --c-reviews /secure/C_review.json --out /secure/C_preflight_report.json
```
Output remains `BLOCKED` until archival/temporal/lineage acceptance is complete. C must additionally confirm cryptographic authenticity of the trusted ledger and independently evaluate the raw original/source timestamps. A provisional green state cannot be presented as prediction accuracy.

## Next gates

A: locate and version-pin exact 2019 JMA/daytime bulletins, pre-event facility/hazard/map materials, and authority/availability chain. Record publication time/precision; when only a date is known, stay UNKNOWN.

C: cross-check captured originals, timing evidence and C approval chain; run this preflight with **real, approved** input and independently partition truth.

D: only after C approval, build a frozen-as-of provider **without injecting operational opening truth**. B/E: only display verified T0, honest UNKNOWN, and provenance until T1 validated. All changes require separate owner PR and Merge Captain review.

**Non-goal:** This PR does not expand real-world shelter decisions or certify the current MVP for disaster-time use.
