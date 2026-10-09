# C independent GSI flood designated emergency place audit

2026-10-09. Scope: validation only. Depends on A #62 and D #63.

This checker compares each original, locally archived GSI flood GeoJSON skhb01 feature with the corresponding D normalized record. It never imports the D algorithm. It checks the original GeoJSON Point [longitude, latitude], source properties name/address/remarks/disaster1 integer 1, SHA-256, exact trace feature_index, the GSI HTTPS tile URL, and the exact 1:1 record set.

Invocation after official source acquisition and D raw normalization:

PowerShell from repository root:

    & 'C:\HINANEX\pipeline\.venv\Scripts\python.exe' .\validation\validation\verify_gsi_flood_source.py --region 13123 --raw .\pipeline\data\raw\gsi_flood_tile.geojson --source-url 'https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson' --records .\pipeline\data\verified\edogawa_gsi_flood_records.json --acceptance-out .\pipeline\data\verified\edogawa_gsi_flood_c_acceptance.json

The example tile coordinates above DO NOT certify any site count or municipal coverage. A real downloaded tile and raw archive are required. Do not produce reference candidates using synthetic fixtures.

Expected C output is an audit object with PASS, source SHA256, search context region, dataset GSI_SKHB01_FLOOD, audit reference, and accepted source feature keys. Do not confuse audit PASS with real-world safety, current opening, optimal destination, or municipality membership. The input bytes' official download provenance must be documented independently; this validator cannot attest network origin. Municipal data can be stale or incomplete. Edogawa wide-area evacuation guidance takes precedence over any apparent proximity.

Tests:

    python -m unittest discover -s validation/validation -p "test_gsi_flood_source.py" -v

Test fixtures are synthetic. Re-run against official archived raw before publishing or claiming functional acceptance.
