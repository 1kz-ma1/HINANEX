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

## GISパフォーマンス改善のB受入仕様

施設検索・一覧（PERF-07）、panel / MutationObserver（PERF-08）、marker / cluster表示（PERF-09）は、現行RepositoryではE所有の`gis/**`に実装があります。B feature branchからGIS実装を変更せず、計測baseline、UI要件、データ意味を維持する受入条件、Desktop / Mobile回帰項目を[`docs/GIS_PERFORMANCE_UX_ACCEPTANCE.md`](docs/GIS_PERFORMANCE_UX_ACCEPTANCE.md)にまとめています。

BはEの実装後にこの仕様でUI/UXを確認します。性能改善を理由に、座標欠損record、`CANDIDATE` / `EXCLUDED` / `UNKNOWN`、DとGSIのSource区別、取得失敗状態を別の意味へ変換しません。


## チーム向け施設レビュー（JSON交換・完全ブラウザ内）

- エントリ：`/frontend/team-review.html`（静的HINANEXのFrontend）
- 単体配布：`frontend/team-review.html` を班員へ共有し、ブラウザで直接開く。スタイルと処理はHTMLに内蔵し、サーバー・外部JS・通信は不要。
- JSONサンプル：`frontend/mock/team-review-example.json` は**完全に合成データ**。実在施設に関する事実は含まず、正式データとして利用できない。
- アプリはJSONの読み込み・施設別の確認メモ/根拠URL/作業状態編集・JSON書き出しに対応。**自動保存なし・同時編集なし**。班員間では各自の書き出し版を別ファイルとして保存すること。最新UIは出典fingerprintと施設ID・施設情報の一致を検証したうえで**複数JSONのレビューを統合**できる（同施設の異なる記録は競合として全件中止）。未反映フォームや未書き出しの変更を失わないよう操作をブロック／タブ閉鎖を警告する。ただし実ファイルの保存完了自体を自動検証する機能はない。
- 公開サイト上のページには実施設の確認データを埋め込まず、配布専用JSONだけを**ユーザーがブラウザへ明示的に読み込む**。PRIVATE CSV/HTMLや未承認のABR/GSI候補座標は入力禁止。JSONのスキーマは厳密で、余計なフィールドは拒否する。
- オフラインでもJSONをファイル選択で読み込める（file://からのfetchを使わない）。生成JSONもブラウザ内のBlob APIでダウンロードする。
- 全レコードの施設位置・災害適合性・開設状況・経路安全性は**未承認**。作業状態`evidence_found`は資料を見つけたという意味でのみ使用。出力に`approved_for_map:false` / `data_promotion_authorized:false` / `official_facility_positions_accepted:0`を必須とする。
- Schema（v1、入力時に余分なフィールドを拒否）：
  `schema_id:hinanex.team-review.v1`
  `dataset:{id,region,source_fingerprint}`（source_fingerprintは64桁hex）
  `safety:{approved_for_map:false,data_promotion_authorized:false,official_facility_positions_accepted:0}`
  `records:[{id,name,address,priority:P0|P1|P2,issues:[],sources:[{title,url}],review:{status,checks:{official_source,identity,address,position_evidence},reviewer,notes,evidence_url,reviewed_at}}]`
  status = `not_reviewed|in_progress|evidence_found|needs_follow_up`。位置の評価結果、事実関係の採否、避難先としての安全性を一切表現しない。
- 共有パッケージを生成するときは、**行政が公表している名称・掲載住所・共有を許可した確認理由/出典に限定すること**。座標、個別の実験経緯、監査に使用する秘密のID、GitHub認証情報は含めない。共有する相手や手段を確認する。
- ブラウザーに読み込んだJSONはサーバーへ送信せず、ローカルまたは公開サイトで動く同一HTMLに保持するだけ。ただし公式外部リンクを押した場合は訪問先へアクセスするので、通常の閲覧ログは発生する。
- テスト：`cd frontend && npm test`。Windows Edge/ChromeおよびMac Safariの**実機E2Eは未実施**。PRの統合判断前にファイルインポート・保存・再インポート、ブラウザ再読込後の非保持、オンラインとfile://の同等性を確認する。
- `main`はRenderへ自動デプロイされるため、Merge Captainの承認前にはマージしない。共有UIの一般公開はアクセス制御ではない。守秘の対象をブラウザーへ読み込む運用が必要な場合、別途認証・配布権限制御を設計する。


### 班員3人のJSON自動統合と差分確認（2026-10-22 Draft追加分）

- 最初に**基準JSON**を読み込む。その後「班員の結果JSONをまとめて取り込む」から最大20ファイルを選ぶ（例: 3人の提出ファイル）。**基準データを直接上書きしない**。成功時に表示状態を更新し、必ず別名JSONで書き出す。
- `dataset.id`/`dataset.region`/`dataset.source_fingerprint`、全施設数・不変の名称・住所・優先度・要確認コード・不変IDが揃うか厳密検証。同じ施設の異なるレビュー内容が見つかった場合は**統合全体を中止**し、元データを変更しない。片方の未確認初期状態は更新内容を持つ側を優先。レビュー内容が同じで日時だけ異なる場合は後の日時を保持。
- 基準ファイルの公式PDF資料リンクを維持し、読み込んだ他者JSONから `sources` を自動取り込まない。元データが更新されて参照資料が増えていても、既存レビューの統合を妨げないようにする。異なる施設情報に対するレビューは拒否。
- 「根拠・確認が未完了の施設だけ表示」チェックONがデフォルト。班員の確認記録として必要な4項目のチェック、`evidence_found`、根拠URLのどれかが欠けていれば確認待ちで表示する。**作業記録の形式上の完了は、実際の施設位置承認を意味しない**。
- `evidence_found` なのに根拠URLが空の記録（初期パイロットで実際に発生）は警告し、報告時に補足出典を記録する。
- 名古屋市公式の区別PDFリンクは D側PR #293 の `nagoya_team_review_official_sources.py` により**施設名+住所が完全一致**する9件のみに付与される（2026-09-01時点の公開一覧、2026-10-22確認）。PDF掲載は施設位置・現在の開設・災害適合性の立証とは異なる。
- まだE2E実機未確認。**Draft PR #292, #293, #283 の統合順・展開はMerge Captainの判断。** 自動共有・自動公開・レビューの正式認可は実装していない。
