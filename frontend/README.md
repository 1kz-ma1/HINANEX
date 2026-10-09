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

FrontendはURL生成を担当し、現在のGIS画面は`region` query parameterを読み取って対応地域を初期選択します。未対応の地域コードはGIS側で無視され、既定地域の選択を維持します。

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

## 洪水時の避難候補探索

D `RegionExport.scenarios[]` の `scenario_id=flood_shelter_selection` をConsumerとして表示します。Dの既存 `shelter_discovery` CapabilityとScenarioの判定は別物です。

- Scenario SummaryはDの`status`、`requirement_assessment.reason`、`record_count`、`directly_joined_count`、`raw_value_count`だけを表示
- 施設一覧から候補・候補外・判断不能の件数やScenario状態を再集計しない
- 施設単位の`CANDIDATE / EXCLUDED / UNKNOWN`は「候補 / 候補外 / 判断不能」と表示し、元codeは技術情報へ残す
- Dの`reason`、公式項目、Source固有の意味、公式raw値、利用階の原文、行trace、照合状態、Source URLを「根拠を見る」で追跡できる
- `UNKNOWN`を「危険」「利用不可」「情報なし」に変換しない。`EXCLUDED`も危険・利用不可とは説明しない
- 江戸川の`水害`、新潟の`災害種別_洪水`、名古屋の`洪水・内水`を同じ公式項目へ書き換えない
- 新潟ODSの`○ / × / － / 階数`、名古屋の複合列、江戸川の未照合結果をFrontendで再判定しない
- Loading / Scenario結果なし / Fetch Error / Unsupported Contractを区別し、地域切替開始時に前地域の結果を消去
- 施設一覧は20件ずつページングするが、ページ用の行数をScenario Summaryの判定件数として表示しない
- 公式リンクはHTTPSのみ、施設名・reason・raw値は`textContent`で表示
- 地図導線は既存の地域単位`/gis/gis/?region=<region_code>`だけを使用し、未定義の施設query parameterを追加しない

`mock/region-export.json`のScenarioは候補・候補外・判断不能と根拠開閉を画面確認するための合成データです。実RegionExportとはヘッダーの合成デモ表示で区別され、実在地域の施設判定ではありません。

実装は`src/flood-scenario-view-model.js`でD Contractの表示対象をfail-closedに検査します。未対応のstatusや必須項目欠損がある場合、値を補完せず「未対応のScenario Contract」と表示します。Dの評価ロジックは再実装しません。

**依存関係**: D #46（provider統合）、C #47（Acceptance）。両PRがmainへ入り、Dの実RegionExportが再生成・承認されるまではBのScenario UIをmainへ最終統合しないでください。新潟ODSの公式記号意味は[Issue #48](https://github.com/1kz-ma1/HINANEX/issues/48)で未解決のため、現在のD出力どおり全施設を`UNKNOWN`として扱います。
