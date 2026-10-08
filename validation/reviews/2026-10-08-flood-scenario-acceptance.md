# C Acceptance Review — Flood Shelter Selection (D PR #41)

- Review date: **2026-10-08**
- Reviewer: C validation undertaken in ChatGPT after the assigned C workflow was inactive. **The same assistant previously implemented D; this is a separate validation pass, not an independent human/auditor sign-off.**
- Reviewed provider: [D PR #41](https://github.com/1kz-ma1/HINANEX/pull/41), merged into `role/d-pipeline`; reviewed head `91ef16938821784ef69ffe58105378547e591dbf`.
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
- C action: raw histogram and D row mapping are confirmed. **The 173 `2階以上`, 9 `3階以上`, and 74 `全階可` cases (256 in total) currently all appear as UNKNOWN**. Ask A to verify these markers against the *current* ODS source/legend, then ask D to formally design conditional usability representation (preserve required floor / all-floor fact and display conditions), without silently converting these to unrestricted CANDIDATE or a safety guarantee. Clarify the scope of `×` and `－` from the authoritative legend before committing exclusion semantics.
- Status: raw-value/row matching **PASS**; **potential functional under-classification now evidenced for floor-limited facilities**, pending authoritative 2026 semantics and explicit D Contract decision. **Unconditional `main` acceptance remains blocked.**

**C-FLOOD-02 — MEDIUM — Edogawa raw facility Evidence not yet materialized**

- Source: A handoff reports a separate water-disaster HTML table and only PARTIAL joinability. D `edogawa_facts()` produces one placeholder UNVERIFIED fact per location, all source_record_trace=null.
- Actual: 152 UNKNOWN, with links to the general official hazard page but **no per-facility hazard page row**.
- Expected for a fuller Scenario vertical slice: distinct extracted official row and trace, verified join only when justified; otherwise UNKNOWN. Never turn water-disaster waiting-facility facts into a flood-only designation.
- Status: **KNOWN LIMITATION**, safe fail-closed behavior for now; not a basis for claiming complete row-level Source→Scenario tracing.

**C-FLOOD-03 — MEDIUM — A metadata on Nagoya is stale**

- Source: A handoff currently records updated_at 2026-07-27 and reference date 2026-07-01, whereas the official webpage currently shows updated 2026-10-07 and as-of 2026-09-01.
- Expected: A updates metadata and verifies whether associated workbook contents/scope actually changed. Do not fabricate a dataset difference merely from page date changes.
- Status: **A return item**, not D-owned.

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
- Added deterministic C regression covering whitespace-only equivalence and intentionally wrong facility names. **Its separate unittest execution has not been reported** (the successful user log covers only the independent raw-row audit).

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

**Execution status (re-run): PASS** — user provided the final transcript: `edogawa records: 152`, `niigata records: 566`, `Nagoya indoor workbooks independently traced: 16`, `nagoya records: 1602`, ending in `C raw trace acceptance: checks PASSED (official semantics remain separate review gate)`. The C regression unittest remains **not reported**, and source semantics remain a **separate acceptance gate**.

## 4. C acceptance decision

| Gate | Result |
| --- | --- |
| D logic deterministic CI | PASS (run #101) |
| D user-local live workflow and smoke verification | PASS (user-submitted output; not independently re-executed) |
| Legacy 0/null, status and 3-region score continuity | PASS on submitted D output; code reviewed |
| Safe treatment of Edogawa uncertain join | PASS for UNKNOWN boundary; facility Evidence trace incomplete |
| Nagoya combined-scope meaning and indoor limit | PASS for output boundary; official date refresh open |
| Niigata raw marker-to-status independent audit | **PASS: 566/566 raw rows and values; conditional flood usability meaning still pending** |
| C-owned automated raw-row audit | **PASS for 3 regions; 16 Nagoya indoor workbooks, 1,602 rows** |
| Scenario UI and GIS E2E | NOT IMPLEMENTED / NOT RUN |
| Independent human review | NOT RUN |

**Verdict:** C's independent **raw-trace verification PASSED**, but formal Scenario acceptance is **CONDITIONAL / NEEDS_REVIEW**. Retain #41 inside `role/d-pipeline`; do not merge to `main` before the Niigata conditional-floors semantic/Contract decision, A source refresh where needed, and Merge Captain integration review. B/E consumer E2E remains a later cross-layer gate.

## 5. Suggested next actions

1. Confirm `2階以上`/`3階以上`/`全階可`/`×`/`－` semantics for the **current** Niigata CSV against city-issued legends; resolve C-FLOOD-01 with A/D. Run the separate C synthetic workbook regression unittest before marking #42 complete.
2. Return C-FLOOD-03 to A for fresh metadata/source reference verification.
3. Review C-FLOOD-04 with the owner of shared RegionExport contracts before B/E consumer rollout.
4. Merge D into main only after acceptance requirements are satisfied, and then implement B/E consumers and run cross-layer E2E in Staging. C-FLOOD-02 remains explicitly documented if partial Edogawa trace is accepted for MVP.
