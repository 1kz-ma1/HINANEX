# A source addendum: 2026-04-01 river / inland water standby lists and former campus reuse

Status: **Municipal official originals acquired and independently verified. NO SAME-CAMPUS IDENTITY OR LIVE SAFETY APPROVAL.** Source observations only, not D input replacement.

## The new official primary disaster-plan revision is materially different

Edogawa municipal 2026 region disaster plan, original https://www.city.edogawa.tokyo.jp/documents/68931/00006.pdf, PDF original SHA256 **92e85981c16542e3e28bd80bafc56c8a71f3ded9a8b5e67bcb53919d16e1ebcb** (3,859,329 bytes). Original PDF page index 2 (printed page 141) says *待避施設一覧表（外水氾濫）*, and page index 4 (printed page 143) says *待避施設一覧表（内水氾濫）*. BOTH are explicitly **令和8年4月1日現在**, distinct from older source HTML and from a legal flood-only designated emergency evacuation place.

| Original official school label | 2026 flood plan address exactly as printed | 外水氾濫 original grade | 内水氾濫 original grade |
| --- | --- | --- | --- |
| 下鎌田小 | **瑞江4-19-1** | B: 2階以上 | A: すべての階 |
| **旧下鎌田小** | **東瑞江3-11-1** | B: 2階以上 | A: すべての階 |

This is direct official documentary evidence that the municipality **separately listed a new and a former campus** as of 2026-04-01, even though a late-2025 water-standby HTML table still says "下鎌田小学校" at the old 東瑞江 site. The 2025-04-01 official disaster-plan PDF version lists only old 下鎌田 at 東瑞江3-11-1. **Do not mutate the older source or infer it was a database corruption; different source documents represent different dates.**

**Address discrepancy requiring verification**: The 2026 PDF writes **瑞江4-19-1**; the 2026 municipal school directory/GSI register lists the actual contemporary school as **瑞江4丁目19番10号**. This may be typographical, but that interpretation is unapproved. No numeric address correction or new D facility identity may be written without a documented authoritative review.

## Official post-closure site-use change creates a safety-sensitive condition

The separate April 2025 notice *旧下鎌田小学校 後利用方針変更のお知らせ*, official original https://www.city.edogawa.tokyo.jp/documents/40376/0704simokamata_1.pdf, PDF SHA256 **a4fee786088052e1bb787f0db0473245d01cc1cae9784c80ef40b3174ed089bf** (24,991 bytes), shows a BEFORE/AFTER decision:
- Previous plan stated *体育館* would continue to be used as an emergency evacuation shelter after checking safety, while original school buildings would be demolished/used for parkland.
- **Revised** plan says **校舎・校庭・体育館のすべての建物を解体** and to prepare land for a Tokyo metropolitan special-support school; actual demolition timing is still being arranged. It does NOT prove the buildings were already demolished as of 2026-10.
- A 2026-08-04 official municipal page https://www.city.edogawa.tokyo.jp/e085/kuseijoho/zaisei/kokyoshisetsu/rikatuyou.html, SHA256 **a72a71f297d4dd3c3e0017b83051b5a26c8974415bc8f5316b71181d592589ca** (19,876 bytes), lists the former 下鎌田 school as a post-closure property and links that 2025 revised policy. It is NOT a current opening register.

The revised demolition **plan** and the April 2026 two-campus **water standby list** can coexist, but require a direct municipality confirmation whether the former-campus standby designation, actual usable buildings/floors and active opening policy are still valid. Do not silently label old site CANDIDATE nor EXCLUDED.

## Reproducible original archive: isolated from prior 7 school-history originals and GSI

- A collector: data-research/tools/archive_edogawa_2026_water_site_revisions.py; A offline negative tests in data-research/tests/test_archive_edogawa_2026_water_site_revisions.py.
- C independent PDF-page-content audit: validation/validation/verify_edogawa_2026_water_site_revisions.py; C independent synthetic negative tests under validation/validation/test_edogawa_2026_water_site_revisions.py.
- Hosted real original network + PyMuPDF original page read **SUCCESS**: https://github.com/1kz-ma1/HINANEX/actions/runs/38339232496, including A+C original source capture, independent integrity and page-marker checks. Captured 2026-10-13 UTC, artifact #11786311158, expires 2026-10-20. GitHub artifact ZIP SHA256 **b3ab0c220e8cae2b9abd9c83c182bb8c2ce9da01448ca2dfb041f020f16f4f35**, all original 3/3 file hashes independently rechecked.
- No raw PDFs, archived HTML or generated C report committed to the repository. This evidence must be linked to, not substituted for, prior 2025-12 HTML, 2025-04 PDF, current D location CSV, and GSI 111-row earthquake-designated places.

**Source validity ≠ site-pair validity ≠ hazard subtype applicability ≠ today's opening.** C human physical-site approvals 0, flood CANDIDATE/EXCLUDED added 0, current D 152 UNKNOWN. Need C individual campus time/same-building review and D/C scope review before any new D facilities or B/E status display.
