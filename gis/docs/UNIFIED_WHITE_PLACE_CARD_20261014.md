# GIS unified white place card — 2026-10-14

The user's accepted staging screenshot has a compact white GSI popup beside a much larger dark bottom palette. All normal selected-place facts now appear in **one consistent light card**, not a second large bottom drawer.

## Implementation
- E-only CSS converts the already-present id=details overlay to a white floating card at top/right, with a discrete close button. On wide screens while the 50s GSI presenter runs the card sits to the **left** of the demonstration panel, as in the screenshot. Narrow layouts bound card size/scroll and do not obstruct a small-screen demonstration panel.
- Existing E detail() keeps all actual D/GSI/raster values and trust-gated external source URLs. It divides up to 4 primary fields (type, address, flood status, etc.) from the remaining technical rows in native <details><summary>詳しい情報を見る</summary>. Long provenance disclaimers are separate <details><summary>注意事項と確認範囲</summary>. A short caution remains visible for facility and verified official-reference records.
- Suppress the automatic GSI Leaflet popup on selection; it previously appeared simultaneously with the bottom detail sheet. The existing popup binding remains for compatibility but the application card is the primary inspection surface. All marker coordinates and the C/D/GSI distinctions remain unchanged.
- User-visible phrases like D施設, 地域D, D RegionExport and D UNKNOWN are rewritten in GIS normal and presenter prose to 地域の避難施設, 施設情報, 元データ等. Internal contract identifiers, source enums, C audit, GeoJSON raw feature trace and schema fields **are unchanged**.
- Detail links retain the original safe http/https guard, escaped text and external rel=noopener noreferrer; raw feature indexes remain inspectable only in detailed accordion, not mistaken for business/official row numbers.
- Existing top toolbar map controls, GIS evidence view, manual panning, 50s GSI and 52s D source demonstrations still use their original IDs and data API.
- If the official data is missing, the map continues to fail closed and explicitly offers the independent D-only tour.

## Follow-up QA (2026-10-14)
- Keep raw `UNKNOWN` in source data/technical trace, but show `未判定` rather than internal enums in the primary facility summary; explicitly warn that missing judgment does not mean danger.
- Make D-presenter copy natural; remove remaining engineering-only badges and English display headings.
- Small-screen presenter mode keeps a capped, scrollable place card above the bottom-anchored demo sheet instead of making the selected place inaccessible.
- Update the map asset regression to the new UI-only cache key; the discovery module's compatibility signature is unchanged.

## Acceptance
Required GIS browser-controller test checks compact vs expanded HTML, sanitized provenance and URL, no technical trace in default view, both D and GSI clicks, close button, responsive light card styling and no normal-screen internal term leakage. Manual Render Edge/mobile screenshot acceptance remains necessary; no user-uploaded photo was modified.
