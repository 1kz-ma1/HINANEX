# A / Edogawa final-presentation source version handoff — 2026-10-19

**Role:** A/Data Research, primary-source evidence only. **Status:** `SOURCE_ORIGINALS_CAPTURED_C_TECHNICAL_REPORT_VERIFIED; HUMAN_A_REVIEW_PENDING`. This is a versioned *review candidate*, **not** approved publication/effective-date metadata, a designated evacuation facility identity, or permission to change D/GSI data. Tracks #264, #265, #268. Prior A school-campus/other-water evidence remains independent: [school history](2026-10-13-edogawa-school-campus-history-evidence.md), [2026 external/inland water plan](2026-10-13-edogawa-2026-external-inland-water-original-evidence.md).

## 1. Immutable original source provenance

These are **two real GitHub-hosted HTTPS collection runs**, with raw originals independently checked by C.

| Capture | UTC | GitHub workflow / immutable raw artifact ZIP | ZIP SHA256 |
|---|---|---|---|
| Previous | `2026-10-14T03:14:55.694183+00:00` | [run #38505232094](https://github.com/1kz-ma1/HINANEX/actions/runs/38505232094), artifact `11867253502` | `1abd49c441c51e556636feeac882ed35949cb97c1cf5b2676c96dd5463e63cb2` |
| Later | `2026-10-16T05:46:02.560148+00:00` | [run #38857462945](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945), artifact `12027766826` | `38cb124ab8f5b7c557fd646dc85c0e7f2a40c41e21365c6b89646186dae48c3a` |

Original HTTPS bytes / response metadata are in private manifest-backed archives, **not checked into Git/Render**. HTTP download does not prove the publisher served that identical content at a different historical date. Compare outputs by the C code pinned at `8615c0060a02f9c824ebc846dcf930b042a29a6f` and a user's Oct19 actual CLI execution; the exact JSON report digest `ec7215818b79f0bd8680470e650103c2f09ddf928807819a8c5ea7886560f418` was independently reconciled against saved raw evidence 16/16. The local unsigned operator receipt is not independent process attestation.

**Seven allowlisted official source references, publisher and later-capture original SHA256** (the requested and final URL were identical for each of these captures):

| Source key | Publisher / original URL | Format / bytes | Original SHA256 on Oct16 |
|---|---|---|---|
| `water_facilities` | 江戸川区: [water waiting-facilities table](https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html) | HTML 35,009 | `96001e1a22cdc19580f0c4483e01f2f2e1e6d8b2c595ee5d751f24bf836d4deb` |
| `municipal_locations` | 江戸川区: [municipal CSV](https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv) | CSV 24,777, source CP932 | `64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea` |
| `municipal_school_list` | 江戸川区: [prefectural/private schools](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/toritsushiritsu.html) | HTML 17,027 | `d5d0034497710c77d59983001f5f0bfc62b45bce2e02d62cb397b06c13f6b74d` |
| `municipal_primary_school_list` | 江戸川区: [municipal primary schools](https://www.city.edogawa.tokyo.jp/e068/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/shogakko.html) | HTML 35,353 | `b8939ebfcd530ce34f20018461d2575bbaa3375ca5be45ec9e4c1d9dcb5e8fc1` |
| `municipal_2025_school_relocation` | 江戸川区: [2025 school-new-building notice](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/kohokocho/press/2025/04/0421.html) | HTML 18,209 | `ea3ea43d17264d071d64ade974be2b385817e1eed62ad2ba843ae4e04a7838f6` |
| `tokyo_kasaikoka_school_access` | 東京都教育委員会 / 都立葛西工科高校: [access page](https://www.metro.ed.jp/kasaikoka-h/access/access.html) | HTML 10,976 | `8836084122ced9c7018e4440e23f4a404ae08dd268676874b592d8ad8c24cef0` |
| `kanto_ichiko_school_overview` | 関東第一高等学校: [school outline](https://www.kanto-ichiko.ac.jp/about/outline/) | HTML 87,805 | `dab8fbb7fe4d80362e26acdae9212866d108b5196324ccccacadd5665e58dc84` |

MIME comes from archive response headers (`text/html`, `text/csv`; the private-school overview specified `text/html; charset=UTF-8`), not independent content certification. Encoding of original CSV was checked for this extract; neither the MIME nor inferred decoding should modify the saved original bytes. All seven effective/publication date *machine fields remain null*. HTTP Last-Modified/ETag are **unverified server metadata**, not authoritative dates; see C original manifest/inventory for exact response headers. Reuse/license terms: **NOT VERIFIED** for the seven-page collected bytes (do not infer from the fact that a page is publicly accessible).

## 2. Verified capture-time comparison versus source-specific context

- Exact content shape in **both** runs: 111 municipal water-table rows, 152 municipal location CSV rows, both obtained from the preserved official raw. This is dataset *scope*, not certified counts of current usable flood-designated places.
- **6/7 original payloads identical**, **1/7 changed**: `tokyo_kasaikoka_school_access` old SHA256 `b6fe6b0f831d9c328896a5a76f806bd3325a68972371c800e6c549bedb034ba5` → new SHA256 `8836084122ced9c7018e4440e23f4a404ae08dd268676874b592d8ad8c24cef0`. Only HTML `<meta name="date">` changed `2026-10-14T10:11:31+09:00` → `2026-10-14T15:39:11+09:00`; after normalizing only that attribute the original bodies are byte-identical. **Publisher revision meaning and effective date remain unapproved.**
- In the captured municipal waiting-facility HTML, `下小岩小学校` (南小岩5丁目5番1号, label `2階以上`) and `旧下小岩小学校` (南小岩7丁目8番1号, label `大規模水害では使用不可`) appear separately. The separate official location CSV also has **two different rows/coordinates**. A page value is a literal source statement, **not a live opening/safety claim**.
- The [current municipal school roster](https://www.city.edogawa.tokyo.jp/e068/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/shogakko.html) describes the old school as closed in March 2023. The distinct [April 30, 2025 official release](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/kohokocho/press/2025/04/0430.html), checked as additional contextual source on 2026-10-19 but **not one of the seven originals**, describes the new school building as in school use since **April 2025**. That is **not the effective date of flood/water-disaster designation**.
- Historical [municipal election-site data](https://www.city.edogawa.tokyo.jp/senkyo/data/togikai/basho.html) separately uses the old address as a polling place. Election role, school operation and disaster response are distinct administrative purposes; do not collapse names.
- The **2026-04-01 external/inland-water disaster-plan PDF** is a **separate existing A evidence stream** from the 2025-12 water waiting-facility webpage. Its source rows, official date, and campus conflicts must be independently analyzed, not overwritten into the seven-capture result, including older/newer Shimo-Kamata sites.

## 3. Human A review / C handoff decisions still required

Human A reviewer must record an identity, UTC review date, exact source/page or original SHA reference, source owner, specific assertion, evidence, decision and caveats. No autonomous acceptance:

1. Verify the precise role and version/date context of each of seven sources; distinguish published, updated, cited reference date, HTML metadata and operational use. Maintain `published_at = null` / `effective_date = null` unless an appropriately scoped official original explicitly establishes it.
2. Verify reuse/attribution conditions separately for each collected source. Record `UNKNOWN` when not established; do not invent license.
3. Resolve the timeline and **separate original physical sites** for current/old Shimo-Koiwa and other legacy school-campus transitions with primary-source proof; do not map by fuzzy name, positional proximity or period-agnostic address.
4. Hand each proposed **specific**, dated source-to-physical-facility association to independent C for review; do not preapprove by adding this memo.
5. Keep `municipal_locations`, municipality `水害時待避施設`, GSI `skhb01`, 2026 external/inland-water plan, school educational role and election polling place as **separate evidence classes**. Do not upgrade `UNKNOWN/UNVERIFIED` flood status; `fire.png`/blank icon is not a flood decision.

**A formal human source/version signoff:** **NOT PROVIDED**. **C same-physical-site identity signoff:** **NOT PROVIDED**. **A→D input promotion:** **BLOCKED**. This A memo is intended for human review via Issue #264, then C #265, before D #266's pinned three-region replay. Raw originals never enter Git/Render.
