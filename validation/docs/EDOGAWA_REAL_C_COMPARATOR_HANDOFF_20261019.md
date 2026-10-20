# C final presentation — real two-capture comparator acceptance ledger (2026-10-19)

**Technical status:** `C_FORMAL_REPORT_INDEPENDENTLY_CONSISTENT` / **Human approval:** `PENDING` / **D handoff:** `HOLD`.

This C-scoped memo replaces the *pending actual operator replay* checkpoint in the earlier [recapture procedure](FINAL_SOURCE_RECAPTURE_20261016.md) and [Oct16 capture inventory](EDOGAWA_CAPTURE_38857462945_UNREVIEWED.md) as the current replay status. Earlier dated statements are historical. It is not a publisher attestation, signoff of disaster usability, a source-version approval, or an authorized physical-site join. See A #264, C #265, D #266, combined #268.

## 1. Exact operator provenance and independent check

| Field | Original evidence / status |
|---|---|
| Pinned `main` at operator run | `8615c0060a02f9c824ebc846dcf930b042a29a6f` |
| Unmodified executable | `validation/validation/compare_edogawa_source_snapshots.py` |
| Earlier capture | [Actions #38505232094](https://github.com/1kz-ma1/HINANEX/actions/runs/38505232094), `2026-10-14T03:14:55.694183+00:00` |
| Later capture | [Actions #38857462945](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945), `2026-10-16T05:46:02.560148+00:00` |
| Earlier downloaded artifact ZIP SHA256 | `1abd49c441c51e556636feeac882ed35949cb97c1cf5b2676c96dd5463e63cb2` |
| Later downloaded artifact ZIP SHA256 | `38cb124ab8f5b7c557fd646dc85c0e7f2a40c41e21365c6b89646186dae48c3a` |
| Actual upstream C comparison report SHA256 | `ec7215818b79f0bd8680470e650103c2f09ddf928807819a8c5ea7886560f418` |
| Mac operator receipt SHA256 | `d47d219d388f672298405f7176e90bf0ab34a160989dd47f17e271a9a629f21c` |
| Operator CLI console | `UPSTREAM C CLI COMPLETE — UNREVIEWED` |
| Final report status | `SOURCE_BYTES_CHANGED_REVIEW_REQUIRED` |
| C independent raw/receipt/report consistency | `16/16 PASS`, comparing supplied original JSON bytes to privately preserved ZIPs, original content preflight JSON and manifests |
| Independent C→D gate on actual report | `BLOCKED_PENDING_C_A_HUMAN_SOURCE_REVIEW`; focused offline negative tests `7/7 PASS` |
| Third-party process attestation | **NOT PROVIDED**. Receipt is an unsigned operator declaration corroborated by original bytes, not a cryptographic execution attestation |

**Handling:** Original source ZIPs, report JSON and receipt are preserved privately **outside Git/Render**. Only derived filenames, digests, original source *links*, and review metadata are recorded here. Do not commit captured raw HTML/CSV, private local paths, unreviewed artifacts, or potentially misleading approved status.

## 2. Comparator result and non-inference invariants

Exactly seven allowlisted original source keys were compared. All seven retain unknown official publication/effective-date fields (`null`); HTTP ETag and Last-Modified values are **unverified HTTP hints**, not certified official dates.

| Source key | Old→new original bytes | Observed check | Human review |
|---|---|---|---|
| `water_facilities` | identical | 111 table rows both runs; distinct current/old school names and source-literal floor labels | Source category, edition, scope and applicability |
| `municipal_locations` | identical | 152 CSV data rows both runs; current/old school records separate | CSV column meaning, coordinates and physical ID, separately from water categories |
| `municipal_school_list` | identical | Tokyo/private school listing; page date is context | Institution naming/edition |
| `municipal_primary_school_list` | identical | Current school address and former-school closure labels | School identity and school-list time scope |
| `municipal_2025_school_relocation` | identical | School new-building press statement; date is contextual | Distinguish school use date from flood designation |
| `tokyo_kasaikoka_school_access` | **changed** | Only `<meta name="date">` timestamp changes; unchanged otherwise after single-field normalization | Explain metadata change, publisher/time authenticity |
| `kanto_ichiko_school_overview` | identical | School overview; dated student counts are not disaster designation dates | Source edition and institution context |

Exact change: `tokyo_kasaikoka_school_access` SHA256 `b6fe6b0f831d9c328896a5a76f806bd3325a68972371c800e6c549bedb034ba5` → `8836084122ced9c7018e4440e23f4a404ae08dd268676874b592d8ad8c24cef0`; archived HTML `meta date` changes `2026-10-14T10:11:31+09:00` → `2026-10-14T15:39:11+09:00`. This is a **change in bytes**, not evidence of changed shelter function, certified publication date or effective date.

### Facility-identity review example: keep physical sites separate

**Read from the actual Oct14/Oct16 archived originals (not from D export):**

- Municipal water waiting-facility source [original page](https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html): `下小岩小学校`, `南小岩5丁目5番1号`, `2階以上` (row 60) and a different `旧下小岩小学校`, `南小岩7丁目8番1号`, `大規模水害では使用不可` (row marked `-`). These are **raw literal row assertions** and not a recommendation to shelter there.
- Municipal locations CSV [original CSV URL](https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv): distinct `下小岩小学校` (row 23, lat `35.7254506`, lon `139.8784285`) and `旧下小岩小学校（体育館のみ使用）` (row 114, lat `35.7276762`, lon `139.8831013`). Coordinate values are archived *source rows*, **not independently geodetic-certified physical identity**.
- The [2025-09-25 school list](https://www.city.edogawa.tokyo.jp/e068/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/shogakko.html) identifies the current school and states the former school closed March 2023. The municipal [2025-04-30 school press notice](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/kohokocho/press/2025/04/0430.html), an **additional context source not among the seven captures**, states that the new building began school use in **April 2025**. This does **not** date flood designation/effective status.
- Historic [Tokyo Assembly polling-place page](https://www.city.edogawa.tokyo.jp/senkyo/data/togikai/basho.html) still identifies `旧下小岩小学校` as a polling site at the older address. **Election polling roles do not imply water-disaster or GSI designations**.

**Required boundary:** A/C must approve individual source rows with precise original evidence and temporal scope before any physical-site join. Municipal `水害時待避施設`, `municipal_locations`, an election site and GSI `skhb01` are separate source categories. A `fire.png` icon or blank hazard icon is not an inferred flood eligibility verdict. Never infer whether a site is currently open or safe.

## 3. Human review decision record — leave unsigned until actual review

This template is a review request, **NOT AI-completed approval**. Human reviewers must use immutable primary source evidence, not inferred matches.

| Decision ID | Human reviewer must resolve | Current disposition |
|---|---|---|
| A-01 | Source URLs, publisher, capture provenance, scope, original-page date context and effective-date provenance for **each of seven** source keys; reuse terms where supported | `UNREVIEWED` |
| A-02 | School campus **April 2025** operational context versus original publication date and water-facility designation; no relabelling of historic polling place | `UNREVIEWED` |
| C-01 | Tokyo Kasaikoka meta-date-only diff and validity of publisher/version interpretation; changed source must not self-approve | `UNREVIEWED` |
| C-02 | Current vs old Shimo-Koiwa physical site identity by separate rows and addresses; identify any unresolved cross-source conflict | `UNREVIEWED` |
| C-03 | Distinct semantics for municipal water facilities, location CSV, GSI `skhb01`, and Niigata/Nagoya original-data meanings before any D promotion | `UNREVIEWED` |

Human review record must specify **reviewer name or stable team identity**, review UTC timestamp, exact source URLs/source-key and SHA references, **decision per specific assertion**, basis and limitations, approved/held status, and any targeted same-site mapping (if expressly justified). Do not convert a blanket checkbox or an AI-generated note into source-wide approval. If unavailable or ambiguous, retain `null`, `UNKNOWN`, `UNVERIFIED`.

## 4. Gate state and reproducible next step

| Gate | Verdict |
|---|---|
| Two real HTTPS captures + original integrity and content shape | **PASS** |
| Actual upstream C comparator and produced formal JSON | **PASS (operator-reported execution; independent raw/report/receipt consistency PASS)** |
| A source version/date/reuse review | **PENDING** |
| C physical-site identity and source-category semantic review | **PENDING** |
| Human-approved cross-source site joins | **0** |
| New flood classifications from this comparison | **0** |
| D #266 three-region replay on A/C accepted pinned snapshot | **NOT RUN / HOLD** |
| Latest flooding/live opening/route safety assurance | **NOT EVALUATED** |

The next decision owner should record **specific human A/C signoffs** against A #264 and C #265, preserving their limits. Only then plan D #266 in a nondeployment environment: pin accepted official raw snapshots, run `pipeline/run_all_workflows.py`, `pipeline/verify_d_mvp.py` and `pipeline/verify_a_handoff_integration.py`, compare counts/status/evidence/contract to baseline without treating 152/566/1602 as fixed, and request C independent source→export audit. **Do not silently apply the 7-source C review as a new D production input**.
