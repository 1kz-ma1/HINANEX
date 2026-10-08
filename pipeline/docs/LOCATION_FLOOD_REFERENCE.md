# D: 位置指定 × 洪水指定緊急避難場所（10/22 MVP用、プレビュー段階）

## Purpose
現行の`shelter_location`を「災害時に安全な避難所」に変換せず、**国土地理院の洪水`skhb01`タイルに掲載された「指定緊急避難場所」** を別のSourceとして扱う準備をする。

- Dは候補の公式指定・出典を保持するだけ。「推奨」「安全」「開設中」「安全な経路」は判定しない。
- 江戸川区の水害時の広域避難方針を候補表示で打ち消さない。
- 既存`RegionExport` / `flood_shelter_selection`はそのまま。未確認`UNKNOWN`や`supported_disasters`から新しい候補を生成しない。
- この段階ではGSI公式タイルの**実施設row/field schemaは未取得**。A→C原本確認の後で有効データを出力可能となる。

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

例（**C監査後に限り実行**、すべてユーザーのローカル成果物・Git管理外）:

```powershell
cd pipeline
python run_verified_flood_site_reference.py --region 13123 `
  --raw data/raw/gsi_flood_tile.geojson `
  --records data/verified/edogawa_flood_site_records.json `
  --c-acceptance data/verified/edogawa_flood_site_c_acceptance.json `
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
