# C — 江戸川区水害待避施設×D位置データの保存版照合監査（2026-10-10）

## Status / Acceptance boundary

- **Snapshot consistency: locally rechecked on user-supplied files; PASS with one disclosed, formatting-only difference.**
- **Official independent online re-fetch: NOT RUN.** C signer/reviewer independent approval: **NOT GRANTED**.
- **Facility identity across the two official sources: NOT ACCEPTED.**
- **Flood-only suitability, opening and route safety: NOT VERIFIED; 0 CANDIDATE/EXCLUDED added.**
- This C result is not a flood-assessment certificate and must not be used to turn UNKNOWN into a positive/negative status.

## Reproducible checker

- C implementation: `validation/validation/verify_edogawa_water_join.py`
- C unit tests: `validation/validation/test_edogawa_water_join.py`
- Input: browser-saved municipality water-facility HTML, original archived municipality location CSV, matching historical D RegionExport and A candidate ledger.
- Independent verification design: HTML rows parsed by a C-specific HTML parser; CSV decoded CP932; D location ID recomputed from original source name/lat/lon; all A row fields, candidate IDs/names, raw usable-floor data, original address and SHA256 digests checked without importing A or D evaluators.
- Accepts both the existing A user review workbook's JSON schema and PR #133's new `rows / candidate_location_rows` A generator format. **Neither status format can output VERIFIED_PAIR or classify a facility.**
- Conditional acceptance rejects: altered original floor/address/name, changed source IDs/lat/lon, location-side addresses not in original CSV, duplicate facility hints, false C approval, invalid source hash, or preapproved Scenario promotion.
- Run from repo root (PowerShell):

~~~powershell
python -m unittest discover -s validation/validation -p "test_edogawa_water_join.py" -v
python validation/validation/verify_edogawa_water_join.py --water-html "C:\evidence\edogawa_water_saved.html" --location-csv "C:\evidence\20251211_hinanhokan.csv" --region-export "C:\evidence\edogawa.json" --a-ledger "C:\evidence\edogawa_water_review_20261010.json" --report "C:\evidence\c_snapshot_audit.json"
~~~

## Result for files supplied in chat

| Local input | SHA256 |
| --- | --- |
| Saved official water HTML | `0d7dbf91ce630643f4868cf9d8547eb7acb4398035304d91833731956c44e772` |
| Source Edogawa 20251211 CP932 CSV | `64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea` |
| Historical D RegionExport `edogawa.json` | `f285f9cadb9424a79f0107ddadccd7ba64f2b807f43fea54291d5fc99672da7a` |

- Two relevant HTML tables: 111 original water-disaster standby facility rows.
- CP932 official location CSV: 152 rows, with **no** address / location address field.
- Historical D JSON: 152 rows; C recomputed each JSON ID from name/lat/lon and independently checked 152/152 source CSV row pairs. All 152 addresses are null. The old JSON predates optional flood `scenarios` and must **not** overwrite current main/staging export.
- A review ledger source-field checks: 56 exact normalized-name hints, 52 controlled abbreviation-name hints, 3 manual-review rows; no reused ID among the 108 one-to-one *hints*. **No independent institution-identity approval** (C approved pairs=0).
- Manual review: `旧下小岩小学校` (2 distinct potential D facility rows, with a large-scale water-disaster conditional warning), `都立 葛西工高等学校` and `私立 関東一高等学校` (school-naming semantics are not a shared facility ID).
- Original usable-floor raw histogram: `2階以上=62`, `3階以上=40`, `すべての階=7`, `地下を除くすべての階=1`, `大規模水害では使用不可=1`.
- **One formatting difference:** HTML row 19 phone field contains two numbers separated by newline/tab; earlier A display ledger serialized the same numbers with one space. C compared both numbers after whitespace-only collapsing and explicitly counted **1 phone whitespace normalization**. No address, facility name or usable-floor raw mismatches found. This does not make original phone field byte-identical.
- Browser-saved pages are **not** proof of current municipal server byte-for-byte version.

## Next official data / approval gates

1. Independently fetch current municipal HTML and location CSV, record HTTP retrieval time, official publisher, source version, bytes and SHA256. Compare to the historical uploaded snapshots; do not assume they match.
2. A prepares official row-to-location ID candidate evidence; **C separately confirms the same physical institution with an independently attributable address or municipal ID**. All 108 name hints are unapproved until then, despite internal consistency.
3. Examine 3 exceptions and old/new school sites. `旧下小岩小学校` special non-use condition must not propagate to a different school/gym merely because of its name.
4. D/C agree the exact meaning of source `水害待避施設` in a flood-only Scenario; do not re-label it as an official flood-only emergency designation.
5. After written cross-source and semantic acceptance, change only the appropriately supported D records; use new C negative tests for ambiguous/no join, missing status and altered official-source version.
6. Review latest main, A #133, D #135 and multi-role contract before Merge Captain integration.

Related: [A PR #133](https://github.com/1kz-ma1/HINANEX/pull/133), [D PR #135](https://github.com/1kz-ma1/HINANEX/pull/135), [Edogawa source join Issue #134](https://github.com/1kz-ma1/HINANEX/issues/134), [10/22 gate Issue #89](https://github.com/1kz-ma1/HINANEX/issues/89).
