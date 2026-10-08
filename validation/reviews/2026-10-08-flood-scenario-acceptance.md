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
- The first C-owned independent raw audit was executed in the user's environment on 2026-10-08. **Edogawa's UNKNOWN boundary and all 566 Niigata raw CSV marker/row comparisons passed.** Nagoya stopped at `千種区.xls:7 facility name/raw-row mismatch`, before full Nagoya completion. This is a PARTIAL C acceptance, not a green result.
- Source page checks performed by C: 新潟市 official open-data page lists 指定緊急避難場所一覧 CSV updated **2026-09-25**; 名古屋市 current designation page updated **2026-10-07**, with official indoor/outdoor listing reference date **2026-09-01**.
  - https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/
  - https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html
- C did **not** obtain and independently inspect all the source CSV/Excel bytes in this review session. The facility-level raw marker distribution (especially Niigata) remains unverified until the independent check below is run.

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
- Expected: Separately confirm the **official semantic meaning** of `○`, `×`, `2階以上`, `3階以上`, `全階可`, `－` and whether D's `CANDIDATE/EXCLUDED/UNKNOWN` statuses correctly respect conditional floor constraints. Do not infer official semantics solely from the mapping implemented by D.
- C action: raw histogram and D row mapping are confirmed. The remaining action is **independent official semantic verification**. If the value-to-status mapping is unsupported, return a D correction request with source-row evidence.
- Status: raw-value/row matching **PASS**; official symbol/floor-constraint semantics **PENDING**, not a proven functional error.

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

**C-FLOOD-06 — MEDIUM — C Nagoya audit normalizer inconsistency (fix committed; re-run required)**

- First C run failed at `千種区.xls:7 facility name/raw-row mismatch`.
- The C comparator originally used `str(value).strip()` whereas the D Nagoya Adapter's documented `_optional_string` uses `re.sub(r"\\s+", "", str(value)).strip()` — it removes internal ASCII/full-width whitespace too.
- A comparison of displayed original Excel text with a whitespace-normalized D field can therefore fail even when both refer to the same official value. The code review identifies a **plausible C false positive**; the original failing cell has not been inspected here, so an actual D mismatch is **not ruled out** until the next run.
- The C script now compares raw cells after **whitespace removal only** (no name substitutions or fuzzy match), and prints the exact raw/normalized/output values if a substantive mismatch persists.
- Added deterministic C regression covering whitespace-only equivalence and intentionally wrong facility names. **Regression execution pending on user's local environment.**

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

**Execution status (first run): PARTIAL / FAILED**. Edogawa and all 566 Niigata raw CSV row/marker comparisons passed. Nagoya stopped at `千種区.xls:7 facility name/raw-row mismatch`; the C comparison-normalization fix is committed, but **fresh C regression/official workbook rerun has not yet been reported**.

## 4. C acceptance decision

| Gate | Result |
| --- | --- |
| D logic deterministic CI | PASS (run #101) |
| D user-local live workflow and smoke verification | PASS (user-submitted output; not independently re-executed) |
| Legacy 0/null, status and 3-region score continuity | PASS on submitted D output; code reviewed |
| Safe treatment of Edogawa uncertain join | PASS for UNKNOWN boundary; facility Evidence trace incomplete |
| Nagoya combined-scope meaning and indoor limit | PASS for output boundary; official date refresh open |
| Niigata raw marker-to-status independent audit | **PASS for all 566 raw rows; official meaning pending** |
| C-owned automated raw-row audit | **PARTIAL: Edogawa/Niigata pass; Nagoya failure under re-investigation** |
| Scenario UI and GIS E2E | NOT IMPLEMENTED / NOT RUN |
| Independent human review | NOT RUN |

**Verdict:** Retain #41 inside `role/d-pipeline`. No unconditional C acceptance and no `main` merge until the C Nagoya rerun, official Niigata marker semantics, and Merge Captain contract/dependency decision are complete. Other items can be triaged into bounded follow-up PRs.

## 5. Suggested next actions

1. Rerun the corrected C independent raw-row check and its new whitespace-only regression; verify Nagoya all 16 official workbooks. Capture any substantive raw mismatch from the improved diagnostic.
2. Return C-FLOOD-03 to A for fresh metadata/source reference verification.
3. Review C-FLOOD-04 with the owner of shared RegionExport contracts before B/E consumer rollout.
4. Merge D into main only after acceptance requirements are satisfied, and then implement B/E consumers and run cross-layer E2E in Staging. C-FLOOD-02 remains explicitly documented if partial Edogawa trace is accepted for MVP.
