# C source review checkpoint — actual Edogawa capture run 38857462945

**Status (2026-10-19): SOURCE_BYTES_AND_CONTENT_SHAPE_PASS / HUMAN_SOURCE_REVIEW_PENDING / TWO_RUN_DELTA_NOT_TESTED.**
This is a reproducibility checkpoint for final-presentation Phase 1, not certification of publisher identity, source-effective dates, individual physical facilities, disaster suitability, or whether a destination is currently open. See #264 (A), #265 (C), #268 (combined).

## Exact provenance

- [Actions run 38857462945](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945) was manually dispatched **2026-10-16T05:45:43Z**, completed SUCCESS at commit `751277d89916b5c9035c8629538b45feb74d3756`.
- Manifest capture timestamp: `2026-10-16T05:46:02.560148+00:00`.
- All seven exact official HTTPS response byte sources were captured, and their allowlisted requested/final URLs, byte counts, SHA256 and manifest fail-closed flags passed the original C verifier.
- [Seven-originals UNREVIEWED artifact](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945/artifacts/12027766826) (7 source payloads + manifest) and [independent C content-report artifact](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945/artifacts/12027503328) (not approved).
- Artifacts expire **2026-10-23T05:46:04Z** and **2026-10-23T05:46:03Z** respectively (unless preserved privately beforehand). **Do not commit captured raw bytes to Git/Render.**
- Independently, local review of the downloaded original archive confirmed each payload matches its manifest SHA256/byte size, aggregate original bytes **229,156**. No unexpected archive files or missing source payloads were seen.

## Original-byte inventory — exact run, not authoritative source-version signoff

| C source key | Bytes | SHA256 of original response |
|---|---:|---|
| `water_facilities` | 35,009 | `96001e1a22cdc19580f0c4483e01f2f2e1e6d8b2c595ee5d751f24bf836d4deb` |
| `municipal_locations` | 24,777 | `64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea` |
| `municipal_school_list` | 17,027 | `d5d0034497710c77d59983001f5f0bfc62b45bce2e02d62cb397b06c13f6b74d` |
| `municipal_primary_school_list` | 35,353 | `b8939ebfcd530ce34f20018461d2575bbaa3375ca5be45ec9e4c1d9dcb5e8fc1` |
| `municipal_2025_school_relocation` | 18,209 | `ea3ea43d17264d071d64ade974be2b385817e1eed62ad2ba843ae4e04a7838f6` |
| `tokyo_kasaikoka_school_access` | 10,976 | `8836084122ced9c7018e4440e23f4a404ae08dd268676874b592d8ad8c24cef0` |
| `kanto_ichiko_school_overview` | 87,805 | `dab8fbb7fe4d80362e26acdae9212866d108b5196324ccccacadd5665e58dc84` |

A capture run's pass means **this captured byte set is internally consistent**, not that the captured page matches an unaltered historical official edition.

## Independently preflighted source structure

The Actions log and its preserved content preflight report both returned
`ORIGINAL_CONTENT_STRUCTURE_CHECKED_HUMAN_REVIEW_REQUIRED`:
- Water-related official page: **2 tables, 111 rows**.
- Municipal original location CSV: **152 rows**.
- Original water-table usability/floor labels (source-only, not recommended floors):
  `2階以上` 62; `3階以上` 40; `すべての階` 7;
  `地下を除くすべての階` 1; `大規模水害では使用不可` 1.
- The historical priority water rows include **108** `都立 葛西工高等学校` and
  **109** `私立 関東一高等学校` with original address and floor fields.
  These are *matching source text* observations, not approved same-facility matches with another official list.
- The current and former `下小岩小学校` are explicitly distinct in the C source preflight; their physical site/address must **not** be automatically merged.

## Dates seen *inside* captured pages — NOT approved effective dates

The following are **page text displayed in this exact archived capture**,
not C-reviewed publication dates or the effective date of each physical facility:

| Captured original | Date/context printed in that page | Needed A/C review |
|---|---|---|
| `water_facilities` | `更新日：2025年12月19日` | Verify which table edition these labels belong to |
| `municipal_school_list` | `更新日：2023年12月26日` | Confirm that old private/prefectural school names are treated as time-specific |
| `municipal_primary_school_list` | `更新日：2025年9月25日` | Confirm new school locations and former-school closures separately |
| `municipal_2025_school_relocation` | `更新日：2025年4月25日`; announcement says 2025-04-21 | Do not equate press date with a school's legal/operational effective date |
| `tokyo_kasaikoka_school_access` | No date independently established here | Needs explicit school-source review |
| `kanto_ichiko_school_overview` | Includes `生徒数（令和8年4月）` and school history | Student-count reference date is **not** a flood-facility designation date |
| `municipal_locations` | filename includes `20251211` | Filename is not a certified publication/operational effective date |

The authoritative manifest **still has `official_publication_or_effective_date: null` for all seven sources** and `date_context_review_required: true` for all. Preserve those machine values until a C human review explicitly validates scope.

## No-approval invariants and remaining blockers

- `human_c_reviewer_signed_off=false`;
  `approved_cross_source_pairs=0`;
  `flood_scenario_classifications_added=0`;
  `publisher_authenticity_independently_attested=false` in the isolated verification output.
- Distinguish municipal `水害時待避施設` rows, municipal locations CSV and GSI `skhb01` (洪水指定緊急避難場所): **no automatic join** and **no claim of open/currently safe destinations**.
- Official source-content/version approval and old/current site identity remain A/C manual tasks (#264).
- **No second real archived capture** was found in the current Actions workflow history as of 2026-10-19. Thus the new comparator in #267 **has not run on two distinct actual snapshots**, and no real old→new SHA deltas can be claimed. To enable that report, obtain a newer independent capture before the earlier seven-day artifact expires, keep both archives separately outside Git, and run the [read-only comparison procedure](FINAL_SOURCE_RECAPTURE_20261016.md).
- D's three-region real replay (#266), any new source-to-D acceptance and user-facing final release are **NOT TESTED** by this C snapshot run.

## Acceptance ledger

| Gate | Result | Evidence |
|---|---|---|
| New official HTTPS run | PASS | Actions #38857462945 |
| Seven raw bytes/manifest integrity | PASS | Runner verify output + separate downloaded ZIP SHA comparison |
| Live original content/CSV shape | PASS | `edogawa-C-content-UNREVIEWED-38857462945` |
| Human approval of source context/date | NOT TESTED | All seven manifest effective dates null |
| Two distinct real-time archives compared | NOT TESTED | Only one identified actual hosted capture |
| Physical facility identity approvals | NOT TESTED | 0 approved; C/A review pending |
| Flood safety, opening, or GSI↔D joins | NOT TESTED | No data semantics or application inference |
