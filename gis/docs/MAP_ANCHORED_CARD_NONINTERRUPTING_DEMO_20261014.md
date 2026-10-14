# Map-anchored information bubbles and uninterrupted GIS demos — 2026-10-14

## Desired user interactions
- Clicking one of the original D shelter-location markers or a C-accepted GSI reference marker opens **one white Leaflet popup attached to that exact source location**, not a fixed viewport-side card.
- Clicking another marker replaces the previous bubble. Clicking an empty map area closes the bubble without automatically replacing it with the flood-raster detail card.
- Leaflet itself owns popup positioning/repositioning while panning and zooming, including native keyboard-close and its popup tip. Long advanced provenance is collapsible and scrollable inside the popup. The prior `#details` markup is a hidden, compatible template; there is no visible duplicate card.
- A selected manual-origin point uses its explicitly selected latitude/longitude. A visual cluster may display a labeled aggregate bubble at its on-screen centroid, **not** a fabricated site or recommendation. Boundary click, if a fixture is present, anchors to the actual user click. Source identity and raw/unknown status are not changed.
- During the 50-second GSI demonstration, the 52-second D attribute demonstration, and the 3-region guided tour, ordinary manual pan/zoom and inspection do **not** pause the presentation clock or call `halt()`. User-triggered stop, pause, next, restart and closing retain their explicit meanings. After manual camera interaction the close/stop handler refrains from restoring the old camera; automatic scene changes may still focus original source points.
- A click on the visible presenter control is not treated as an empty map click. The right-pane compatibility DOM is never displayed during normal GIS use.

## Safety and scope
Only E-owned `gis/**` changes. No coordinate interpolation, geocoding, RegionExport/schema edits, source qualification change, hazard suitability classification, or actual shelter recommendation. Source URLs continue to pass the existing safeExternalUrl guard and escapeHtml. An UNKNOWN classification is not danger or inability to use the site.

## Validation
- Deterministic tests must cover GSI and D selected marker bubble placement, replacement, blank-map dismissal, script cache signatures and continued demo ticking after gestures.
- The existing Chromium predeploy test is updated to exercise the actual Leaflet popup and bounded scroll at mobile/tablet widths. The GitHub required `test` workflow runs the JS/controller tests and syntax checks; it does **not** run the Playwright smoke end-to-end.
- Production/staging visual screenshot acceptance requires the new PR to be integrated and deployed. No other-team repository paths need changes.

## Compact zoom-sensitive bubble revision (2026-10-14)

After visual review of the live 江戸川区 boundary fixture, its popup was disproportionately large relative to the map. The presentation now **scales the *bubble*, not the disaster data**, using three inclusive, clamped screen-space sizes at map zooms below 11, 11–13 and 14+. Default non-boundary widths: 188 / 216 / 260 CSS px; boundary fixture widths: 174 / 194 / 215 px. Height is capped independently and native scrolling preserves access to long technical records. Breakpoints/widths are CSS presentation values, **not** map scale, ground distance, accuracy, classification or site geometry. Text remains legible; there is no unbounded CSS transform.

The visible summary contains at most two prioritized fields. The non-facility **自治体境界（参考）** fixture shows only its name and status label initially, while source fields and the "表示確認用" caveat remain behind one native details expander. Facility and GSI cards retain the **visible** unverified safety/opening caution. The two previous expanders have been merged into one ("詳しい情報を見る"), retaining source trace, warnings, and raw values without inventing or discarding evidence.

Leaflet remeasures a still-open bubble on `zoomend` rather than closing or reopening it, so the selected map attachment and disclosure state persist. The background/other-pin dismissal rules and independent demo timers remain unchanged. Controller tests verify zoom threshold mapping, attached popup reuse, CSS bounds and cache keys. The existing full Chromium smoke was updated to exercise responsive zoom bounds and the compact boundary fixture but is **not** run by required Node CI.
