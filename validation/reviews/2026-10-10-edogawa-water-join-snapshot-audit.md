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

## 2026-10-10 official secondary-source corroboration of three exceptions (research leads; no approval)

This **additional web review** checks separate authoritative institutions' descriptions. It is **not** official server-byte archive acceptance, not independent C signer review, not a valid D ID cross-source join, and not a flood-only Scenario interpretation.

| Case on user-saved water table | Original water row evidence | Separate authoritative evidence / interpretation |
| --- | --- | --- |
| `都立 葛西工高等学校` | `一之江7丁目68番1号` / `03-3653-4111` / `2階以上` | City official [都立・私立学校一覧](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/toritsushiritsu.html) lists `都立葛西工科高校` with matching address/phone; official [東京都立葛西工科高等学校アクセス](https://www.metro.ed.jp/kasaikoka-h/access/access.html) independently lists its full name and same address. **Cross-document institution reference is strongly corroborated**, but the D location record's own municipal Source has no address column and C has NOT accepted its ID against the water-page facility. |
| `私立 関東一高等学校` | `松島2丁目10番11号` / `03-3653-1541` / `3階以上` | Same city official school list lists `関東第一高校` with same address/phone. [School's official overview](https://www.kanto-ichiko.ac.jp/about/outline/) confirms formal name `関東第一高等学校`, address and same phone. **Additional documentary corroboration**, NOT a D official-flood-Scenario pairing acceptance. |
| `旧下小岩小学校` | `南小岩7丁目8番1号` / `大規模水害では使用不可` | Tokyo Metropolitan Government's [避難施設一覧（令和7年8月29日現在）](https://www.bousai.metro.tokyo.lg.jp/_res/projects/default_project/_page_/001/030/344/250901itiran.pdf) distinguishes `旧下小岩小学校` at `南小岩7丁目8番1号` from `下小岩小学校` at `南小岩5丁目5番1号`; the [Edogawa official neighborhood shelter page](https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/jijo/search-1/s-koiwa1-8.html) independently lists both. **Never join the old school's non-use condition to the newer school or collapse them into one site**. Flood-only or real-time status remains unverified. |

- **Important temporal scope:** the city school list is dated 2023-12-26 and the Tokyo PDF 2025-08-29; the city's saved water-facility page displays 2025-12-19. These different versions have not been accepted as a synchronized current emergency dataset. C must check official latest revisions when accepting matching.
- These external corroboration links were checked as public website/page content; do not claim that the linked PDFs/HTML were independently downloaded and byte-hashed locally in this run.
- Recommended reviewer sequence: validate official source version → verify identity of each location **record** via a separate authoritative address and origin row/ID → decide water standby vs flood-only semantics in D/C → assert scenario outcomes only with positive evidence. Until then `C-approved=0`, `Scenario newly classified=0`.
