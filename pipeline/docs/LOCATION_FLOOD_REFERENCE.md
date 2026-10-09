# D: 位置指定 × 洪水指定緊急避難場所（10/22 MVP用、プレビュー段階）

## Purpose
現行の`shelter_location`を「災害時に安全な避難所」に変換せず、**国土地理院の洪水`skhb01`タイルに掲載された「指定緊急避難場所」** を別のSourceとして扱う準備をする。

- Dは候補の公式指定・出典を保持するだけ。「推奨」「安全」「開設中」「安全な経路」は判定しない。
- 江戸川区の水害時の広域避難方針を候補表示で打ち消さない。
- 既存`RegionExport` / `flood_shelter_selection`はそのまま。未確認`UNKNOWN`や`supported_disasters`から新しい候補を生成しない。
- 2026-10-09時点でGSI公式タイル1枚の原本とCの1,195行照合がユーザー環境でPASS済み。ただしこの数字はタイル全体の件数であり、江戸川区内の施設数ではない。HTTPS再取得・カタログ出力・ブラウザ受入は別途必要。

## Data gate

`src/hinanex/flood_site_reference.py` の `build_flood_site_catalog` は:

1. 入力rawバイトの SHA-256 とCの受入JSON `source_raw_sha256`を完全一致確認。
2. C独立受入の地域・Source識別`GSI_SKHB01_FLOOD`、`status=PASS`、受入ID集合を確認。
3. 各D整理レコードの公式ID/地域名/数値座標/Source URL/元feature trace/災害専用分類を型・範囲・重複含め検証。公式タイルURLは`https://cyberjapandata.gsi.go.jp/xyz/skhb01/{z}/{x}/{y}.geojson`だけ認める。
4. いずれかが欠ければ`BLOCKED_UNVERIFIED_SOURCE`で参照施設0件（もしくは不正な受入の際には例外）。評価不能を安全扱いに昇格しない。

**注意:** 「C PASS」という文字列だけでSourceが実際に検証済みになるわけではない。Cが元のGeoJSON feature内容と正規化レコードを独立に照合し、監査参照番号とSHAを作る作業が必須。Cによる監査の実行結果は別途受入ゲート。

## Standalone output (additive, not RegionExport schema)

```json
{
  "catalog_kind": "flood_designated_emergency_site_reference",
  "region_code": "13123",
  "hazard": "flood",
  "status": "BLOCKED_UNVERIFIED_SOURCE",
  "source_status": "NOT_ACCEPTED",
  "sites": [],
  "total_source_records": 0,
  "notice": "公式施設rowの独立監査が完了するまで候補非表示",
  "limitations": ["..."]
}
```

Cで受け入れた場合のみ`status=REFERENCE_ONLY`, `source_status=C_ACCEPTED`, `sites[]`にraw名称・緯度経度・source URL・source feature trace・元sha256等が入る。既存source施設との曖昧名称joinは禁止。

例（**Cのraw監査と独立HTTPS再取得MATCH後のみ実行**。すべてローカル成果物・Git管理外）:

```powershell
cd pipeline
python run_verified_flood_site_reference.py --region 13123 `
  --raw data/raw/gsi_flood_tile.geojson `
  --records data/verified/edogawa_gsi_flood_records.json `
  --c-acceptance data/verified/edogawa_gsi_flood_c_acceptance.json `
  --provenance data/verified/gsi_https_provenance_20261009.json `
  --out data/output/edogawa_flood_site_catalog.json
```

このCLIは存在しないSource/監査ファイルを自動生成しない。公式データのCSV/GeoJSON field-mapと地域限定の正しさをA/Cが確定するまで実データ発行はブロック。

## Dependency and deployment
- A Evidence: `data-research/scenarios/2026-10-09-location-flood-official-designations.md` / PR #62。
- C: **独立**raw検証（raw feature ID・元名・geometry・municipality codeを確認。監査ログ保存）。GSIが公開未掲載なら公式指定の不存在と断定しない。
- E: **手動地図クリック/ユーザー許可後GPS**で位置指定。端末の位置はサーバーに送信せず、受入サイトの直線距離のみ表示可能。距離順は「安全順」と表示しない。
- Browser: catalogファイルがない・`BLOCKED`なら「公式指定情報の照合待ち」と表示。従来の地図・施設一覧は維持。
- Merge Captain: `main`への変更は別判断。

## Tests
```powershell
cd pipeline
python -m unittest tests.test_flood_site_reference -v
python -m unittest discover -s tests -v
```
公式rawでの結合試験・C検証・実端末動作は上記単体テストに含まない。

## 2026-10-09 GSI source normalization and C gate workflow

The official GSI tile specification declares `properties.name`, `address`, `remarks`, and **integer `disaster1=1`** for a flood-designated emergency evacuation place. This D parser reads those explicit source fields, the original GeoJSON Point coordinate order **[longitude, latitude]**, the physical `feature_index=N`, and SHA256 without interpreting local municipal markers.

A generated `source_feature_key` is `{source_url}#feature_index=N`, a deterministic **source trace key, not an official municipality-assigned facility ID**. The `search_context_region_code` identifies the HINANEX demo search region, **not** the municipality where an original feature belongs (the GSI tile may cross borders).

Run after obtaining the archived source bytes from the official server. Example single tile URL below is **illustrative, not a claim of full Edogawa coverage or verified facilities**.

```powershell
cd C:\HINANEX-Preview
$gsiUrl = 'https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson'
$raw = '.\pipeline\data\raw\gsi_flood_tile.geojson'
New-Item -ItemType Directory -Force '.\pipeline\data\raw' | Out-Null
Invoke-WebRequest -Uri $gsiUrl -OutFile $raw

& 'C:\HINANEX\pipeline\.venv\Scripts\python.exe' .\pipeline\prepare_gsi_flood_tile.py --region 13123 --raw $raw --source-url $gsiUrl --out .\pipeline\data\verified\edogawa_gsi_flood_records.json
& 'C:\HINANEX\pipeline\.venv\Scripts\python.exe' .\validation\validation\verify_gsi_flood_source.py --region 13123 --raw $raw --source-url $gsiUrl --records .\pipeline\data\verified\edogawa_gsi_flood_records.json --acceptance-out .\pipeline\data\verified\edogawa_gsi_flood_c_acceptance.json

& 'C:\HINANEX\pipeline\.venv\Scripts\python.exe' .\validation\validation\verify_gsi_flood_provenance.py --raw $raw --source-url $gsiUrl --c-acceptance .\pipeline\data\verified\edogawa_gsi_flood_c_acceptance.json --report-out .\pipeline\data\verified\gsi_https_provenance_20261009.json

cd .\pipeline
& 'C:\HINANEX\pipeline\.venv\Scripts\python.exe' .\run_verified_flood_site_reference.py --region 13123 --raw .\data\raw\gsi_flood_tile.geojson --records .\data\verified\edogawa_gsi_flood_records.json --c-acceptance .\data\verified\edogawa_gsi_flood_c_acceptance.json --provenance .\data\verified\gsi_https_provenance_20261009.json --out .\data\output\edogawa_flood_site_catalog.json
```

If the raw tile is missing/empty/unrecognized, do not create fake records. The strict C validator rejects empty or malformed source data. Keep the real download URL/time/HTTP success and SHA256 for independent A/C review. Official municipality update date and data completeness remain external release gates. To cover multiple tiles, use a separately verified multi-tile provider; do not pretend this single-tile exporter covers the whole region.

The C checker above lives in PR #64 and must be integrated in the local worktree (along with D #63) before running this example. Its PASS means **raw row equality**, not authentication of the HTTPS acquisition nor suitability/current opening.

## HTTPS provenance publication gate (2026-10-09)

D CLIの`--provenance`は必須です。C raw監査の後、`validation/validation/verify_gsi_flood_provenance.py`を統合プレビュールートから実行して公式HTTPS再取得・バイト一致の`MATCH`レポートを新規作成してください（手順:`validation/docs/GSI_FLOOD_PROVENANCE.md`）。

Dは原本/C監査/HTTPSレポートのURL、原本SHA256、HTTP 200、サイズ、件数、監査参照、UTC取得時刻を照合し、不一致では**カタログを出力しません**。既存の出力が存在する場合、失敗時に残る古いJSONをブラウザへ配信しないよう、運用側で隔離・確認してください。

なおこのゲートは取得時点の公式配信バイト一致のみを保証し、施設の自治体所属・網羅性・開設・安全・経路選定を認定しません。メインリリースにはブラウザ実機試験とMerge Captain承認が別途必要です。
