# MJ-01 固定合成ジャーニーUI v0.1
2026-11-24 / FIXED_SYNTHETIC_FIXTURE_ONLY / SOURCE MERGE HOLD
Owner decision: https://github.com/1kz-ma1/HINANEX/issues/362#issuecomment-7120366611
Base: f13ab2035c51cde0084d1463036f3148ff1b8ecc

## Scope / pre-implementation specification
New independent prototype. J02–J05 in one document; explicit start. No B1 link, S0/S1 provider, official data, GPS, persistence, external network, ranking, safety claim or route. No shared contract. All output is manually authored display fixture, NOT S1 output. B2 model.js is imported unmodified: createB2Session, isB2Loopback, rows, toggle, selected, choose, choice, clear. No reuse of B2 page DOM; new step-specific shell only. Comparison/choice state has one authority: the current B2 session; no S1 identity mapping. B2 IDs here use a separate mj01 namespace. Fixed scenarios pet/step have explicitly authored per-row status/reason/source/unknowns; no condition evaluation, no arbitrary records. CANDIDATE/EXCLUDED/UNKNOWN are display-only fixture labels, never real safety/eligibility.

## State transitions
IDLE -> explicit START -> J02 (no condition selected) -> explicit condition + SHOW -> J03 -> CONTINUE -> J04 -> exactly two selected -> J05. J05 is complete only after explicit choice of one compared ID. UNKNOWN and EXCLUDED remain unchanged when chosen. Back to J04 clears comparison/choice (new session for same fixed condition). Change condition from J03/J04/J05 discards session and condition, returns J02. Simulated LOAD_ERROR from active steps discards session/condition; restart requires explicit START. END discards all -> IDLE. pagehide, hidden document and BFCache return reset to IDLE; no restored choice. Each render rebuilds dynamic DOM, callbacks capture revision and are rejected after render/transition. No async provider or expiry guarantee is implied. Reference route unavailable; no link. Strict HTTP allowlisted loopback only; default closed HTML, no query inputs. Static modules loaded locally; no fetch/storage writes. CSP blocks connect/frame/form/remote assets. Browser guard is secondary, not deployment guard.

## UI/accessibility
Fixed training notice, no live claim. Native buttons, named controls, aria-pressed for compared items, aria-current step, status announcement, heading focus on transition and focus restoration for same-step comparison. Responsive stacked/grid layout, 320/390/1440 CSS px. Text only for evidence. No external resources.

## Planned files / non-public inventory (L-PRIV)
All under `frontend/prototypes/f05-flood-journey/mj01-shell/`:
- README.md (this specification)
- fixtures.js (static display scenarios)
- model.js (step state / B2 reuse)
- index.html (closed-by-default shell)
- app.js (DOM presentation)
- model.test.js (Node)
- browser-http.test.cjs (actual HTTP Chrome)
Existing sibling b2-compare/model.js is a read-only dependency; remains private. No files outside this directory changed. Independent Shared exclusion proof of every file and future nested files required before merge, even though F05 parent already listed. Guard proof not supplied by UI test. #371 remains blocked; no dependency on #371 or #386 for fixed mock code.

## Verification plan
From frontend: node --test prototypes/f05-flood-journey/mj01-shell/model.test.js prototypes/f05-flood-journey/mj01-shell/browser-http.test.cjs; npm test; npm run lint; npm run build. CI Chrome absence FAIL. Test native Tab/Enter, 320/390/1440, two max, UNKNOWN, clear on change/error/end, old revision, nonallowlisted host, network/storage. Required exact HEAD test separate. Physical device/Safari/AT, formal connections, official evidence and LIVE deployment NOT_RUN; #372 separate. Draft / merge blocked / publication NO-GO.
