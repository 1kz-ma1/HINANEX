# Edogawa source-content preflight and independent review (C)

Status: **UNREVIEWED**. Extracted unchanged from original #136, decision tracked in #221. Depends on C snapshot core #222; does not change D, RegionExport or accepted shelter status.

## Gates / order

1. Capture official raw HTTP originals in a fresh outside-Git directory:
   `archive_edogawa_official_sources.py --out-dir /outside-git/edogawa-originals`.
2. Recheck the raw original-byte SHA256 and Manifest with `--verify-dir`.
3. Inspect **content shape**, CSV header/coordinates and official water table/source landmarks:
   `validate_edogawa_official_archive.py --archive-dir /outside-git/edogawa-originals --report /outside-git/preflight.json`.
4. When A candidate ledger, D RegionExport and original bytes are available **from the same audited version**, run `verify_edogawa_water_join.py` for C-independent source-to-output consistency. It must **not** convert any naming/coordinate hint to an accepted physical-site match.

Offline negative test commands:

```bash
python -m unittest discover -s validation/validation -p 'test_edogawa_water_join.py' -v
python -m unittest discover -s validation/validation -p 'test_edogawa_official_archive_content.py' -v
```

## Semantics

200 OK is not proof the requested original source was served. Both the snapshot and content-shape gates are technical checks **only**, not proof of official historical release date, authenticity of an archived revision, physical facility identity, hazard scope, safety or current opening. Source URLs/byte hashes and A/C/D source roles must remain separate. Unapproved pairs = 0; all relevant D hazard statuses remain UNKNOWN/UNVERIFIED. Save review outputs and raw bytes outside Git. Do not infer flood-only legal meanings or cross-source joins.
