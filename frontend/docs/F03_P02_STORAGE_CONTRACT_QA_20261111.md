# F03/P-02 Issue #356 — 端末保存契約差分と実HTTP Chrome検証

Status: **independent B draft QA / not production approved / not connected to GIS**. Updated 2026-11-11 (JST).

## Sources (actual references, do not substitute inferred code)

1. Root `AGENTS.md`, `frontend/AGENTS.md` on main.
2. Owner-supplied original `HINANEX_F03_事前準備UI_レビュー修正版_20261104.zip`, SHA-256 checked, 13 entries, decompressed with `ZipFile.testzip()==None`. Its original `index.html`, `styles.css` and `app.js` were inspected and used as the starting point of `frontend/prototypes/f03-storage-contract-qa`. The ZIP's previous simulated result **13/13 PASS** does not establish HTTP persistence.
3. [Draft #346 F03 proposal](https://github.com/1kz-ma1/HINANEX/blob/docs/feature-specs-20261030/docs/strategy/features/03_PRE_EVENT_PREPARATION.md), not accepted product contract.
4. [E Draft PR #311](https://github.com/1kz-ma1/HINANEX/pull/311), `gis/gis/js/pre_event_preparation.js` and `gis/tests/pre_event_preparation.test.js`, E scope, unmerged.
5. [Issue #356](https://github.com/1kz-ma1/HINANEX/issues/356).

## Storage contract diff — do **not** interoperate or migrate without decision

| Axis | Owner-reviewed F03 P-01 ZIP (as actually inspected) | E Draft PR #311 (as actually inspected) | Current B P-02 QA choice |
| --- | --- | --- | --- |
| Status | Local standalone demo, not connected | E module-only Draft, no user-facing UI | B standalone Draft QA, not connected |
| Storage key | `hinanex.preparedness.demo.v1` | `hinanex.gis.pre_event.optin.v1` | Retain demo key only |
| Schema | `{ "selected_region": "13123", "schema_version": 1 }` | `{ schemaVersion: 1, consentSaved: true, savedAt: ISO8601, profile: { regionCode, occupiedFloor, upperFloorAccess } }` | Retain demo schema; reject extras |
| Fields | One allowlisted region code (`13123`/`15100`/`23100`) | Arbitrary five-digit region code, nullable floor 1–200, nullable upper-floor access Boolean | One field, synthetic limited set, **no adoption of E fields** |
| Age and expiry | None, no `savedAt` | More than 180 days triggers `STALE_SAVED_DATA` (not automatic deletion); future timestamp guard | No auto expiry; 180-day tests are **N/A for B demo**, keep E tests separate |
| Consent | Explicit click to save; **original ZIP automatically reads on page load** | Explicit `read()` and `save(...,{consentGiven:true})`; constructor has no storage side effects; caller UI must prove human consent | Explicit read *and* explicit save; no startup read/write |
| Update failure | Preserve prior displayed saved region on setItem exception | `save()` returns `STORAGE_UNAVAILABLE`; caller UI absent | Preserve prior region; check read-back before success |
| Delete | `removeItem` then `getItem` confirmation and success text only if absent | `deleteSaved()` verifies `getItem()===null` and returns `DELETE_UNCONFIRMED` otherwise | Retain confirmation and feedback |
| Privacy | Client-side cleartext localStorage, normal shared origin (original note underspecified same-origin JS) | Cleartext same-origin JS, consent UI absent | Explicit UI statement; no claim of encrypted or legal consent |
| Integration | F01/F02/GIS not connected | GIS not connected | **No integration or key migration** |

### Confirmed discrepancy and proposed owner decision

The supplied ZIP executes `readSavedRegion()` immediately on startup, including a probe `setItem()`/`removeItem()` before `getItem()`. This contradicts Issue #356's stricter *no implicit read/write before a user's action* requirement. The B isolated QA branch corrects it for experimentation by adding an explicit read button. It is **not** an unreviewed change to the owner's original ZIP or E module. Owner to decide if that revised UX replaces the earlier immediate-restore expectation.

Separate concern: `setItem` success does not always prove persistence, so B verifies read-back. The E module's `save` currently returns success after a nonthrowing `setItem`, without a readback; **do not edit E from B**. Potential E follow-up needs a separately owned review.

## Tests: PASS / FAIL / NOT_RUN must be separated

- Static node: `cd frontend && node --test tests/f03-storage-contract.test.js` (checks scope, controls and safety disclosures).
- Real HTTP Chrome: `cd frontend && node --test tests/f03-storage-http-chrome.test.js` (no mocked storage; headless Chrome, localhost HTTP, real user-data-dir and browser restart). Included in required `npm test` CI.
- PASS/FAIL of individual browser cases and exact-head required CI will be added to PR body after execution. Do not interpret Node syntax-only or the ZIP's in-memory mocked tests as HTTP PASS.
- Local sandbox may enforce `ERR_BLOCKED_BY_ADMINISTRATOR` on loopback Chrome; this is a **BLOCKED** local environment, not a product failure.
- NOT_RUN: physical Android/iOS Safari, real Render, external official-site delivery, 180-day behavior inside B demo (not part of schema), legal/privacy and screen reader acceptance. E #311 already has synthetic Node 180-day test; its real HTTP Chrome is separate/not connected to this UI.

## Security and disaster safety

- State only region code; no GPS, street address, name, health, family, household/contacts, precise coordinates, room/floor attributes.
- No fetch/XHR/beacon/analytics/background sync; region code never put into URLs. Normal user click to a **separate official site** is an external navigation and requires internet.
- Every same-origin script can access the cleartext browser storage; users must consider shared devices. No guaranteed backup/transfer. Browser site-data clearing can delete stored settings.
- Demo's three municipal labels are sample selections, not evidence of current warnings, shelter opening or safe routes. No physical evacuation guidance, no RegionExport/GIS connection.

## Outstanding decisions for owner/Merge Captain

1. Explicit **opt-in read** UX vs original demo's automatic restore; choose only after human review.
2. Do not adopt E #311's key/schema/180-day policy or infer a migration without formal contract decision, privacy review and B/E coordination.
3. E module `save` readback guarantee, old value persistence, and failure mapping deserve separate E-side review.
4. Review real browser CI metrics, then separate physical-device/privacy acceptance before any public use.

**PR creation ≠ integration approval.** This branch modifies only `frontend/**`; no main merge or GIS connection.
