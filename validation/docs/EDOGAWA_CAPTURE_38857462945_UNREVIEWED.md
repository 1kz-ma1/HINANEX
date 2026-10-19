# C source review checkpoint — actual Edogawa capture run 38857462945

**Status (2026-10-19): SOURCE_BYTES_AND_CONTENT_SHAPE_PASS / TWO_ACTUAL_RUN_SHA_DELTA_RECHECKED / HUMAN_SOURCE_REVIEW_PENDING.**
This is a two-capture source reproducibility checkpoint for final-presentation Phase 1, not certification of publisher identity, source-effective dates, individual physical facilities, disaster suitability, or whether a destination is currently open. See #264 (A), #265 (C), #268 (combined).

## Exact provenance

- [Actions run 38857462945](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945) was manually dispatched **2026-10-16T05:45:43Z**, completed SUCCESS at commit `751277d89916b5c9035c8629538b45feb74d3756`.
- Manifest capture timestamp: `2026-10-16T05:46:02.560148+00:00`.
- All seven exact official HTTPS response byte sources were captured, and their allowlisted requested/final URLs, byte counts, SHA256 and manifest fail-closed flags passed the original C verifier.
- [Seven-originals UNREVIEWED artifact](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945/artifacts/12027766826) (7 source payloads + manifest) and [independent C content-report artifact](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945/artifacts/12027503328) (not approved).
- Artifacts expire **2026-10-23T05:46:04Z** and **2026-10-23T05:46:03Z** respectively (unless preserved privately beforehand). **Do not commit captured raw bytes to Git/Render.**
- Independently, local review of the downloaded original archive confirmed each payload matches its manifest SHA256/byte size, aggregate original bytes **229,156**. No unexpected archive files or missing source payloads were seen.

## Original-byte inventory — 2026-10-16 run, not authoritative source-version signoff

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
- A prior real hosted capture **was found in existing program Issue #268** (the previous review had overlooked it): [Actions #38505232094](https://github.com/1kz-ma1/HINANEX/actions/runs/38505232094), 2026-10-14T03:14:55.694183Z, commit `4559b06c46372e22edca388450606128047f099f`. Its [originals artifact #11867253502](https://github.com/1kz-ma1/HINANEX/actions/runs/38505232094/artifacts/11867253502) expires **2026-10-21T03:14:57Z** (so secure the private copy promptly); [C content report #11866799523](https://github.com/1kz-ma1/HINANEX/actions/runs/38505232094/artifacts/11866799523) expires one second earlier.
- Both downloaded original ZIP archives were independently rechecked: all seven payload SHA256 hashes/byte lengths match each archive's manifest, and the two separately generated C content-preflight reports have matching structure (111 water rows, 152 location CSV rows, former/current schools kept distinct, no C approvals).
- **Actual SHA comparison is 6 byte-identical originals and 1 changed original**. Only `tokyo_kasaikoka_school_access` differs: original SHA256 `b6fe6b0f831d9c328896a5a76f806bd3325a68972371c800e6c549bedb034ba5` → `8836084122ced9c7018e4440e23f4a404ae08dd268676874b592d8ad8c24cef0`; total original bytes are 229,156 at both timestamps. The exact original HTML bytes become equal when **only** the `<meta name="date" content="…">` time string is normalized. The printed meta dates are `2026-10-14T10:11:31+09:00` → `2026-10-14T15:39:11+09:00`. This is a source HTML metadata change, **not** evidence that any facility location, access, designated flood policy or publication/effective date changed.
- This independently reran the **byte comparisons on actual ZIP payloads**, rather than merely relying on a previous issue statement. The specific new C command `compare_edogawa_source_snapshots.py` has **not yet been run in this isolated container**; its deterministic synthetic tests did pass in merged PR #267. The separate human A/C semantic source revision and time-validity review remains pending.
- D's three-region real replay (#266), any new source-to-D acceptance and user-facing final release are **NOT TESTED** by this C snapshot run.

## Acceptance ledger

| Gate | Result | Evidence |
|---|---|---|
| New official HTTPS run | PASS | Actions #38857462945 |
| Seven raw bytes/manifest integrity | PASS | Runner verify output + separate downloaded ZIP SHA comparison |
| Live original content/CSV shape | PASS | `edogawa-C-content-UNREVIEWED-38857462945` |
| Human approval of source context/date | NOT TESTED | All seven manifest effective dates null |
| Two actual archived runs' seven SHA hashes compared | PASS | Downloaded ZIPs from Actions #38505232094 and #38857462945; 6 unchanged / 1 metadata-only SHA change |
| New C comparator CLI applied to these two archives | NOT TESTED | Independent ZIP byte comparison done; production CLI with original archive directories still to be run |
| Physical facility identity approvals | NOT TESTED | 0 approved; C/A review pending |
| Flood safety, opening, or GSI↔D joins | NOT TESTED | No data semantics or application inference |
