# HINANEX E担当 GIS仕様 — Integration Candidate v5

## 1. 責務
Eは `gis/` 配下のみを担当し、Dが正規化した位置情報を地図へ可視化する。
自治体固有CSVの列解釈、geocoding、危険度評価、Source normalizationはEへ複製しない。

## 2. Dとの正本Contract
D-MVP v1.0の正本は `pipeline/data/output/{region}.json` の `RegionExport`。
現行JSON Schema versionは **0.9**。Eは `datasets` から `requirement_code == "shelter_location"` を検索し、`records` を描画する。

対象出力:

- `edogawa.json` / region code `13123`
- `niigata.json` / region code `15100`
- `nagoya.json` / region code `23100`

`data/output/*.json` はD側で再生成可能なruntime artifactとしてGit管理外であるため、Eは相対URL自動探索とファイル選択の両方を提供する。

### shelter_location record
現行Dモデル `ShelterRecord` に合わせる。

- `id: string`
- `name: string`
- `latitude: number | null`
- `longitude: number | null`
- `address: string | null`
- `administrative_area: string | null`
- `facility_type: string | null`
- `supported_disasters: string[] | null`
- `accessibility: boolean | null`
- `capacity: integer | null`
- `detail_url: string | null`
- `notes: string | null`

### Null semantics
- `latitude/longitude = null`: 元データに機械可読座標がない。Eで推測しない。
- `supported_disasters = null`: 安全に判断不能。Eで災害対応を推測しない。
- その他のnullも「不明 / 未確認」として表示する。

## 3. Contract validation
描画前に最低限以下を検証する。

- `region.code` / `region.name`
- `datasets` array
- `meta.schema_version == "0.9"`
- 選択地域と `RegionExport.region.code` の一致
- `shelter_location.region_code` とトップレベルregion codeの一致
- 緯度・経度は両方number、または両方null
- 緯度経度の範囲
- `supported_disasters` / `accessibility` / `capacity` の型

Contract不一致を黙って捨てず、読込失敗としてUIへ出す。

## 4. 座標欠損の扱い
地図描画できないrecordを黙って捨てない。UIで必ず以下を表示する。

- datasetの全records数
- 地図へ描画したrecords数
- 座標欠損records数

片方だけ座標が存在するrecordはContract違反として読込を失敗させる。
名古屋市のように機械可読座標がない地域でも、0件表示と欠損件数を正しく示し、geocodingしない。

## 5. 地域切替
D-MVP対象3地域を選択可能にする。

地域切替時は:

1. 既存の避難所markerをクリアする。
2. 対応する `data/output/{region}.json` を探索する。
3. 読めた場合は選択地域codeとの一致を検証して描画する。
4. 境界fixtureが存在する地域は境界へfitする。
5. 境界fixtureがなく座標付きrecordがある場合はmarker boundsへfitする。
6. どちらもない場合は推測した中心座標へ移動しない。
7. リセットボタンの地域名は選択地域へ追従する。

## 6. 起動方式
`file://` 直開きでは相対 `fetch()` がブラウザのOrigin制約を受けるため、自動読込を試行しない。
UIで理由を明示し、次のどちらかを利用する。

- リポジトリrootからHTTP配信して `gis/gis/` を開く。
- 「JSONを選択」からRegionExportを手動読込する。

これにより `file:` unique originに起因するエラーを、データ不具合のように見せない。

## 7. 洪水表示
Dの現行MVPには洪水分析DataRequirementがまだ存在しない。
そのためEでは、ハザードマップポータルサイトの「洪水浸水想定区域（想定最大規模）」を **公的参照ラスタ** として表示する。

- 独自riskへ変換しない。
- ラスタ色から浸水深を推測してDの分析値のように表示しない。
- Dで洪水Contractが追加された場合は、Add → Migrateの順で接続する。

## 8. 境界fixture
江戸川区は表示確認用の行政区域fixtureを利用する。これは画面の表示範囲を確定するための参照であり、HINANEX分析の正本ではない。
新潟市・名古屋市について、Eが推測した境界・中心座標は追加しない。D座標が存在する場合はmarker boundsを利用し、存在しない場合は「表示範囲未確定」とする。

座標系はWGS84緯度経度（GeoJSON coordinate order: longitude, latitude）を前提とする。境界fixtureの精度を分析値として利用しない。

## 9. Integration test
E側のdeterministic fixtureは、実在施設を模倣せず `TEST` recordとして生成する。
`generate_d_regionexport_fixtures.py` はDの実装中の `NormalizedDataset` / `ShelterRecord` / `build_region_export()` をimportしてRegionExportを生成し、E adapterが3地域を読めることを確認する。

期待値:

- 江戸川区: 2 records / 1 map / 1 missing
- 新潟市: 2 records / 1 map / 1 missing
- 名古屋市: 2 records / 0 map / 2 missing

テストfixtureは契約確認専用であり、防災情報として利用しない。

## 10. 受入条件
1. D RegionExport 0.9をファイル選択またはHTTP相対URLから読める。
2. 江戸川区・新潟市・名古屋市の出力pathを切り替えられる。
3. `shelter_location` 以外のdatasetを誤って避難所として描画しない。
4. `null` 座標をgeocoding・補間しない。
5. 座標欠損件数をUIで確認できる。
6. Region / schema version / field type不一致を検出できる。
7. Dのnull semanticsを壊さない。
8. 公的洪水ラスタとD避難所レイヤーを独立してON/OFFできる。
9. 公的洪水は想定最大規模として表示し、独自評価へ変換しない。
10. `file://` 起動時に相対fetchを試みず、手動読込/HTTP起動へ案内する。
11. Dの現行builderを利用して生成した3地域RegionExport fixtureでconsumer integrationを確認できる。
12. E担当外のファイル変更を必要としない。
