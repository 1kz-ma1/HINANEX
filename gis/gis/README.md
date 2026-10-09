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

## 2026-10-22 実演・再現手順

実機で受入済みのD3地域・D/GSI比較・クラスタ・GPS拒否を約90秒で実演し、外部洪水タイルが未配信の場合の代替手順まで記録する。[EのGISライブデモ受入台本](../docs/DEMO_ACCEPTANCE_20261022.md) を使用する。台本は実機でのリハーサル合格・本番公開許可を意味しない。

**表示上の安全性補助（v11）**：名古屋のように選択地域のD施設が全件座標欠損のときは、施設一覧に地図が覆われるため「地図をクリックして出発地点を指定」ボタンを無効化し、施設名・住所検索を案内する。座標を推測補完せず、GPSの独立した取得機能のコードは変更しない。洪水ラスタの外部 `tileerror` が検知されたら、Dの読込状態に上書きされない別の注意文を「レイヤー」に表示する。1タイルの `ObjectNotFound` を「浸水なし」や全域の非配信とは解釈しない。

## 10/22 Phase 1 ブラウザ受入：3表示モード・GPS拒否・外部配信

Cのローカル証跡検査（ユーザー実行で `35.70,139.90` / `35.70,140.10` の双方9/9）と、Leafletの**実機表示受入**は別工程。Windows Edgeで次を確認して記録する。

1. `http://localhost:8000/gis/gis/?region=13123` を `Ctrl+Shift+R` で更新。`35.70,139.90` と `35.70,140.10` を順に入力する。検証済みタイル・掲載件数はそれぞれ**9/9・6,656件**、**9/9・4,713件**。どちらも起点タイルと周囲8タイルの公式掲載件数で、自治体内の件数ではない。
2. `選択地点周辺のGSI公式掲載` では、**青い二重リング＝ユーザー指定の探索起点**、紫の無番号マーカー＝検証済みGSI公式掲載地点、緑のD避難所レイヤーは非表示。起点と紫の位置が近い場合も青が前面に見えること。
3. `地域Dと周辺GSIを比較` を選択する。選択地点が千葉側（例：`35.70,140.10`）の場合は江戸川区D施設が現在の地図範囲に入らないため、右下GSIパネルの **「緑と紫を一緒に見る」** を押し、**実際に座標が確認できるD緑マーカーと検証済みGSI紫マーカー**が両方地図範囲に入ることを確認する。これは表示範囲を合わせる操作であり、安全性・優先度を評価しない。続いて `地域のD施設` を選択し、紫マーカーと**右下GSI説明パネルが両方消える**ことを確認。再度 `選択地点周辺のGSI公式掲載` に戻せば、元のC照合済み紫マーカーと右下パネルが再表示される。切替だけで再ダウンロードしない。選択地域のDに座標が無い場合は比較範囲ボタンを無効化し、欠損・未読込を明示する。**比較表示は施設の安全性・優劣を意味しない**。
4. 位置情報ボタンを押し、ブラウザの位置情報要求を拒否する（既に許可済みならEdgeのサイト権限設定で一時的に再確認）。拒否した場合は座標入力にフォーカスが移り、数値入力から探索を継続できること。位置情報を拒否しても起点と探索結果が勝手に変更されないこと。サイト権限の変更はテスト後に元に戻す。
5. Edgeの `F12` から **Console** と **Network** を確認。Consoleの未処理JavaScript例外と、`pipeline/data/output/gsi_verified_tiles` の静的JSON取得結果を分けて記録。外部`disaportaldata.gsi.go.jp`の洪水ラスタについては失敗URI / status / 発生座標ズームを控え、GSI`skhb01`公式掲載データの独立C受入と**別の配信障害**として扱う。個別ラスタの404を「浸水なし」「避難先安全」と断定しない。
6. 新潟市 (`15100`)・名古屋市 (`23100`) に地域選択を切り替えて、選択中のURLとDの名称・件数・UNKNOWN / 座標欠損が一貫して表示されること。Git管理外のD JSONが未配信なら**未読込**と記録し、合格扱いしない。

**PASSと区別すべきもの：** この手順でマーカーと地域切替が動いても、公式データの最新性、実際の開設・避難経路・リスク判定、全国対応、`main`リリース可否にはならない。コンソール・GPS・外部ラスタ・3自治体Dの確認結果はIssue #89へ `PASS / LIMITATION / NOT TESTED` を分けて記録する。

## 3自治体のローカルD出力を一括で受入前チェックする（読み取り専用）

実機の\`C:\HINANEX-Multi\`でD RegionExportが各地域に用意されているかを、**ブラウザと同じE D adapter**で検証する。Rawソース・生成済みJSONは**変更・削除・上書きしない**。同じadapterで解析できることは、A/C独立監査や公式ソースの正しさを証明するものではない。

~~~powershell
cd C:\HINANEX-Multi
node .\gis\tests\inspect_local_region_exports.js
# 構造化した全結果が必要なら:
node .\gis\tests\inspect_local_region_exports.js --json
~~~

自動照合する3ファイルは \`pipeline/data/output/edogawa.json\` / \`niigata.json\` / \`nagoya.json\`。欠損している場合は \`MISSING_FILE\` と表示し、**公式施設が存在しないという意味にはしない**。元のD用worktreeにしかファイルがないなら別途コピーするか、その地域のJSONを画面の手動読込から指定する。

- \`LOCAL_CONTRACT_OK\`: その地域コードのRegionExport 0.9をEが解析できる。出典の独立検証や開設・避難安全性は未検証。
- \`INVALID_JSON\` / \`INVALID_CONTRACT\` / \`DUPLICATE_FACILITY_ID\`: ファイル・整合性の問題。既存データの推測補完や自動修復をせずD側へ引き継ぐ。
- \`records\` / \`mapped\` / \`missing_coordinates\`: それぞれ元レコード全数・座標を確認できた件数・欠損数。3数値間の整合を確認する。
- \`scenario_unknown\` と \`scenario_status\`: D原値のみ。新潟ODSや名古屋の災害列の意味はEで推測せず \`UNKNOWN\` を保持する。Scenarioが存在しない場合は \`NO_FLOOD_SCENARIO_PRESENT\`。
- 出力にはローカルファイルのSHA256を付けるが、**C公的原本照合を実行したという意味ではない**。\`baseline_accepted\` は常に \`false\`、HTTPで配信できるか、GPSや洪水ラスタは \`NOT TESTED\`。

実機の最後の受入は、3つの地域のそれぞれでGIS URLを開き、画面の「D出力読込済」・元件数・座標欠損・\`UNKNOWN\`・位置を人間が確認する。コマンドの \`LOCAL_CONTRACT_OK\` だけで公開可能と判定しない。

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

### D施設の広域表示クラスタ（E可視化のみ）

広域ズーム **12以下** で近接したD RegionExport施設の緑マーカーを**画面ピクセルの固定グリッド**でまとめ、円内に**Dレコードの実件数**を表示する。**ズーム13以上では全施設を元の個別マーカーに戻す**（外部Leafletプラグイン不要）。各クラスタをクリックするとズームを2段階まで拡大し、さらに拡大すると元のD施設ごとのSource由来属性が確認できる。

- 集計範囲は選択地域の**座標が確認済みのD mappableRecordsだけ**。RegionExport自体の総件数・UNKNOWN・座標欠損数は変更しない。座標欠損をグループに混ぜたり、推測補完したりしない。
- クラスタ円の位置は構成施設座標の**描画上の平均**であり、実在する避難施設の場所・移動先ではない。円内の数字は掲載順位・推奨度・収容人数ではない。
- **紫のC検証済みGSI公式掲載地点5件、青の探索起点、別災害の判定**はクラスタに含めない。GSI側はこれまでどおり無番号のまま。
- 地域切替・D JSON差替・ズーム・非表示→復帰でもDの元データとGSI独立監査を維持する。

### 公的洪水ラスタの部分配信の診断

国土地理院の「洪水浸水想定区域（想定最大規模）」ラスタタイルは独立した外部配信（<https://disaportaldata.gsi.go.jp/hazardmap/copyright/opendata.html>、URL `01_flood_l2_shinsuishin_data`、公式ズーム **2～17**）。一部地域は掲載が限定される。Leafletが`tileerror`を返した際は「外部タイルの**一部**が表示できない」とし、**洪水被害なし・安全・避難可能**へ変換しない。DevTools Consoleへ最大3件/配信元の公式タイルURLを出力するが、HTTPステータスや根本原因はこのイベントだけでは確定しない。**NetworkでURL・ステータス・ブラウザブロック理由・ズームを独立確認**する。GSI `skhb01`指定緊急避難場所のC独立監査とは別情報で、未表示ラスタはその照合結果を取り消さない。
