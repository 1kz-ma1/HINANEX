# GIS wheel-speed and zoom continuity refinement — 2026-10-14

## User observation and scope
The current mouse wheel/touchpad zoom felt under-responsive even with the 1.5× baseline, and the background map still looked jerky. Update **GIS E presentation only**: responsiveness, tile continuity and independent local settings. Do not change source latitude/longitude, official flood raster meaning, zoom-to-recommendation logic, GSI/D provenance, RegionExport contracts or GIS risk classification.

## Behavior
- New default sensitivity is **3.75×**, 2.5 times the old 1.5× baseline, using Leaflet's wheel pixels per level `round(100 / sensitivity)` = **27px** instead of 67px. Existing `zoomSnap:0` remains continuous, and native pinch behavior is not overridden.
- Slider: 0.5–5.0 in 0.25 steps, initially 3.75; manual user changes apply without changing the map center, zoom or source visibility.
- `wheelDebounceTime:80` (formerly 40ms) groups fast wheel bursts into fewer Leaflet zoom transitions. Keep Leaflet animated zoom enabled and increase the animation threshold from 4 to 5. These are intended responsiveness/smoothness trade-offs, **not a proven frame-rate improvement**.
- Previously the official GSI basemap used `updateWhenZooming:false`, leaving an enlarged tile until zoom end. Now use `true`, throttled via `updateInterval:220` and `keepBuffer:4` so existing and intermediate tiles can be reused rather than swapping all at once. The heavier official flood overlay retains `updateWhenZooming:false` and `keepBuffer:3`; **never hide the hazard layer for animation**. It can still update at the end of a zoom.
- Preferences migrate from `hinanex.gis.gesture.v1` to `v2`: the exact old default of 1.5 maps to 3.75, while explicitly selected nondefault sensitivity and "steps" preferences remain unchanged. Version 2 writes occur on user changes, without location/GPS persistence. Fail closed to default on localStorage errors.
- Retain `?zoomFeel=previous` (100px/level, 0.5 zoom snap, 40ms debounce, deferred basemap updates) and `?zoomFeel=slow` (240px/level, 0.25 snap, 55ms debounce) as test-only A/B comparisons. On the new default branch, selecting settings explicitly overrides those temporary comparison values.

## Verification boundaries
- Required GitHub CI: deterministic E controller tests for default settings, slider, backward compatibility/migration, unchanged flood overlay, throttled base tiles, opt-in diagnostics and no source data changes.
- Existing independent Chromium smoke adds a real wheel zoom on the assembled GIS to catch missing wheel handlers and checks the tile policy. Required CI statically validates its syntax but does **not** execute Chromium or measure FPS.
- Before claiming **visually smooth**, perform interactive staging smoke on desktop mouse/touchpad and mobile Safari, ideally comparing the two query-mode URLs with browser performance tools. Measure frame timing, terrain tile network load and source layer latency; a passing CI or Render Live status alone does not prove perceptual smoothness.

## Follow-up: destination-first zoom (2026-10-14)

Visual feedback identified a flaw in the preceding progressive-refresh strategy: repeatedly rendering **transient zoom levels** can make a fast mouse-wheel gesture feel like a stack of steps even with fractional `zoomSnap:0`.

The updated default is **target-first** without replacing Leaflet's wheel handler:
- Keep pointer-anchored, continuous `zoomSnap:0` and default **3.75×** wheel sensitivity.
- Accumulate nearby wheel events inside Leaflet's native **135 ms wheel debounce** (was 80 ms). Leaflet then resolves a final gesture target in one map zoom call. This adds a small delay before an animation begins, deliberately trading a little latency for fewer repeated transitions.
- **`baseMap.updateWhenZooming:false`** means intermediate background tile levels are *not individually requested during the animation*; after reaching the destination, load the official destination raster tiles. The existing cached imagery may be temporarily scaled while traveling. This is not the same as Google Maps' private renderer, nor does it guarantee that target tiles arrive without network delay.
- The **official flood raster is unchanged**, visible throughout the gesture, and still refreshed on zoom end. No fake hazard overlay or hidden-risk interpretation is introduced.
- Preserve `?zoomFeel=progressive` with the prior 80 ms debounce + intermediate base-tile updates at **the same 3.75× sensitivity** for a controlled apples-to-apples visual comparison. Retain legacy `?zoomFeel=previous` and `?zoomFeel=slow` settings and existing local wheel controls. User settings continue to change only sensitivity/step style; no map/GPS state is saved.
- Existing map/popup/marker zoomend callbacks remain intact. D marker group reuse at integer zoom buckets is unchanged and source geometry is never interpolated.

**Verification scope:** required CI tests cover destination-only tile scheduling, wheel parameter bounds, per-mode comparison options and unchanged official flood raster configuration. The independently authored Playwright smoke checks options and mouse-wheel operation but is not executed by required CI. In-browser frame timing, input responsiveness and actual network tile requests remain to be checked against deployed staging; do not equate CI success with proven perceptual smoothness.

**Rollback:** `?zoomFeel=progressive` restores the previous raster-refresh strategy for comparison without a source/schema change; fully reverting default policy requires a new GIS PR.

## Follow-up: one animation per continuous wheel gesture (2026-10-14)

User feedback after #244: **raster imagery improved**, but the **camera's zoom itself still looked stepped**. The latest GIS E change tackles that second cause without changing source or tile semantics.

For default continuous mouse-wheel handling, a **capture-phase wheel listener** on the Leaflet map container coalesces a burst of input until 135 ms idle, then computes **one final fractional target** using Leaflet's bounded logistic wheel curve. The camera moves once through the public `map.setZoomAround(anchor, targetZoom, {animate:true})` API. It stays centered on the last wheel pointer, clamps to the map's actual dynamic min/max zoom, and caps gesture movement below four zoom levels so built-in Leaflet zoom animation can run. Intermediate wheel events no longer cause their own `setZoomAround` calls. Terrain GSI tiles and the official flood overlay retain #244's destination-first refresh policy; visible hazard data never disappears or changes meaning.

**Compatibility and fallback:** Ctrl/Meta + wheel (including browser/trackpad pinch gestures), Leaflet controls, popup interior scroll, and the user-selected 0.5-step zoom style bypass the custom handler and retain native event flow. A/B switch `?zoomFeel=native` restores the #244 native Leaflet wheel implementation with exactly the same 3.75× default, 135 ms debounce, and destination-only tiles. `?zoomFeel=progressive` still restores intermediary tiles for comparison. Saved gesture preferences, keyboard, +/- controls, touch pinch and map data/contracts do not change.

**Tradeoff:** a 135 ms end-of-burst pause is introduced before the single camera move; very long continuous wheel streams may wait until the user releases the wheel. This prioritizes a single smooth move over immediate frame-by-frame camera response and may not fit every input device. The change is **not Google Maps' proprietary animation engine**.

**Verification:** deterministic controller tests cover repeated wheel events yielding one map animation, pointer anchor, scroll direction, Ctrl+wheel bypass, source-popup scrolling, stepped-setting fallback, clamping at min/max, and old-mode comparisons. An independently authored Playwright smoke records the count of real Leaflet `setZoomAround` calls from multiple wheel events. Required GitHub CI parses that script but does not run Playwright. Desktop trackpad/mouse and Safari physical-device visual and latency acceptance remain essential before claiming measured smoothness; use `?zoomFeel=native` to compare identical raster policies.
