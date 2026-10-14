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
