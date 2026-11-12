# C independent official-source edition audit: two distinct Shimokamata campuses (2026-10-13)

**UNAPPROVED SOURCE EVIDENCE. NOT THE CURRENT SAFE/OPEN STATUS OF ANY FACILITY.**

## Source provenance and independently audited pages

- **2026-04-01 as-of municipality disaster plan**, official direct PDF URL https://www.city.edogawa.tokyo.jp/documents/68931/00006.pdf, SHA256 92e85981c16542e3e28bd80bafc56c8a71f3ded9a8b5e67bcb53919d16e1ebcb. Original PDF page index 2 is external water inundation (外水氾濫), page 4 inland water inundation (内水氾濫). The C review used PyMuPDF to verify the page context, date text and BOTH former/new site labels and respective original address strings on the intended PDF pages. Both pages were also visually inspected as reference, **not human C signoff**.
- **2025-04 former school postclosure site-use change notice**, official URL https://www.city.edogawa.tokyo.jp/documents/40376/0704simokamata_1.pdf, SHA256 a4fee786088052e1bb787f0db0473245d01cc1cae9784c80ef40b3174ed089bf. One original PDF page, old/new intended property use and building demolition terms visible, no actual demolition-completion date certified.
- **2026 municipal former-school property-afteruse page**, URL https://www.city.edogawa.tokyo.jp/e085/kuseijoho/zaisei/kokyoshisetsu/rikatuyou.html, SHA256 a72a71f297d4dd3c3e0017b83051b5a26c8974415bc8f5316b71181d592589ca.
- GitHub Actions **38339232496 SUCCESS** official HTTPS archive → A original SHA check → C independent source URL/bytes/manifest verification → PDF page-content checks, **three original source hashes 3/3 identical**. Private UNAPPROVED artifact #11786311158 ZIP SHA256 b3ab0c220e8ca2b9abd9c83c182bb8c2ce9da01448ca2dfb041f020f16f4f35, expires 2026-10-20. C machine output: C_2026_EXTERNAL_INTERNAL_SOURCE_EDITION_VERIFIED_HUMAN_REVIEW_REQUIRED. C negative tests prohibit altered bytes, misleading URI/edition, faked human review and premature flood eligibility.
- C tool validation/validation/verify_edogawa_2026_water_site_revisions.py, tests test_edogawa_2026_water_site_revisions.py. Original site-source capture belongs to A PR #133 and shared isolated official-runner job PR #139.

## New evidence is more specific than the 2025-era water facility HTML

The **2026 original plan explicitly distinguishes two separate entries**. Source floor grades observed (manual page review not yet formally C signed):

| Source name | Original address | 外水氾濫 | 内水氾濫 |
| --- | --- | --- | --- |
| 下鎌田小 | 瑞江4-19-1 | B (=2F+) | A (=all floors) |
| 旧下鎌田小 | 東瑞江3-11-1 | B (=2F+) | A (=all floors) |

C must independently confirm that those grades attach to the actual relevant buildings (as opposed to a draft or typo), whether the older physical site remains, and whether opening/usable floors are currently operational. The original new-site address **瑞江4-19-1** differs from the original contemporary school directory **瑞江4丁目19番10号**; neither is silently corrected or rewritten.

**Potentially material conflict requiring prompt official clarification:**
- 2025 revised afteruse notice replaced an earlier proposal to retain the old gym as an emergency shelter with a plan to demolish all old buildings, including gym, for future metropolitan special-support school use. Timing under discussion; demolition completion is NOT established.
- 2026-04 plan nevertheless includes the old site as an external/inland inundation standby facility. A demolition PLAN alone is not a current demolition FACT; a dated listing alone is not an active opening guarantee. C must confirm from the responsible municipal disaster-prevention/asset divisions and retain both original versions.
- The municipality earlier 2025-12 HTML listed 下鎌田小 only at the old address. It may be a version-lagged cross-page reference; do not automatically overwrite its row with 2026 plan (or treat distinct official river/inland water categories as blanket flood-only GIS suitability).
- The **GSI 111 Edogawa records all had earthquake=1/flood blank**. They represent different registry semantics and do not exclude the water-standby entries. Preserve all separate typologies.

## C review blocking decision (Issue #141 / #134)

1. Confirm exact site/address and official 2026 plan subtype: external-river inundation vs inland-water inundation, accepted floor grades.
2. Verify the official 2026 PDF's apparent address digit discrepancy with contemporary school registry using a dated, authoritative correction or public decision record; never silently add a missing digit.
3. Ask whether the **old former school buildings including gym exist now**, their legal standby classification as of the review date, and whether a planned demolition changes emergency usage. The actual demolition schedule is missing; do not infer completed/not completed.
4. Record signed human C reviewer/date, official URL/digest/page, old/new campus ID and whether the original 2025 HTML row refers to the former physical site. Until then, neither row is an accepted D join.
5. D/C separately decides how to encode dated official external/internal flood standby listing vs generic flood-only Scenario and live opening. B/E cannot show verified candidate/exclusion without this contract review.
6. Verify all regions and staging acceptance before any merge or live data UI use.

**C approved physical site links: 0. New flood CANDIDATE/EXCLUDED: 0. D 152 statuses UNKNOWN. No D/B/E data changes, no main/Render changes, PR #136 Draft.** Evidence capture is a significant documentary improvement but not a safety certification.
