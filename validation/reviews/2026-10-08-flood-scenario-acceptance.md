# C Acceptance Review — Flood Shelter Selection (D PR #41)

- Review date: **2026-10-08**
- Reviewer: C validation undertaken in ChatGPT after the assigned C workflow was inactive. **The same assistant previously implemented D; this is a separate validation pass, not an independent human/auditor sign-off.**
- Reviewed provider: [D PR #41](https://github.com/1kz-ma1/HINANEX/pull/41) (original Scenario), and [D PR #44](https://github.com/1kz-ma1/HINANEX/pull/44) (Niigata floor-raw preservation), both merged to `role/d-pipeline`. Latest C report is based on the user's post-#44 independent audit log.
- A source: [PR #37](https://github.com/1kz-ma1/HINANEX/pull/37), `data-research/scenarios/flood-shelter-selection.md`, `data-research/handoff/HINANEX_A_flood_scenario_handoff.json`.
- Target: `flood_shelter_selection`, Scenario-local `shelter_hazard_applicability`, optional `RegionExport.scenarios[]`.
- **Disposition: CONDITIONAL / NEEDS_REVIEW — NOT YET ACCEPTED FOR MAIN.**
- No modifications to `pipeline/**` made by C. This review is separate from the D implementation branch.

## 1. Evidence classes: do not conflate

**Observed from user-run output (not independently re-executed by C):**

| Region | Legacy location | Scenario result | CANDIDATE | EXCLUDED | UNKNOWN |
| --- | --- | --- | ---: | ---: | ---: |
| 江戸川区 (13123) | 152 / FULL / Gap 0 | UNKNOWN | 0 | 0 | 152 |
| 新潟市 (15100) | 566 / FULL / Gap 0 | DEGRADED | 16 | 239 | 311 |
| 名古屋市 (23100) | 1602 / BLOCKED / Gap 1 | UNKNOWN | 0 | 0 | 1602 |

- User ran `run_all_workflows.py`, `verify_d_mvp.py`, `verify_a_handoff_integration.py`, `verify_flood_scenario.py`; pasted logs end in READY/COMPLETE.
- D PR #41 GitHub Actions run #101 passed. D reported 56 pipeline tests and 3 deploy tests, Scope Guard, generated Schema check.
- The corrected C-owned independent raw audit was re-executed by the user on 2026-10-08 and **PASSED for all three regions**. Edogawa: 152 UNKNOWN / UNVERIFIED as documented; Niigata: all 566 archived official CSV rows and raw markers trace; Nagoya: all 16 indoor Excel files and 1,602 facility facts traced, all UNKNOWN. The preceding `千種区.xls:7` false-positive comparison failure is resolved after whitespace-equivalent C audit logic. This is a **raw-trace pass**, not unconditional Scenario semantic acceptance.
- Source page checks performed by C: 新潟市 official open-data page lists 指定緊急避難場所一覧 CSV updated **2026-09-25**; 名古屋市 current designation page updated **2026-10-07**, with official indoor/outdoor listing reference date **2026-09-01**.
  - https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/
  - https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html
- C's independently coded local script consumed the user's saved official CSV/Excel archives and completed raw-row comparison for the entire dataset. The assistant has not received copies of the underlying archives and has not independently re-downloaded every row; the user-provided audit transcript is the execution evidence. **Official meaning of marker values is evaluated separately below.**

## 2. Contract and semantic findings

### Confirmed by code/source inspection

1. **Preserved**: Old `shelter_location` normalization, 0 vs null score semantics, `shelter_discovery` logic and old `meta` counts were not changed by this Scenario evaluator. RegionExport introduces only an optional `scenarios[]` property.
2. **Preserved**: Edogawa's `水害` source is not renamed as a flood-only designation. All 152 location records are reported UNKNOWN, with UNVERIFIED joins; no fuzzy-name match or invented geocoordinates.
3. **Preserved**: Niigata uses the same archived official CSV as the legacy location adapter and reconstructs the facility ID from its original raw row.
4. **Preserved**: Nagoya extracts the original `洪水・内水` combined column from the same indoor Excel workbook/row, keeps raw `○/×/－/階数` text, and does not split it into independent flood/inland decisions. 16-ward indoor-only scope is respected.
5. **Preserved**: D's verifier requires exact scenario-to-location ID sets and rejects unverified joins / combined hazards classified as flood-only results. This is a code-path safety guard; its factual correctness still depends on the archived Source.
6. **Preserved with compatibility caveat**: `RegionExport.scenarios[]` is additive. Legacy B/E JavaScript appears to ignore unknown fields but strict consumers compiled against the old JSON schema may still reject a v0.9 payload with new properties.

### C return items / residual risk

**C-FLOOD-01 — HIGH — raw markers matched, official marker meaning still needs source confirmation (blocks unconditional acceptance)**

- Source: A scenario handoff acknowledges that Niigata's current CSV raw-value distribution was **not independently re-counted** by A.
- Actual D output: Niigata 16 CANDIDATE, **239 EXCLUDED**, 311 UNKNOWN. C independently compared all 566 result entries against the archived official CSV, including marker values, facility names, row references, source URLs and status categories; this part **PASSED**. Raw histogram: `○=16`, `×=239`, `2階以上=173`, `3階以上=9`, `全階可=74`, `－=55`.
- New official-source finding: Niigata City directly states in its 2022 Konan Ward official article that flood evacuation facilities marked **`2階以上`** or **`全階可`** can be used for flood evacuation, with restrictions on usable floors. This supports treating these markers as **meaningful floor-dependent usability facts**, rather than as uninformative unknown strings. Current 2026 CSV marker definitions, the `3階以上` marker, `○`, `×`, and `－` still require source-specific semantic confirmation before changing D status mapping. Official city source: https://www.city.niigata.lg.jp/konan/kohoshi/kuyakusho/r04/konan_365/konan_365_1.html (section Check2).
- C action: raw histogram and D row mapping are confirmed. A #43 documented the 2026 official river-specific flood legend and emphasized it is **not a confirmed complete mapping for the ODS CSV field**. D #44 now preserves **all 256 official raw floor-constraint strings** (173 `2階以上`, 9 `3階以上`, 74 `全階可`) in optional `usable_floor_raw`, while retaining `UNKNOWN`. The user's latest C audit verified **256/256** against archived CSV raw rows. This resolves the **raw preservation** subtask, not the official ODS-specific semantics for `○/×/－` or conditional eligibility. B/E must never silently upgrade statuses.
- Status: raw-value/row matching **PASS after D #44**; floor condition preservation **PASS (256 entries)**; ODS-specific eligibility/exclusion semantics **PENDING**, hence **unconditional `main` acceptance remains blocked**. Do not present current UNKNOWN as lack of any original source floor condition.

**C-FLOOD-02 — MEDIUM — Edogawa raw facility Evidence not yet materialized**

- Source: A handoff reports a separate water-disaster HTML table and only PARTIAL joinability. D `edogawa_facts()` produces one placeholder UNVERIFIED fact per location, all source_record_trace=null.
- Actual: 152 UNKNOWN, with links to the general official hazard page but **no per-facility hazard page row**.
- Expected for a fuller Scenario vertical slice: distinct extracted official row and trace, verified join only when justified; otherwise UNKNOWN. Never turn water-disaster waiting-facility facts into a flood-only designation.
- Status: **KNOWN LIMITATION**, safe fail-closed behavior for now; not a basis for claiming complete row-level Source→Scenario tracing.

**C-FLOOD-03 — MEDIUM — A metadata on Nagoya is stale**

- Source: The *original* A #37 handoff recorded updated_at 2026-07-27 and reference date 2026-07-01; the official site later showed updated 2026-10-07 and list as of 2026-09-01.
- Resolution: A [PR #43](https://github.com/1kz-ma1/HINANEX/pull/43) refreshed both dates in the A report and structured handoff and merged into `role/a-data`.
- Status: **RESOLVED (metadata)**. Historical workbook content/difference verification remains **NOT RUN**; current 16 indoor workbook raw trace was independently checked by C.

**C-FLOOD-04 — MEDIUM — formal Requirement/Capability trace terminology**

- The new Requirement is defined as a **Scenario-local** `DataRequirement` and a `ScenarioRequirementAssessment`. It is **not** added as a second `NormalizedDataset`/`DatasetAssessment` in the legacy arrays; Scenario-local `gaps/recommendations` are strings rather than existing Gap/Recommendation records.
- This differs from the complete legacy `Source→Evidence→Normalized Record→DatasetAssessment→CapabilityAssessment→Gap→Recommendation` trace initially envisioned. It is not necessarily invalid, but B/C/E must explicitly accept this alternative contract and never present Scenario-local status as the legacy 0–4 capability score.
- Status: **CONTRACT DECISION REQUIRED** before declaring the full multi-consumer milestone complete.

**C-FLOOD-05 — MEDIUM — new consumer E2E not yet tested**

- B and E have not implemented the new Scenario UI/map. Current Staging points to `main` which does not yet contain D's role-branch Scenario changes.
- Expected: after provider integration and consumer work, verify `UNKNOWN` is visible; map hides no missing-coordinate records without explanation; no own hazard evaluation in B/E; no claim of safe shelter or route.
- Status: **PENDING**, integration-stage item.

**C-FLOOD-06 — RESOLVED — C Nagoya audit normalizer mismatch**

- First C run failed at `千種区.xls:7 facility name/raw-row mismatch`.
- The C comparator originally used `str(value).strip()` whereas the D Nagoya Adapter's documented `_optional_string` uses `re.sub(r"\\s+", "", str(value)).strip()` — it removes internal ASCII/full-width whitespace too.
- C's first raw-vs-normalized text comparison could fail on legitimate internal whitespace. After normalizing **whitespace only**, the user re-ran the official-archive audit and all 16 Nagoya workbooks / 1,602 records passed. This provides execution evidence that the first mismatch was a C comparator mismatch, not a confirmed D source-row error.
- The C script now compares raw cells after **whitespace removal only** (no name substitutions or fuzzy match), and prints the exact raw/normalized/output values if a substantive mismatch persists.
- Added deterministic C regression covering whitespace-only equivalence and intentionally wrong facility names. **User confirmed the corrected six-test standalone C suite passed** after the Windows CSV fixture fix (2026-10-08).

## 3. Additional independent acceptance check

C-owned script:
```powershell
cd C:\HINANEX
# after run_all_workflows.py on D branch:
py -3.12 validation/validation/verify_flood_scenario_acceptance.py
```

The script is separate from D's own tests and implements the following:

- Reads exported JSON without importing D's models or evaluator.
- Verifies all three region identities, legacy `shelter_discovery` statuses, Requirement name, exact ID set and preservation of original latitude/longitude.
- Reads Niigata's archived official CSV with a standard-library CSV parser, verifies `official_status_raw`, facility names, physical row traces, source URLs, marker categories, and prints **raw-value histogram**.
- Reads each of Nagoya's 16 official indoor workbooks from the archived ZIP and independently checks workbook row/combined-hazard-column value, facility name, address, trace, Source URL, `UNKNOWN` status.
- Verifies Edogawa produces no unverified CANDIDATE/EXCLUDED and records lack official facility-level raw facts.
- Fails closed with actionable descriptions on mismatches.
- No per-facility CSV, XLS, address or personal data committed to Git.

**Execution status (after D #44): PASS** — user supplied the new independent audit transcript: Edogawa 152 UNKNOWN, Niigata 566 with `raw floor conditions independently verified: 256` and status 16 CANDIDATE / 239 EXCLUDED / 311 UNKNOWN, Nagoya 16 indoor XLS files / 1,602 UNKNOWN. Final line: `C raw trace acceptance: checks PASSED (official semantics remain separate review gate)`. Results are based on *user-run test output*, not a separate GitHub Actions live municipal ingestion. The newly added C synthetic unit tests were **not shown in the submitted log**.

## 4. C acceptance decision

| Gate | Result |
| --- | --- |
| D logic deterministic CI | PASS (run #101) |
| D user-local live workflow and smoke verification | PASS (user-submitted output; not independently re-executed) |
| Legacy 0/null, status and 3-region score continuity | PASS on submitted D output; code reviewed |
| Safe treatment of Edogawa uncertain join | PASS for UNKNOWN boundary; facility Evidence trace incomplete |
| Nagoya combined-scope meaning and indoor limit | PASS for output boundary; official date refresh open |
| Niigata raw marker-to-status independent audit | **PASS: 566/566 raw rows and values; conditional flood usability meaning still pending** |
| C-owned automated raw-row audit | **PASS after D #44** — 3 regions, Niigata 256 raw floor fields verified, 16 Nagoya XLS workbooks |
| Scenario UI and GIS E2E | NOT IMPLEMENTED / NOT RUN |
| Independent human review | NOT RUN |

**Verdict:** C's independent **raw-trace verification PASSED**, but formal Scenario acceptance is **CONDITIONAL / NEEDS_REVIEW**. Retain #41 inside `role/d-pipeline`; do not merge to `main` before the Niigata conditional-floors semantic/Contract decision, A source refresh where needed, and Merge Captain integration review. B/E consumer E2E remains a later cross-layer gate.

## 5. Suggested next actions

1. D #44 raw-floor preservation is **verified by C**, and the standalone synthetic regression suite passed **6/6** on user rerun. Next confirm `○` / `×` / `－` and conditional-floor meaning for the **current** Niigata ODS CSV against an authoritative source-specific legend or publisher clarification, then review D status mapping.
2. C-FLOOD-03 Nagoya page/list metadata refreshed in A #43; **resolved**, with historical workbook differences still unverified.
3. Review C-FLOOD-04 with the owner of shared RegionExport contracts before B/E consumer rollout.
4. Merge D into main only after acceptance requirements are satisfied, and then implement B/E consumers and run cross-layer E2E in Staging. C-FLOOD-02 remains explicitly documented if partial Edogawa trace is accepted for MVP.

## 6. D #44 follow-up / revalidation (2026-10-08)

- [A PR #43](https://github.com/1kz-ma1/HINANEX/pull/43) merged into `role/a-data`, with official 2026-03 city flood-legend distinctions and updated Nagoya evidence dates. **ODS CSV-specific marker mapping still not established**.
- [D PR #44](https://github.com/1kz-ma1/HINANEX/pull/44) merged into `role/d-pipeline`, CI #110 SUCCESS. For Niigata `災害種別_洪水`, D now preserves `2階以上` / `3階以上` / `全階可` in the previously existing optional `fact.usable_floor_raw` while keeping their Scenario status `UNKNOWN`.
- The C independent validator now checks each Niigata CSV row's `usable_floor_raw` directly against the corresponding raw marker, and refuses premature eligibility classification. An unexpected new `N階以上` value fails closed pending D/A source review.
- Additional deterministic C synthetic CSV tests catch missing/altered floor values and status promotion. The user confirmed the corrected standalone suite **PASS (6/6)**; it remains outside the current GitHub workflow.
- **Revalidation completed (user-run)**: the latest submitted log confirms all three regions PASS, and **256 Niigata floor-raw conditions** matched source CSV. This replaces the earlier pre-#44 validation as the current execution evidence. The new C synthetic workbook/CSV unittest suite was later confirmed **PASS (6/6)** by the user after a test-fixture newline fix; the full latest terminal transcript was not pasted.
- **C semantics gate remains conditional**: `○/×/－` and floor meaning within the current ODS CSV still await authoritative A/D agreement; no `main` merge authorization here.

## 7. Post-#44 acceptance evidence and remaining gates (2026-10-08)

- **PASS / executed by user:** C independent official-archive/RegionExport verifier on post-#44 outputs, covering Edogawa 152 UNKNOWN, Niigata 566 official raw rows, and Nagoya 1,602 rows from 16 indoor Excel files.
- **PASS / executed by user:** all Niigata `usable_floor_raw` fields for 256 floor-marked official CSV rows agree with the original raw cells. All 256 remain `UNKNOWN`. No facility's eligibility or real-time availability was inferred from a floor condition.
- **PASS / GitHub:** D CI #110 after #44 and C PR CI #114; **GitHub CI does not execute C's standalone municipal raw verifier or new C synthetic tests**.
- **PASS (user-reported):** C standalone synthetic unittest suite `python -m unittest discover -s validation/validation -p "test_*.py" -v`, **6/6** after the Windows CSV fixture correction. The full passing terminal output was not pasted; prior failed output was recorded separately.
- **UNRESOLVED SEMANTICS:** official Niigata ODS-specific meaning for `○` / `×` / `－` and the exact relationship between the city's river-specific hazard legend and ODS CSV `災害種別_洪水`. A #43 documents relevant official flood legend while explicitly preserving this distinction. The C raw audit has *not* approved D's existing 16 CANDIDATE / 239 EXCLUDED labels as disaster-safety facts.
- **INTEGRATION:** the additive RegionExport `scenarios[]` field must be reviewed with B/E consumers; old schema 0.9 required fields are unchanged. B/E Staging E2E and Merge Captain's latest-main merge decision remain separate gates.

**Decision: C RAW-TRACE ACCEPTANCE = PASS after D #44. Full flood Scenario SEMANTIC/RELEASE ACCEPTANCE = CONDITIONAL / NEEDS_REVIEW. This record does not approve `main` merge.**

## 8. C synthetic unittest Windows CSV fixture correction (2026-10-08)

User executed `python -m unittest discover -s validation/validation -p "test_*.py" -v` after D #44:

- Total: **5 tests**. Nagoya whitespace normalization and mismatch rejection: **2 PASS**. Niigata synthetic regression: **1 ERROR, 2 FAIL**.
- All three Niigata reports trace back to the same first-row **`csv_row=2` versus physical line `3`** mismatch. The intended negative assertions were not reached.
- Root cause in C test-only fixture: `csv.writer(io.StringIO(newline=""))` emits CRLF, but `Path.write_text(..., encoding="utf-8-sig")` on Windows translates LF again, writing CRCRLF and shifting CSV reader physical line numbers. This is not evidence of a D raw adapter failure; the previously successful C real-archive audit remains valid.
- Fix in `validation/validation/test_flood_scenario_acceptance.py`: write the CSV via `write_bytes(data.getvalue().encode("utf-8-sig"))` to preserve `csv.writer`'s exact bytes. Added a fixture-specific cross-platform regression confirming physical row positions 2–7.
- **Verification status:** fixture fix committed, local re-run subsequently reported **PASS (6/6)** by the user. No substantive changes were made to the C official raw checker or D pipeline.

This does not change D or A code, RegionExport, the C production-independent raw audit checker, or any official data assumption. Semantic release acceptance remains conditional.

## 9. C standalone regression acceptance completed (2026-10-08)

After correcting the Windows test fixture's CRLF double-translation, the user reran:
```powershell
.\pipeline\.venv\Scripts\python.exe -m unittest discover -s validation/validation -p "test_*.py" -v
```
**User-confirmed result: all six tests OK.** The suite covers two Nagoya raw normalization/mismatch tests, three Niigata floor-raw fail-closed cases and one physical CSV-line-number regression. This is user-reported passing execution; a copy of the entire successful terminal output was not provided.

**C branch acceptance for the implemented D #44 raw-fact preservation and traceability: PASS.** The C PR may be merged **to `role/c-validation` only**. The broader flood Scenario release remains **CONDITIONAL / NEEDS_REVIEW**, specifically ODS-specific official marker semantics and B/E/Shared Contract integration; this does not authorize merging to `main` or declaring shelters safe.
