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
- 施設一覧は20件ずつ表示し、総件数と閲覧位置を明示する。結果0件ではページ送りを出さず、避難先不存在とはみなさない
- 公式リンクはHTTPSのみ、施設名/原文はtextContentとして安全に表示。施設の公式記録・出典はキーボード操作可能な折りたたみで確認
- 現行新潟ODSの `○`、`×`、`－` はIssue #48で公式意味未確定。B側で「候補・除外」へ再分類しない
- `2階以上`等の`usable_floor_raw`は生の制約文。階数条件だけで安全・開設状況・安全な移動経路を判定しない
- 旧暫定status `CANDIDATE/EXCLUDED`を含む古いJSONを手動読込した場合も**Dの元値としてのみ**表示し、公式安全適合とは扱わない

読み込み中・データ取得失敗・Contract不整合・0件結果は別々に表示します。`FULL` はScenarioの判定範囲、`AVAILABLE` は公式raw取得状況を表し、安全性や開設状況を保証しません。詳細仕様: `docs/FLOOD_SCENARIO_CONSUMER_GUARD.md`。

新規テスト: `tests/flood-scenario-view-model.test.js`。新モデルは `src/flood-scenario-view-model.js` で、Dの評価ロジックを再実装しません。

**統合状況**: #106でD/C/B/EのFlood Scenario統合版をmainへ反映済み。#110でContract不整合のfail-closed guardを追加済み。新潟ODSの公式記号意味の確定は[Issue #48](https://github.com/1kz-ma1/HINANEX/issues/48)で引き続き確認します。

## 2026-10-09 独立した地図・分析画面間の導線

- GISヘッダーの **「分析・根拠 ↗」** は独立したB分析ページ（`/frontend/`）を新規タブで開く。埋め込み表示・固定×オーバーレイは実装しない。
- B分析画面のヘッダーには **「← 地図へ戻る」** を常時表示し、同じタブから `/gis/gis/?region=<選択地域コード>` へリンクする。
- GISに戻るリンク先は3つの地域ボタンを切り替えるたびに更新。読込中は選択地域を使用し、合成データを実在する地図として見せず、デモ中は明示的に選択されている地域にリンクする。
- 分析ページ内でスクロールしてもヘッダーが使えるようsticky表示。モバイル44pxタップ領域・キーボードフォーカスに対応。
- 元のGISタブは引き続き存在するが、別タブ間の自動フォーカス移動やタブ自動クローズは実装しない。ブラウザの戻る履歴や `window.opener` に依存しない。
- UI導線のみでD RegionExport/GISの判定・公式データの意味は変更しない。実ブラウザでの見え方は別途確認。


## 2026-10-13 独立した根拠検証事例ページ（B / Issue #157）

\`/frontend/evidence-case.html\` から、旧下鎌田小学校の**公表資料の時点差**を3状態で閲覧できるUIを追加。地域分析トップの「出典の時点差を検証する事例を見る」から移動する。既存の D RegionExport、Flood Scenario、E GIS マップ、施設ピン、推薦ロジックとは**独立した教育用ページ**であり、実際の避難先を探す用途ではない。

- \`frontend/mock/shimokamata-evidence-ui-preview.json\` は画面をすぐ確認できる**B手製のUIプレビュー用サンプル**。C PR #136の公開用JSON契約に記載された公表済み公式資料4件の固定SHA256と文章を写し、\`C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1\` の形で検証する。**Cジェネレータを実際に実行して得た最新出力ではなく、新規に公式原本の再照合・現況調査を実施していない。** 画面でも「表示確認用サンプル」と常時表示。
- Cが生成した公開用JSONは、ページの「C公開用JSONを選択」からローカルファイルを手動読込できる。ファイルの内容は外部サーバーへアップロードしない。読込時はJSON形式、契約バージョン、公開用途フラグ、資料4件のURI/原本SHA/対象日/本文、表示3状態の順序と固定文、旧新校舎の別住所、UNKNOWNを全部検証。改変・未対応・不審なデータは**fail-closed**で拒否し、前に表示していた事例を消す。
- 表示用情報は原文・ファイル名・SHAなどの**非公開の行政回答**を含まず、独立した市の公開原本4件の出典情報だけ。原本の再取得や行政の本人確認をBでは実行しない。公式URLリンクはあらかじめ決められたHTTPS元データだけで、DOMへは\`textContent\`を使用し、HTMLを入力から解釈しない。
- 表示3状態は \`DOCUMENTARY_FACT\`、\`SOURCE_VERSION_RECONCILIATION\`、\`CURRENT_OPERATIONS_UNKNOWN\`。最後は目立つUNKNOWNであり、**「安全/危険」「開設中/閉鎖」「利用可/不可」へ変換しない**。外水/内水と旧/新敷地、行政上の掲載と実際の開設は別物。
- 実装：\`src/evidence-case-view-model.js\`（C Consumer guard）、\`src/evidence-case-page.js\`（DOM描画、参照原本一覧、JSONファイル読み込み）、\`evidence-case.css\`（独立スタイル）。\`tests/evidence-case-view-model.test.js\`（不正な安全フラグ、URL/SHA/資料時点改変、個人情報漏洩、旧新学校住所統合などの否認）。
- ビルドとテスト：\`cd frontend && npm test && npm run lint && npm run build\`。CI required \`test\` が成功しても、実ブラウザのレスポンシブ・C実出力の手動投入、スクリーンリーダー、ステージングの動作確認は別途必要。

**前提**：C provider Draft PR #136、公式原本のA PR #133、捕捉CI PR #139、B/E引継ぎ Issue #157。これらは統合前の作業で、プレビューは暫定。C生成JSONの安定供給経路が確立するまで自動取得・本番配信は導入しない。公開原本の利用/転載条件は別途確認する。HINANEXの「実災害の過去再現と成功/失敗3パターン」の精度実証とは別の補足デモ。


## 2026-10-13 Chromium実ブラウザでのC→B教育用Evidence表示検証

**静的サイトにおける実ブラウザ確認済み**。B用テスト `scripts/evidence-case-browser-smoke.mjs` は、C PR #136の生成コードから作った本物の公開用3状態JSONを読み込み、Chromiumのデスクトップ1365×900・モバイル390×844において、3状態・4原本HTTPSリンク・キーボードフォーカス・横はみ出し・不正JSONの拒否と旧画面クリア・明示的プレビュー復帰をチェックする。

- C→Bブラウザ用ジョブは共通Draft PR #139の `.github/workflows/edogawa-official-source-capture.yml` の `b-educational-chromium-smoke` に分離配置。Bは`frontend/**`のみを変更。
- 実施済みRunner: https://github.com/1kz-ma1/HINANEX/actions/runs/38349656269 、**Chromium browser smoke SUCCESS**。画像4枚（PC/スマホ正常・不正JSON表示）、`browser_smoke_manifest.json` はGitHub Actionsの7日間保持の非公開アーティファクト #11790550681 に保存。スクリーンショットは旧校舎の行政回答原文を含まない**公表資料の表示結果**のみ。
- 画面初期化直後の表示状態を待たずに期待値を確認していたテスト不備と、プレビューメッセージ文字列の誤記を修正した後に、ブラウザ検証を通過。前段の失敗を無視／skipして成功扱いにしたものではない。
- ブラウザテストはCIでの**静的ページ動作確認**であり、Render stagingのデプロイ済みURL、実機iOS Safari、音声読み上げ実機、通信断・非同期大量アクセスの実環境テストを保証しない。
- 検証対象は出典時点の教育用ケース。**避難先候補や実際の建物の利用可否・開設状態を示すものではない**。C人間承認0件・新規D洪水評価0件。`main`及びRenderは引き続き変更しない。

手元の実行にはテスト専用Playwrightのインストールが必要。実際のC公開用JSONをローカルに配置し、リポジトリルートで `python -m http.server 8765 --bind 127.0.0.1` を起動したうえで `node frontend/scripts/evidence-case-browser-smoke.mjs /path/to/C_public_educational_case.json /tmp/screenshots` を実行する。通常の静的画面にPlaywrightを追加配布しない。

## 2026-10-13 WebKit・Chromium自動アクセシビリティ受入（C実出力）

Cの `C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1` 実生成JSON（行政回答は両部署未連絡・原本ファイルなし）を使い、Linux上のPlaywright **WebKit / Chromium** の各 **デスクトップ1365×900 / モバイル390×844** で検証するCIを実装。`scripts/evidence-case-webkit-a11y-smoke.mjs` はB専用テストであり、製品版の依存にはPlaywright/axeを追加しない。

- 検査内容：3状態・4公表原本と `UNKNOWN` 表示、JSONのキーボード対応選択、Tab順（表示ボタン→プレビュー復帰、オフスクリーンの`input[type=file]`は `tabindex=-1`）、フォーカス枠、横はみ出し、axeによる WCAG 2.0/2.1 A/AA 対象ルール、不正な `OPEN` / 秘密文字列入りJSONの拒否と過去表示の消去・`role=alert`。
- GitHub Actions [#38350554576](https://github.com/1kz-ma1/HINANEX/actions/runs/38350554576) **全ジョブ成功**。WebKit / Chromium × PC / スマホ **4環境ともaxe自動検査違反0件**、4画像と検査結果JSONを個別のUNAPPROVEDアーティファクト #11790832612（ZIP SHA256 `507ab9a6095b7f4b56242157c818abf8acaa7a18e490fcfdc1d93b765861899c`、2026-10-20期限）に保管。
- 画像と出力Manifestを確認。モバイル横はみ出しなし、資料の時点付き3状態と `UNKNOWN` が見える。コントラストを含むaxe自動監査に加え、手動の文意・安全性審査は別。
- **非保証**：Playwright WebKit (Ubuntu) はApple実機 iOS Safari/VoiceOverではない。axeのA/AAルール0件は全WCAG適合や障害当事者ユーザーテストの代替ではない。Render stagingへのデプロイ、実際の災害時開設、施設同一性のC人的承認を一切行わない。
- 独立の共通Draft PR #139 `b-educational-webkit-a11y` ジョブで実行。B変更はすべて`frontend/**`、main/Renderへの変更・マージなし。人間のMerge CaptainがC依存先・ステージング・実機支援技術テストを承認するまでこのPRはDraft。
