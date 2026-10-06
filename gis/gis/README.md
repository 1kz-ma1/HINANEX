# E — GIS / Map

Dの `RegionExport` を使って避難所位置を地図表示するE担当のMVPです。背景地図は国土地理院、洪水はハザードマップポータルサイトの公的参照ラスタを利用します。

## 起動

リポジトリrootをHTTP配信してください。

```powershell
cd HINANEX
python -m http.server 8000
```

ブラウザで次を開きます。

```text
http://localhost:8000/gis/gis/
```

`file://` 直開きでも画面自体は開けますが、ブラウザのorigin制約を避けるためD出力の自動 `fetch()` は実行しません。その場合は画面の「JSONを選択」からRegionExportを読み込めます。

Frontendなどから地域を指定して開く場合は、`region` query parameterを利用できます。

```text
http://localhost:8000/gis/gis/?region=13123
http://localhost:8000/gis/gis/?region=15100
http://localhost:8000/gis/gis/?region=23100
```

対応していない地域コードは推測せず、画面既定の地域へ安全にフォールバックします。

## D出力

Dのruntime artifactはGit管理外です。先に `pipeline` で生成するか、画面からRegionExport JSONを選択してください。

```powershell
cd pipeline
python run_all_workflows.py
```

Eは次を自動探索します。

```text
pipeline/data/output/edogawa.json
pipeline/data/output/niigata.json
pipeline/data/output/nagoya.json
```

## Safety / Contract

- RegionExport schema version `0.9` を対象にする。
- 座標欠損を住所から推測しない。
- 座標欠損recordは件数に残し、地図表示件数との差をUIに出す。
- 地域切替時は古い非同期読込結果を破棄する。
- `detail_url` は `http/https` のみリンク化する。
- 洪水は公的参照ラスタであり、Dの分析値ではない。
- ラスタ色から独自の危険度や地点属性を生成しない。
- 洪水凡例は統一後の8段階分類を表示し、色は公式ラスタそのものを参照する。

## Eテスト

リポジトリrootから実行します。

```powershell
python gis/tests/smoke_checks.py
node --check gis/gis/js/d_region_adapter.js
node --check gis/gis/js/map.js
node gis/tests/d_region_adapter.test.js
node gis/tests/map_controller.test.js
python gis/tests/generate_d_regionexport_fixtures.py
node gis/tests/region_exports.integration.test.js
```

`map_controller.test.js` はD RegionExport 0.9相当の3地域fixtureを使い、地域切替・座標欠損・`file://` guardをブラウザ非依存で検証します。

詳細は `../E_GIS_SPEC.md` を参照してください。


`region_exports.integration.test.js` は、Dの実際のRegionExport builderから生成したdeterministic fixtureをE adapterへ通し、D→E Contractの接続を確認します。fixtureはすべて合成TEST recordで、実在の防災情報ではありません。
