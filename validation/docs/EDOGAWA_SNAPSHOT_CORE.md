# Edogawa original-source snapshot core (C)

Status: **UNREVIEWED evidence capture only**. Extracted unchanged from C draft PR #136 as the minimum auditable base for PR #139 decomposition. Tracking: issue #221.

## Scope / commands

```bash
python -m unittest discover -s validation/validation -p 'test_edogawa_official_snapshot_archive.py' -v
python validation/validation/archive_edogawa_official_sources.py --out-dir /outside-git/edogawa-originals-YYYYMMDD
python validation/validation/archive_edogawa_official_sources.py --verify-dir /outside-git/edogawa-originals-YYYYMMDD
```

- Capture exactly seven explicitly allowlisted HTTPS resources, each with raw response bytes, URL/provider metadata and SHA-256.
- Refuse non-HTTPS/untrusted publisher redirects, oversized/empty originals, changed/missing/replaced original bytes, unexpected extra files, forged approval and non-UTC timestamps.
- Preserve sources and manifest **outside Git**, in a new empty directory; do not upload or deploy raw data.
- Offline unit tests use synthetic responses. Actual source availability and content shape require a separate network-enabled CI runner and independent review.

## Output / semantic invariants

`snapshot_manifest.json` is internal archive metadata, **not a public or D RegionExport contract**. It explicitly reports `human_c_reviewer_signed_off=false` and `flood_scenario_classifications_added=0`. Byte/manifest consistency alone **does not prove the current publisher's authenticity or historical source-version identity**, nor physical shelter site equivalence, official hazard meaning, current opening or safety. All such judgments remain `UNKNOWN` / `UNVERIFIED` and no human approvals are granted.

## Follow-ups

- #139: one isolated hosted capture and independent content preflight after verifying dependencies; avoid bundling 10 unrelated jobs.
- #136: move remaining C source-content checks, GSI/site identity analyses and history/review scripts in small coherent slices.
- #164: educational UI is on hold, not dependent on promotion of shelter facts.
