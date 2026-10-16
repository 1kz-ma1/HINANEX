# Final-presentation Phase 1: Edogawa original-source recapture and C delta review

Status: **tooling under review, no new official sources captured by this PR**, no C human approval, no D or GIS source/status changes. Related: #89, #221, #264 (A), #265 (C), #266 (D).

## Ground truth / reusing existing work

- `#222`: C seven-official-source raw-byte capture and fail-closed manifest integrity.
- `#224`: independent 200-OK wrong-content/CSV/header/old-vs-new school source preflight.
- `#223/#225`: isolated GitHub-hosted source capture and content preflight, artifacts kept private 7 days, no permanent official raw in Git.
- Latest `main` CI success only verifies code/test state; do **not** call a new source recapture successful until a new network capture run is linked and its artifact reviewed.
- Existing draft #136/#139 remain blocked/archival. Do not merge those large bundles for this slice.

## Operator sequence (no raw data is committed)

1. Obtain two actual **different-time** original archives using the existing C HTTPS capture command, or by downloading the private time-limited artifacts from two documented `edogawa-source-snapshot-minimal.yml` runs into separate fresh directories outside Git. Confirm their capture times and provenance; do not silently relabel old artifacts as new.
2. Verify each archive with its unmodified `archive_edogawa_official_sources.py --verify-dir` and content preflight `validate_edogawa_official_archive.py`. A changed publisher page may invalidate content-shape assumptions: this is a review **blocker**, not evidence for inferring new meanings.
3. Run the C comparison:

```bash
python validation/validation/compare_edogawa_source_snapshots.py \
  --before /outside-git/edogawa-older \
  --after /outside-git/edogawa-newer \
  --report /outside-git/edogawa-source-delta-UNREVIEWED.json

python -m unittest discover -s validation/validation \
  -p 'test_compare_edogawa_source_snapshots.py' -v
```

4. C manually reviews each `changed_source_keys[]` item against both original sources, records source/revision/effective-date evidence *separately*, checks relevant facility time and campus history, and flags any ambiguity. Neither source hash equality nor HTTP `Last-Modified`/ETag proves the official page is unchanged or historically applicable.
5. Only A/C verified and independently approved inputs may be considered for D reproduction (#266). Keep incompatible municipal `水害時待避施設`, GSI `skhb01`, and D municipal-location datasets separate. Preserve all unsupported flood status as `UNKNOWN` / `UNVERIFIED` and 0 approved physical-site pairs.

## Comparison output semantics

- `SOURCE_BYTES_CHANGED_REVIEW_REQUIRED`: at least one independently stored official raw file has different SHA256 **across two valid archives**. Human revision review required; not a legal interpretation.
- `BYTE_IDENTICAL_SNAPSHOTS_REVIEW_PENDING`: all seven captured file hashes match. This is **not** publisher freshness, historical validity, same physical shelter, current opening, or safety approval.
- `changed_source_count`: number of source originals with byte differences, **not** number of changed buildings or verified evacuation facilities.
- `content_shape_comparison`: source table and location CSV raw row counts. Do not assume baseline 111/152 is immutable; changed counts require independent original-content review.
- Reports always keep `source_revision_human_review_completed=false`, `physical_site_identity_human_review_completed=false`, `approved_cross_source_pairs=0`, and `flood_scenario_classifications_added=0`.

## Passed / Failed / Not run

- **Passed:** pending exact-head required CI and focused offline tests.
- **Failed:** pending.
- **Not run:** fresh official network capture (no workflow dispatch capability in this PR), comparison on two real new primary-source versions, independent human A/C source-version review, approved pair/campus linkage, live safety and D deployed output.
- **Reason:** this is a scoped offline C review mechanism; fetching official bytes is a separate real hosted/manual operation and human review is a separate authority.
