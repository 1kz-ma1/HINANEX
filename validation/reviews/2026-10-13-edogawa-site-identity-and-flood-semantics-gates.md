# Edogawa: Independent C gate for site identity vs flood-only scenario (2026-10-13)

Status: EVIDENCE-BASED REVIEW IN PROGRESS, **NOT APPROVED**.

## Official scope evidence

- Source: https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html
  Municipality water-facility original SHA256: 96001e1a22cdc19580f0c4483e01f2f2e1e6d8b2c595ee5d751f24bf836d4deb. The source lists named emergency standby sites and original usable floors.
- Supporting official guidance: https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/suigaihinan.html
  A standby facility is for people unable to leave in time or move farther. It may have inundated lower floors and limited supplies. **This separate page has not been original-byte archived by the 7-source collector; independently review its current publication date before formal semantics acceptance.**
- Supporting official operational context: https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/jijo/suigaihinan.html
  Water-disaster response varies by weather phase; no historic facility list certifies real-time opening. **This separate guidance has not yet been SHA256-pinned in the seven originals.**
- Separate location dataset: official 20251211_hinanhokan.csv with 152 rows, SHA256 64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea, contains name, URL, icon, notes, latitude and longitude **but no location-side address or municipality-certified cross-source ID**. The icon is not a verified flood designation.
- Exact A→current D→C runner https://github.com/1kz-ma1/HINANEX/actions/runs/38332810819 succeeded for source trace consistency only (111 water rows; 152 D positions).

## Independent decision axes

1. SOURCE VALIDITY — Official raw bytes, headers, SHA and time context. Valid source bytes do not prove facility identity.
2. PHYSICAL SITE PAIRING — The water table names/addresses and the school directory + school-operated sites corroborate contact/location text, **not** D CSV coordinates tied to the exact same campus. The D ID is a local name+coordinate hash, not a shared government ID. Reviewer must inspect trusted geographical/site documentation, aliases, school history, exact campus and source dates.
3. DISASTER TYPOLOGY — Emergency water-disaster standby use is not synonymous with unconditional flood-only designated emergency eligibility. The raw floors and conditions are source facts, not a safe/unsafe result.
4. REAL-TIME OPERATION — Flood conditions, opening, accessibility and route safety are not inferred from a stored list.
5. SCENARIO PROMOTION — UNKNOWN remains for every unreviewed pairing even if documentary evidence appears strong; verified identity would not by itself resolve flood-only scope.

## Priority site reviews — no auto-approval

| Water source | Official water address/phone/floor | Other official documentary leads | D ID |
| --- | --- | --- | --- |
| #108 都立 葛西工高等学校 | 一之江7丁目68番1号 / 03-3653-4111 / 2階以上 | Municipal directory row uses 都立葛西工科高校; Tokyo high school access page https://www.metro.ed.jp/kasaikoka-h/access/access.html writes 一之江7-68-1; human confirms notation + same exact campus | edogawa-d79a702373c6add7 |
| #109 私立 関東一高等学校 | 松島2丁目10番11号 / 03-3653-1541 / 3階以上 | Municipal directory row uses 関東第一高校; institution https://www.kanto-ichiko.ac.jp/about/outline/ writes 松島二丁目10番11号; human confirms notation + same exact campus | edogawa-fbe048a8e7100768 |

For both: C person has not independently approved the coordinate-to-physical-school match. Human judgment needs reviewer/date, exact source URLs and digests, original excerpts, independently inspected official campus evidence and rationale. Do not automatically approve based on school name, phone, address text, URL or nearby position.

**Former/current Shimo-Koiwa separation:** old school 南小岩7丁目8番1号 was labeled 大規模水害では使用不可; current school 南小岩5丁目5番1号 is labeled 2階以上. The D records share a school homepage URL but NOT campus identity. Retain two D IDs and separate floor restrictions.

## D/C signoff checklist

- [x] Official water/list original 7-source archive SHA consistency, preflight and version pinning
- [x] CSV→current D trace 152/152 and A source table→C trace 111/111
- [x] 2-school unapproved human review packet from original institutional pages
- [ ] C human reviewer verifies **physical D position vs exact official campus**, with separate dated acceptance and source digests per pair
- [ ] D/C formally agree hazard subtype, scope, conditions and exact meaning of 水害待避施設 vs 洪水単独指定; supporting guidance original bytes and applicability dates still need capture
- [ ] Reviewed cross-source link represented separately from DIRECT_SAME_SOURCE, with independent C checks and Contract review if schema affected
- [ ] B/E staging smoke and Merge Captain integration confirmation

**0 accepted physical facility pairs; 0 new CANDIDATE/EXCLUDED; 152 UNKNOWN; main and Render unchanged.** This document grants neither a flood assessment nor a live opening/safety recommendation.
