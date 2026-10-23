# Flood RegionExport consistency preflight — #301 / depends on #302

## Purpose and source of truth

The existing `RegionExport.scenarios[]` remains the sole D-to-B/E output contract. This standalone D-area preflight consumes **immutable exported JSON bytes** and a *separately supplied* pin manifest. It calls the exact existing Scenario models and the read-only `select_flood_scenario()` from #302; it does not export additional status fields, or provide a browser API.

This is a **snapshot consistency** check only. It is not independent original-document content review, verified raw SHA, historical PDF differencing, official source freshness, municipal flood legend acceptance, C source approval, accepted facility coordinates, current opening status, safety, or publication clearance.

## Current semantics gate

As of 2026-10-23, no municipality's flood-only eligibility interpretation has been certified in the current D Scenario evaluator. **All statuses must remain UNKNOWN**. Any facility CANDIDATE / EXCLUDED or non-UNKNOWN overall Scenario status in the saved export blocks this preflight, even if the user-supplied URL pins and snapshot digest match. This prevents accidental or malicious positive promotion while official symbol and joined source meaning approvals remain unfinished. Only separately reviewed future D/C source-semantics work can change this rule.

## Manual external pin manifest (local-only, not generated from ScenarioResult)

The JSON below is a **shape example**, NOT an approved municipal manifest:

```json
{
  "region_code": "15100",
  "export_sha256": "<64-character-lowercase-digest-of-existing-RegionExport-file>",
  "scenario_evaluated_at": "<existing-ScenarioResult-evaluated_at-with-timezone>",
  "source_urls_by_facility": {
    "<existing-facility-id>": "https://example.test/official-record.csv"
  },
  "review_reference": "SYNTHETIC_EXAMPLE_NOT_APPROVED"
}
```

Supply **every exact facility ID** and source URL from the separately reviewed source archive/ledger. The manifest must not be assembled merely by copying the untrusted URL map from the Scenario output. `review_reference` records an external ledger identifier, **not** proof that the review happened. A source URL's equality does not prove that its bytes, current update, interpretation or physical facility identity have been approved. A SHA256 of exported JSON pins the computation snapshot, **not** the official source.

Do not commit real-data artifacts, review documents with personal information, or generated pin files.

## Run

```bash
cd pipeline
python audit_flood_export_selection.py \
  --export data/output/niigata.json \
  --pins /secure/manual/niigata_source_pins.json
```

Missing or mismatched pins / missing Scenario / an unexpected positive classification cause exit 2 and `BLOCKED`. Successful output is explicit: `SNAPSHOT_CONSISTENCY_ONLY`, `publication_authorized=false`, and all official acceptance/freshness/location/safety fields `NOT_ESTABLISHED`. No files are modified. Without a human-prepared independent pin manifest, **do not fake one to make the command pass**; leave this gate blocked.

## Follow-up contract boundary

E PR #303 currently renders D statuses from the existing `RegionExport` with caveats; it **does not call this preflight** and must not claim a passing preflight, URL authenticity or C certification. To make this a public acceptance gate in the future, obtain the A/C independent source/byte identity approval, decide an explicit reviewed provider interface, and separately review any shared contract change before implementing consumer-side indicators. In the meantime E can display UNKNOWN and raw facts as unapproved research information.

Tests: `cd pipeline && python -m unittest tests/test_flood_export_preflight.py -v` plus entire pipeline suite and D-MVP acceptance when actual outputs are present. No live fetch, user device or real municipal dataset changes here.
