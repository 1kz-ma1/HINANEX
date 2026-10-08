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
