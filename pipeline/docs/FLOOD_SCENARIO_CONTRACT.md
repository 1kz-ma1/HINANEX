# D / Flood Shelter Selection — additive Scenario contract (v0.9 compatible)

## Status

This is a D-owned, formal **Scenario-local** requirement `shelter_hazard_applicability`, adopted from the A proposal in PR #37. It does **not** alter the established `shelter_location` requirement or the existing `shelter_discovery` scoring engine.

The optional `RegionExport.scenarios[]` field is additive; it defaults to an empty array and legacy required fields and `meta.schema_version=0.9` remain unchanged. Old consumers should ignore the new field until they explicitly opt in. Consumer contract support must be reviewed before using strict additionalProperties:false validators compiled against the prior schema.

Scenario: `flood_shelter_selection` / 洪水時の避難候補探索.

## Workflow

Run `python run_all_workflows.py` from `pipeline/`, then `python verify_flood_scenario.py` to check all three exported scenario contracts and their safety boundaries. The three old municipal workflows archive the exact official CSV/Excel inputs first. The new `run_flood_scenario.py` reads **those same archived bytes** and existing `data/normalized/*_shelters.json` files, then produces:

- `data/normalized/edogawa_flood_scenario.json`
- `data/normalized/niigata_flood_scenario.json`
- `data/normalized/nagoya_flood_scenario.json`

`build_region_contracts.py` includes each result as `scenarios[0]` in `data/output/{region}.json`.

The new optional field has no effect on legacy `datasets/assessments/capabilities/gaps/recommendations` or their `meta` counts. Scenario-local `requirement_assessment`, `status`, `gaps` and `recommendations` must not be mistaken for legacy 0–4 quality scores or existing `Shelter Discovery` Gap/Recommendation.

## Result shape

```text
scenarios[0]
  scenario_id = flood_shelter_selection
  requirement_assessment
    requirement_code = shelter_hazard_applicability
    discovery_status
    record_count / directly_joined_count / raw_value_count / reason
  status = FULL | DEGRADED | UNKNOWN
  facility_results[]
    facility_id (exact match to datasets[shelter_location].records[].id)
    status = CANDIDATE | EXCLUDED | UNKNOWN
    reason
    fact
      facility_id / facility_name
      hazard_scope_raw / source_semantics
      official_status_raw / usable_floor_raw
      source_url / source_record_trace
      join_status
      latitude / longitude
  reasons[] / gaps[] / recommendations[]
```

`CANDIDATE` and `EXCLUDED` remain **reserved status values** for future evidence-approved decisions. No current Niigata ODS `災害種別_洪水` marker has an authoritative column-specific value mapping accepted by A/C. Therefore **all existing Niigata facilities are `UNKNOWN` regardless of `○`, `×`, `－`, or floor condition**. Raw values, coordinates and original row traces remain available, but are not eligibility/safety decisions.

`UNKNOWN` is mandatory when raw value is absent/unrecognized, a facility join is unverified, the source's hazard scope is not flood-only, or required position information is missing. In particular `UNKNOWN` **must never** be silently converted to `EXCLUDED`.

### Niigata floor-condition evidence — A #43 / D follow-up

A's 2026-10-08 re-verification distinguishes the **official 2026-03 river-specific flood hazard-map legend** from the current ODS CSV's `災害種別_洪水` column. The map explains `全階可`, `○階以上`, and the river-conditional `－` notation, but **there is no verified one-to-one official mapping for every ODS CSV marker**. The city's PDF uses `○/×` for other hazard columns as well; their meanings must not be transferred to this flood CSV automatically.

D now populates the **existing, optional** `facility_results[].fact.usable_floor_raw` from the same official CSV row, only when its `official_status_raw` is exactly `2階以上`, `3階以上`, or `全階可`. These are raw textual floor constraints, **not** a decoded number, verified designation, guaranteed opening, or unrestricted safe candidate. The `official_status_raw` remains unchanged; `source_record_trace` and `source_url` identify the archived CSV row and Source. The `usable_floor_raw` field also remains available for Nagoya's combined-hazard scope as before.

- This is a **data-preservation change only**. The three markers remain `UNKNOWN`, with a reason explaining that the ODS semantics and conditional eligibility are not yet formally approved.
- **Fail-closed update / Issue #48:** The previous provisional D `○` → `CANDIDATE` and `×` → `EXCLUDED` mapping is now suspended. The current ODS has no verified municipality-specific official value dictionary for the exact flood column; all raw values remain intact and all Niigata statuses stay `UNKNOWN`. B/E must not infer flood designation, availability, or exclusion from `○/×/－`.
- The independent C raw audit dated 2026-10-08 reported six marker classes, `○=16 / ×=239 / 2階以上=173 / 3階以上=9 / 全階可=74 / －=55` in 566 official CSV rows. These counts are a **historical audit snapshot**, not permanent constants in code.
- Confirm the official meanings of the current ODS `○`, `×`, `－`, and floor-valued cells with A/C before expanding the `CANDIDATE/EXCLUDED` mapping. Future conditional-candidate UI/contract changes need a separate explicit review.
- The `RegionExport.scenarios[]` shape, optional `HazardFact.usable_floor_raw` field, version `0.9`, old `shelter_discovery` results and legacy counts are unchanged.

A Evidence: `data-research/scenarios/2026-10-08-flood-source-reverification.md` in `role/a-data`; C Audit: `validation/reviews/2026-10-08-flood-scenario-acceptance.md` in `feature/c-flood-scenario-acceptance`.

## Municipality rules

| Area | Source and join | Facility-level evaluation |
|---|---|---|
| Edogawa | A identified official water-disaster waiting facilities; no common ID with existing shelter_location. `UNVERIFIED`; the A page is a separate Source. | All existing location records stay `UNKNOWN` until an independently verified row-level join is established. Never match fuzzy names automatically or equate `水害` with flood-only designation. This iteration does not claim to have parsed the page's HTML table into per-facility facts. |
| Niigata | Same official ODS CSV raw row. `DIRECT_SAME_SOURCE` with precisely reconstructed facility ID; `csv_row` trace. | All markers, including `○`, `×` and `－`, remain `UNKNOWN` while the official ODS column-specific dictionary is unavailable. `2階以上` / `3階以上` / `全階可` are separately preserved in `usable_floor_raw`. The original Source value is preserved verbatim. |
| Nagoya | Same official 16-ward indoor Excel raw row and same composite ID. `DIRECT_SAME_SOURCE` with workbook/row trace. | The official `洪水・内水` column is inseparable at source level. Preserve `○ / × / － / 階数` verbatim and never manufacture two independent flood/inland outcomes; current flood-only Scenario result is `UNKNOWN`. No inferred coordinates. Outdoor facilities are outside the current dataset. |

If an exact same-source record ID mismatch occurs, the build **fails closed**. Repeated automatic similarity matching and inferred geocoding are prohibited.

## D→B/E/C handoff

- B/E consume D's Scenario status and source facts; **do not** reclassify raw markers or combine GIS raster colors with facility points to invent hazard decisions.
- E can display `fact.latitude/longitude` only if present; explain missing geometry and `UNKNOWN` plainly.
- C verifies `Official Source → archived raw row → HazardFact → requirement_assessment → ScenarioResult` and compares facility IDs to the existing location records. Unit tests verify positive/negative/unknown boundaries, unsafe joins, and combined hazard scopes.
- A PR #43 refreshed Nagoya page update (2026-10-07) and list reference date (2026-09-01); underlying historical workbook diff is not verified. D does not silently rewrite A Evidence.
- Live re-fetch/recount and Render E2E are separate acceptance gates after CI.

## Contract impact

**Additive only**. The new `scenarios` property is optional. `shelter_location`, legacy score semantics (`0 != null`), `NOT_FOUND`, capability engine, RegionExport's required top-level keys, and `meta` counts are unchanged. Consumer opt-in and a future explicit version negotiation can be handled as a coordinated Shared Contract release, rather than silently breaking current `meta.schema_version=0.9` clients.


## Fail-closed ODS status mapping — 2026-10-08

Until [Issue #48](https://github.com/1kz-ma1/HINANEX/issues/48) has an authoritative, source-specific Niigata city interpretation of the **`災害種別_洪水` CSV column**, there is **no approved positive or negative set**. Every Niigata facility reports `facility_results[].status=UNKNOWN` even when its official raw cell is `○` or `×`. The overall Scenario status is `UNKNOWN`, while `requirement_assessment.discovery_status=AVAILABLE` still indicates that all original rows were actually ingested. This is deliberate: **raw data availability is not semantic eligibility**.

Old historical counts (16 CANDIDATE/239 EXCLUDED) refer exclusively to the pre-fix build and must not be presented as current output or as official designation facts. No `RegionExport` schema modification, geocoding, or old `shelter_discovery` scoring changes are made. A future status policy requires explicit A Evidence, D contract review, C regression, and Merge Captain sign-off.
