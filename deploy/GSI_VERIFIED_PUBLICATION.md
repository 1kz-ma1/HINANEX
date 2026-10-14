# Shared staging: independently verified GSI flood tiles

Issue #238. Render automatically builds D and C, but previously did not package accepted GSI flood GeoJSON references.

The new build-time flow in deploy/publish_gsi_staging.py uses an explicitly pinned, A/C previously documented GSI skhb01 z10 origin tile 10/909/403 as *partial area source* for the Edogawa SEARCH CONTEXT (not a claim that the tile's sites all belong to Edogawa).

1. Fetch the exact official HTTPS URL without redirect and with 16 MiB bound.
2. D normalizes all GeoJSON features (raw name, address, disaster1=1, coordinates, feature_index, raw SHA).
3. Independent C checker re-parses original raw bytes, checks every feature and exact row equality.
4. Separate C official HTTPS check fetches the exact URL AGAIN and requires byte equality. Neither a self-attested PASS nor a simulated MATCH can pass.
5. D requires accepted C source+HTTPS evidence and makes REFERENCE_ONLY JSON; C rechecks the complete C/D/E contract and z10 source cell.
6. Only after acceptance publish generated JSON at pipeline/data/output/gsi_verified_tiles/13123/10-909-403.json inside deploy/dist, with build-time SHA and UTC proof in _staging.json. No raw/data artifact is committed to Git.

Normal Render build runs the verification. Offline --skip-pipeline remains deterministic; --skip-gsi explicitly opts out. If GSI cannot be fetched or bytes differ, there is **no official GSI catalog** and _staging.json reports BLOCKED_UNVERIFIED_SOURCE; D/C staging and the browser's honest D-only fallback remain available.

This verifies source bytes at build time, NOT current opening, safe routing, disaster response, legal designation time, or membership of individual source features in Edogawa. The A nationwide GSI CSV from 2026-10-13 has 111 Edogawa emergency-place records with blank flood column; that is a DIFFERENT published source and does not alter the source tile or D UNKNOWN. Multiple tiles, live HTTP playback, and a 7-minute presenter rehearsal require separate verification and any further approved A/C reviewed coverage.

Run offline tests: python -m unittest deploy.tests.test_gsi_staging_publication -v. Never treat CI or a successful Render build as proof that an actual GSI tile was distributed: inspect /_staging.json and the exact JSON endpoint.
