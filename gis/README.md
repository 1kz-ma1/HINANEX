# HINANEX — E / GIS

`gis/` は E担当（GIS / Map / 空間可視化）の領域です。

実装入口は `gis/` サブディレクトリです。

- UI / 起動方法: `gis/README.md`
- E仕様: `E_GIS_SPEC.md`
- テスト: `tests/`

Dの `RegionExport` をconsumerとして利用し、自治体固有Rawデータの解釈や暗黙geocodingは行いません。

## 洪水Scenarioの公式raw Evidence（任意Consumer）

Dの`RegionExport.scenarios[]`に`scenario_id=flood_shelter_selection`がある場合、既存の`shelter_location.records[].id`と**完全一致**で結合して、マーカー詳細に以下を表示します。

- DのScenario status（再判定しない）
- 災害列名のraw、施設単位の公式raw値（`○`/`×`/`－`など）
- `usable_floor_raw`（`2階以上`などの階数条件の原文）
- 元の施設行・source URL・Dの理由
- 地域の情報パネルに、Scenario UNKNOWN件数と公式rawの取得状態

**重要**: 地図の施設点はあくまでDの座標付き`shelter_location`レコードです。Scenarioの`UNKNOWN`を候補外と解釈したり、記号や公的洪水ラスタとの位置重ね合わせから独自に洪水時の利用可否・建物安全性・ルート安全性を判定したりしません。座標のない施設は従来どおり件数へ残し、推測補完はしません。

旧RegionExport（Scenario未搭載）はそのまま表示します。Scenario施設IDが位置レコードと一致しない場合は安全のため読込失敗とし、曖昧な施設名マッチをしません。出典URLは既存`safeExternalUrl()`を通して無効なスキームを拒否します。

**Gitと統合について**: 現在の`role/e-gis`はmainに対し大幅に遅れていたため、今回は最新mainから`feature/e-flood-scenario-evidence`を作成し、E担当`gis/**`だけを変更します。D #46がmain未統合の間、このconsumer PRは依存ありのDraftとし、Merge Captain判断を待ちます。

実行できる確認（Node.js 20+）:

```powershell
cd C:\HINANEX
node gis/tests/d_region_adapter.test.js
node gis/tests/map_controller.test.js
node gis/tests/region_exports.integration.test.js
```

これらの合成テストの成功は、公式記号の意味の認定や実洪水に対する安全性検証を意味しません。新潟ODS記号の正式な意味は[Issue #48](https://github.com/1kz-ma1/HINANEX/issues/48)で追跡します。

## 2026-10-08 地図の無座標表示・ブラウザ警告

- Nagoya公式raw資料の1,602施設には機械可読な緯度経度がないため、`records=1602 / 地図表示=0 / 座標欠損=1602` は正常なデータ状態です。位置を推測して表示しません。
- 地域切替で前の地域の地図が透けて誤認されないよう、座標と参照境界のない地域は**不透明な未確定オーバーレイ**で地図本体を覆います。対応する公式座標を取得するまで地図位置は確定しません。
- 既存`supported_disasters`は`元データ記載の災害（適合性未検証）`と表示し、Source上の文字列と洪水Scenarioの独立した`UNKNOWN`を混同しません。
- Microsoft Edgeの`Tracking Prevention blocked access to storage for https://unpkg.com/leaflet@1.9.4/dist/leaflet.css`は、第三者CDNに対するブラウザストレージ制限の警告です。**地図ライブラリが正しく読み込めないことをこのログだけから断定しません**。もしLeafletのCSS/JSが実際にブロックされた場合は、別途ロード成否を確認して静的アセット配布の方針を決めてください。これは無座標や洪水Scenarioの判定とは独立です。

## 無座標施設の検索・閲覧モード（E / GIS Consumer）

Dの `shelter_location.records[]` が存在する一方で **座標付きレコードが0件** の場合、Eは推測地図を描く代わりに一覧モードへ自動切替します。例：名古屋市の2026-10-08時点の屋内施設データ1,602件（公式raw照合済み、座標表示0件）。

- 名称・住所・行政区域・施設ID・Scenarioの公式raw値や利用階原文で検索（全角/半角や空白を検索時のみ正規化）
- 1ページ20件のページ送り。ヒット0件も明示。**元recordsは全件保持**し、元の文字列は変更しない
- `details/summary` で各施設の住所・行政区域・種別・Dに記載された災害種別・元のScenario status・公式raw値・利用階原文・照合方式・元Source行・判定理由を表示。SourceリンクはHTTPSに限り表示
- 洪水Scenario自体が未搭載の旧RegionExport 0.9でも一覧は利用可能。公式raw情報が存在しないときに適合性を埋めたり推測しない
- 名古屋市での洪水・内水は混合列で、HINANEX独自に洪水単独判定へ分割しない。UNKNOWNは危険・利用不可・開設なしを意味しない
- モバイルでも詳細は一覧内展開可能（右サイドパネルを前提としない）
- 座標が確認できる地域では従来の地図/マーカー機能を使い、切替時は古い検索語や前地域の一覧をクリアする

**DのSchemaや施設のSource/座標は変更しません。** 明示的geocoding、AIの施設候補選定、避難経路の安全計算、現在の開設案内は実装しません。

実装：`gis/gis/js/facility_list.js`（検索/ページングのみ）・`gis/gis/js/map.js`（UI接続）。回帰テストは `gis/tests/facility_list.test.js` と `gis/tests/map_controller.test.js`。

```powershell
node gis/tests/facility_list.test.js
node gis/tests/d_region_adapter.test.js
node gis/tests/map_controller.test.js
node gis/tests/region_exports.integration.test.js
```

依存：E GISのプレビューPR #58、無座標表示修正 #60、D保守的判定 #49、C独立監査 #50。 `main` はMerge Captain専用であり、この変更はプレビュー向けfeature PRとして提出します。

## 10/22 MVP: 現在地 × 洪水公式指定緊急避難場所（参考探索）

江戸川区のGISで、ユーザーは **地図上の地点を手動クリック**するか、**位置情報を明示的に許可した場合のみ**現在地を選択できる。位置の座標はブラウザ内で保持し、位置座標をHTTPリクエストに付加しない。

別データとしてDが発行した C-accepted GSI洪水指定緊急避難場所カタログ `pipeline/data/output/edogawa_flood_site_catalog.json` を、地点を選択して初めて読み込む。カタログの `REFERENCE_ONLY + C_ACCEPTED`、公式タイルSource、施設の元名・住所・備考・座標・Source hash/feature traceを確認できた時だけ**直線距離の近い5地点を参考掲載**する。距離が近い=安全、行くべき避難先、経路時間、実際の開設中ではない。江戸川区公式の広域避難方針へのリンクを常設。

カタログ不存在、C未承認、内容異常、GPS拒否・未対応時は明示的な説明を表示して安全に終了。既存 `shelter_location` 152件、3地域の `UNKNOWN` Scenario、国土地理院の浸水想定参照ラスタなどから適合性を推測しない。名古屋の無座標施設一覧モードも既存どおり保持する。

**手順**：
1. A公式ソース調査 → D archived GSI skhb01 Source normalize → C独立raw監査 → D参考カタログ生成。未認証データでは掲載は0件。
2. HTTP配信で `/gis/gis/?region=13123` を開く。
3. 「地図から出発地点を指定」を押して地図をクリック。端末のGPSは別ボタンで明示許可を要求。
4. 一致した公式掲載地点がある場合のみ、公式住所/Source/直線距離を確認。江戸川の広域避難指針を優先。

**テスト（Node）**：
```powershell
node gis/tests/flood_discovery.test.js
node gis/tests/map_controller.test.js
node gis/tests/facility_list.test.js
node gis/tests/d_region_adapter.test.js
node gis/tests/region_exports.integration.test.js
```

公式の配布GeoJSONに対するA/C実検証が完了するまで、GSI Sourceの`REFERENCE_ONLY`掲載を正式な自治体データ検証PASSとは扱わない。
