# HINANEX Frontend

B担当のUI実装です。D担当が生成するRegionExport JSONをConsumerとして読み込み、分析済みの結果を表示します。

## 現在の実装（SC02 地域詳細）

RegionExport `0.9`の以下を、契約上の意味を変えずに一画面へ表示します。

- 江戸川区・新潟市・名古屋市のセグメントボタン切替
- 地域名、Capability状態、取得件数、Gap件数、Recommendation件数、生成日時の分析サマリー
- 地域基本情報と出力件数
- Capability状態、評価理由、依存データ
- Dataset Assessmentのdiscovery status、record件数、findings
- Data Quality / Application Readinessの各MetricScore
- GapとRecommendation
- `requirement_code`で追跡できるEvidence
- 地域コードを引き継ぐGIS画面への導線

再読込、手動JSON読込、合成デモ、Contract Version、`generated_at`は「詳細設定」にまとめています。Data Quality 7項目とApplication Readiness 8項目は個別に展開でき、合計点・平均・ランキングは作りません。

UI側では評価結果、スコア、Gap、Recommendationを再計算しません。`score=0`は`0 / 4`、`score=null`は`未評価`として区別します。

`mock/region-export.json`は画面確認専用の合成データです。実在地域の防災状態を表しません。BLOCKED、Gap、Recommendation、`score=4 / 0 / null`、`published_at=null`を確認できる形にしています。

名古屋市の`shelter_location`については、正式なB向け引き渡し資料に従い、record件数を「16区別の屋内施設データ」の現在取得件数として表示します。名古屋市の全避難関連施設数とは表現しません。

## 実データの読み込み

画面上部の3地域ボタンから、Dが生成する次のRegionExportを直接読み込みます。

```text
pipeline/data/output/edogawa.json
pipeline/data/output/niigata.json
pipeline/data/output/nagoya.json
```

runtime artifactが未生成の場合は、先に`pipeline/run_all_workflows.py`を実行してください。「詳細設定」の「JSONを手動読込」からRegionExportを選ぶこともできます。

`mock/region-export.json`は「合成デモ」ボタンでのみ表示し、実データの自動読込失敗時に黙ってfallbackしません。地域切替中は前の取得を中断し、遅れて完了した古いリクエスト結果で現在表示を上書きしません。

## GIS導線

実データ表示時は分析サマリーから、地域コードをquery parameterとして渡します。

```text
/gis/gis/?region=13123
/gis/gis/?region=15100
/gis/gis/?region=23100
```

FrontendはURL生成だけを担当します。現時点のGIS画面には`region` query parameterを読み取って初期選択へ反映する処理がないため、E担当での対応が必要です。

## 起動

`frontend/`と`pipeline/data/output/`を同じHTTP originから参照するため、リポジトリrootで静的サーバーを起動します。

```powershell
cd C:\HINANEX
python -m http.server 8000
```

その後、`http://localhost:8000/frontend/`を開きます。

## テスト

追加パッケージは不要です。Node.js 20以降で実行します。

```powershell
node --test
```

`npm`が利用できる環境では以下を実行できます。

```powershell
npm test
npm run lint
npm run build
```

このFrontendは依存なしの静的サイトです。`build`は配布物の生成ではなく、必須ファイル・HTML参照・mock JSONを検証します。

## 契約境界

- JSON Schema: `../pipeline/contracts/region_export.schema.json`
- B向け引き渡し: `../pipeline/docs/HANDOFF_B.md`
- B/C契約: `../pipeline/docs/HANDOFF_CONTRACT_v1.0.md`
- UIルール: `AGENTS.md`

表示に必要なフィールドがContractに存在しない場合は、Frontend独自の意味付けを追加せず、D担当へContract変更として提案します。

## 洪水Scenarioの公式情報パネル（任意）

D `RegionExport.scenarios[]` に `scenario_id=flood_shelter_selection` がある場合のみ、地域詳細に **「洪水に関する公式情報」** を表示します。古いRegionExport（`scenarios`未搭載）は従来画面のまま動作します。Dの旧 `shelter_discovery` CapabilityとScenarioの判定は別物です。

- Dの元status・施設名・公式raw値・利用階の原文・Source URL・元の施設行trace・reasonを表示
- `UNKNOWN`を「危険」「利用不可」「情報なし」と言い換えない。rawセル取得済み（`discovery_status=AVAILABLE`）と適合判定不能（`Scenario.status=UNKNOWN`）を区別
- 施設一覧は20件ずつ表示し、総件数と閲覧位置を明示する
- 公式リンクはHTTPSのみ、施設名/原文はtextContentとして安全に表示
- 現行新潟ODSの `○`、`×`、`－` はIssue #48で公式意味未確定。B側で「候補・除外」へ再分類しない
- `2階以上`等の`usable_floor_raw`は生の制約文。階数条件だけで安全・開設状況・安全な移動経路を判定しない
- 旧暫定status `CANDIDATE/EXCLUDED`を含む古いJSONを手動読込した場合も**Dの元値としてのみ**表示し、公式安全適合とは扱わない

新規テスト: `tests/flood-scenario-view-model.test.js`。新モデルは `src/flood-scenario-view-model.js` で、Dの評価ロジックを再実装しません。

**依存関係**: D #41/#44/#49（`role/d-pipeline`）、A #43、C #42/#50。mainへのD統合（Draft #46）が完了する前はBの消費側のPRを最終統合しないでください。新潟ODSの公式記号意味の確定は[Issue #48](https://github.com/1kz-ma1/HINANEX/issues/48)で引き続き確認します。
