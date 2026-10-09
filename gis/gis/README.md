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

## 座標を指定して公式GSI掲載地点を探索（実機受入用）

地図左上の「緯度・経度で地点を指定」に `35.70, 139.90` のように **10進数の緯度,経度** を入力し、「座標で探索」またはEnterキーを押します。

- 入力した地点へ地図を移動し、既存の「選択地点周辺のGSI公式掲載」モードで、C独立検証済みのタイルを探索します。紫の無番号マーカーは**指定緊急避難場所の公式掲載情報（参考）**であり、安全な行先・推奨順位ではありません。
- テストする2地点の例：`35.70, 139.90`（起点z10 `909/403`）、`35.70, 140.10`（起点z10 `910/403`）。座標検索はアプリ内操作であり、タイルの公式データが検証済み・配信済みでない場合でも地図は移動し、GSI結果は未検証のままです。
- 緯度・経度の順にカンマ（半角・全角・読点）で区切ります。空欄・数値以外・3値以上・Web Mercatorの緯度±85.05112878度超・経度±180度超は拒否します。拒否時は選択地点・レイヤー・地図・送信済みタイルを変更しません。
- 地図クリックやGPS指定も従来どおり利用できます。選択地点は入力欄にも小数5桁で表示されます。別の自治体へ切り替えると旧地点の入力とGSI参照結果をクリアします。
- 正確な座標をHINANEXにPOSTしません。ただし既存のGSI配信サーバーには地図の概略地域を示す**z10タイルID**が送られ、背景地図の要求は地図配信元へ送られます。地図上の位置を指定しても災害種別・安全性の判定が実行されたことにはなりません。

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
