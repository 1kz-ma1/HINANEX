# WP-001｜OPEN PR 45件の明細

調査基準は 2026-11-24 15:01 JST、main `62557a665f59254755a696e2e89292035ea4f6c2`。PR総数45、Draft 44、ready 1（[#325](https://github.com/1kz-ma1/HINANEX/pull/325)）。[棚卸し本体](HINANEX_WP001_ASSET_INVENTORY_20261124.md) に分類根拠、統合順、OPEN Issue、Owner判断を記載した。

以下のahead / behindは**固定mainと固定PR HEADを比較したコミット数**。stackの履歴や既取り込みの同等差分を含む場合がある。ファイル一覧は**各PRのbaseから見たPR差分**。 base欄はPR API応答のSHA。ブランチ一覧では全14件のbase refが存在。#429と#387のbase refはPR応答のbase SHAから前進していた。現在の親に対して#429は ahead 2 / behind 12（親 `3133d94e58f96b056a73d43ee0f984d94f9742f2`）、#387は ahead 2 / behind 2（親 `1847a67fbea13e9dad8ad4565da5876b25073550`）。対象の変更量と最新mainまでの距離は別に読む。CIはHEADのfull SHAと照合したGitHub Actionsの `test`（GitHub App ID 15368）。同HEADの複数試行は取得結果を併記し、main/stack親との組合せが変われば再検証を要する。

GitHub review thread APIで取得した範囲に未解決inline threadはなかった。指摘と監査はConversation本文・コメントに多く、レビュー件数やCIだけでは解消と判定しない。各明細の受入・未確認は取得した記録に基づく。明示記録がない場合は未確認として扱う。

| PR | 担当・範囲 | 分類 | 学内MVP | ahead / behind |
| --- | --- | --- | --- | --- |
| [#491](#pr-491) | B・F02 | FIX候補 | 補助 | 1 / 2 |
| [#489](#pr-489) | B・F01 | FIX候補 | 補助 | 1 / 2 |
| [#485](#pr-485) | B・F05 B2 | FIX候補 | 補助 | 2 / 2 |
| [#483](#pr-483) | B・MJ-01 | HOLD | 中心候補 | 2 / 3 |
| [#465](#pr-465) | Shared・判断台帳 | FIX候補 | 運用 | 2 / 10 |
| [#436](#pr-436) | E・F13 | HOLD | 補助候補 | 16 / 39 |
| [#432](#pr-432) | E・F04 S2 | DEFER候補 | 追加展示 | 2 / 42 |
| [#430](#pr-430) | E・F04 S1 | DEFER候補 | 追加展示 | 1 / 42 |
| [#429](#pr-429) | B・F09 | FIX候補 | P2任意 | 4 / 9 |
| [#396](#pr-396) | D・R0計画 | DEFER候補 | 拡張 | 15 / 67 |
| [#393](#pr-393) | C・R0独立検証 | HOLD | 拡張 | 17 / 64 |
| [#390](#pr-390) | D・R0取得 | DEFER候補 | 拡張 | 10 / 67 |
| [#387](#pr-387) | C・D03 | HOLD | 正式接続時必須 | 3 / 62 |
| [#386](#pr-386) | Shared・D03 | HOLD | 正式接続時必須 | 3 / 62 |
| [#385](#pr-385) | C・H0 | DEFER候補 | 拡張 | 4 / 64 |
| [#379](#pr-379) | D・H0 | DEFER候補 | 拡張 | 6 / 67 |
| [#371](#pr-371) | B・F05 B1 | HOLD | 再利用候補 | 18 / 3 |
| [#367](#pr-367) | A・F02 | HOLD | 実データ利用時 | 6 / 72 |
| [#365](#pr-365) | C・F02 | HOLD | 実データ利用時 | 8 / 73 |
| [#361](#pr-361) | Shared・運用 | CLOSE候補 | 履歴 | 2 / 73 |
| [#350](#pr-350) | B・F02検収 | CLOSE候補 | 履歴 | 1 / 77 |
| [#346](#pr-346) | Shared・仕様 | HOLD | 優先度の参照 | 44 / 78 |
| [#344](#pr-344) | Shared・戦略 | CLOSE候補 | 履歴 | 1 / 79 |
| [#339](#pr-339) | A・名古屋 | DEFER候補 | 拡張 | 2 / 79 |
| [#325](#pr-325) | C・GSI精度 | DEFER候補 | 拡張 | 1 / 122 |
| [#324](#pr-324) | D・名古屋 | DEFER候補 | 拡張 | 81 / 186 |
| [#323](#pr-323) | D・名古屋 | DEFER候補 | 拡張 | 16 / 122 |
| [#318](#pr-318) | D・位置証拠 | DEFER候補 | 拡張 | 4 / 133 |
| [#317](#pr-317) | D・位置証拠 | DEFER候補 | 拡張 | 1 / 133 |
| [#316](#pr-316) | C・市川 | DEFER候補 | 拡張 | 2 / 133 |
| [#311](#pr-311) | E・F03 | HOLD | 任意 | 1 / 149 |
| [#304](#pr-304) | D・洪水監査 | DEFER候補 | 実データ拡張 | 2 / 179 |
| [#302](#pr-302) | D・洪水抽出 | DEFER候補 | 実データ拡張 | 1 / 179 |
| [#298](#pr-298) | B・名古屋 | DEFER候補 | 拡張 | 22 / 180 |
| [#297](#pr-297) | D・名古屋 | DEFER候補 | 拡張 | 100 / 186 |
| [#296](#pr-296) | D・名古屋 | DEFER候補 | 拡張 | 97 / 186 |
| [#295](#pr-295) | D・名古屋 | DEFER候補 | 拡張 | 90 / 186 |
| [#293](#pr-293) | D・名古屋 | DEFER候補 | 拡張 | 84 / 186 |
| [#292](#pr-292) | B・名古屋 | DEFER候補 | 拡張 | 17 / 180 |
| [#289](#pr-289) | Shared・名古屋CI | DEFER候補 | 拡張 | 1 / 183 |
| [#283](#pr-283) | D・名古屋 | DEFER候補 | 拡張 | 73 / 186 |
| [#282](#pr-282) | Shared・運用 | CLOSE候補 | 履歴 | 3 / 187 |
| [#272](#pr-272) | D・3地域 | DEFER候補 | 拡張 | 6 / 195 |
| [#271](#pr-271) | A・江戸川 | HOLD | 実データ拡張 | 3 / 189 |
| [#136](#pr-136) | C・江戸川 | CLOSE候補 | 実データ拡張 | 92 / 380 |

## PR 491

**[#491](https://github.com/1kz-ma1/HINANEX/pull/491) fix(frontend): F02で検索を保持したまま施設選択を解除する (#490)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・F02。検索保持と本人選択解除 |
| base | `main` @ `54e8c71c86656ec7ed6c02e94567ab60985da9f2` |
| HEAD | `fix/b-f02-clear-record-selection-20261124` @ `c7f57ab03eaa8dbb95b0936b12d7aab47a02d08c` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...c7f57ab03eaa8dbb95b0936b12d7aab47a02d08c) ahead 1 / behind 2 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/45329327748/job/138226409345) |
| 前提・契約 | 前提PRなし。DQA-002 |
| Owner・独立QA | 実装側Chrome記録あり。独立B-QA依頼済み |
| 安全・非公開・公開条件 | 既存F02非公開。権利・公式原本は別 |
| 未検証・次の最小作業 | main赤の切り分け後に追従し、同HEADでF02独立ChromeとCI |
| 暫定分類・MVP | FIX候補 / 補助。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/491/files)（4件）。関連Conversation記録 [7122441947](https://github.com/1kz-ma1/HINANEX/pull/491#issuecomment-7122441947)

<details>
<summary>パス・変更行数</summary>

- `frontend/f02.css`（modified、+2/−1）
- `frontend/f02.html`（modified、+1/−0）
- `frontend/src/f02-page.js`（modified、+20/−9）
- `frontend/tests/f02-page-http-browser.test.cjs`（modified、+12/−0）

</details>

## PR 489

**[#489](https://github.com/1kz-ma1/HINANEX/pull/489) fix(frontend): F01の単一ページに表示件数を案内する (#488)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・F01。単一ページ件数と複数ページへの復帰 |
| base | `main` @ `54e8c71c86656ec7ed6c02e94567ab60985da9f2` |
| HEAD | `fix/b-f01-single-page-results-20261124` @ `c5602d4a87f6e460987e70f55ecabcc339fdde75` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...c5602d4a87f6e460987e70f55ecabcc339fdde75) ahead 1 / behind 2 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/45327116354/job/138219263316) |
| 前提・契約 | 前提PRなし。DQA-008 |
| Owner・独立QA | 実装側Chrome記録あり。独立B-QA依頼済み |
| 安全・非公開・公開条件 | 合成と公式原値の境界を保持 |
| 未検証・次の最小作業 | 追従後に件数・0件・失敗・複数ページを再検証 |
| 暫定分類・MVP | FIX候補 / 補助。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/489/files)（3件）。関連Conversation記録 [7122145178](https://github.com/1kz-ma1/HINANEX/pull/489#issuecomment-7122145178)

<details>
<summary>パス・変更行数</summary>

- `frontend/src/app.js`（modified、+36/−33）
- `frontend/styles.css`（modified、+1/−0）
- `frontend/tests/flood-scenario-http-browser.test.cjs`（modified、+4/−1）

</details>

## PR 485

**[#485](https://github.com/1kz-ma1/HINANEX/pull/485) fix(frontend): F05/B2で比較から本人の確認対象選択へ移動する (#484)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・F05 B2。比較から本人選択欄へフォーカス移動 |
| base | `main` @ `54e8c71c86656ec7ed6c02e94567ab60985da9f2` |
| HEAD | `fix/b-f05-b2-choice-navigation-20261124` @ `e93e73912fd31314173f57d8aca04b6808b13447` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...e93e73912fd31314173f57d8aca04b6808b13447) ahead 2 / behind 2 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/45324377911/job/138210308393) |
| 前提・契約 | 既存B2 #399。DQA-007 |
| Owner・独立QA | 実装側Chrome記録あり。独立B-QA依頼済み |
| 安全・非公開・公開条件 | 合成・ローカル限定。移動で選択しない |
| 未検証・次の最小作業 | 追従後に実DOM・選択非変更と配布除外を確認 |
| 暫定分類・MVP | FIX候補 / 補助。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/485/files)（2件）。関連Conversation記録 [7121786400](https://github.com/1kz-ma1/HINANEX/pull/485#issuecomment-7121786400)

<details>
<summary>パス・変更行数</summary>

- `frontend/prototypes/f05-flood-journey/b2-compare/browser-http.test.cjs`（modified、+27/−1）
- `frontend/prototypes/f05-flood-journey/b2-compare/index.html`（modified、+6/−5）

</details>

## PR 483

**[#483](https://github.com/1kz-ma1/HINANEX/pull/483) feat(frontend): MJ-01 isolated fixed synthetic journey shell (#362)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・MJ-01。固定架空Fixture・J02–05単一画面・明示選択 |
| base | `main` @ `f13ab2035c51cde0084d1463036f3148ff1b8ecc` |
| HEAD | `feature/b-mj01-synthetic-shell-20261124` @ `03d8f92a1c776664765dc898acdefa94730cc040` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...03d8f92a1c776664765dc898acdefa94730cc040) ahead 2 / behind 3 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/45314651750/job/138178455254) |
| 前提・契約 | 既存B2 #399。#371/#386のコード依存なし。独立Sharedガードが前提 |
| Owner・独立QA | DECISION-002の限定実装。独立モデル18/18受入。実BrowserとP2残件 |
| 安全・非公開・公開条件 | 7資材と将来ネストを除外するガード証明待ち。合成限定・公開NO-GO |
| 未検証・次の最小作業 | 固定HEADの独立Browserと配布除外を別々に実証。鮮度と再監査を司令塔判断 |
| 暫定分類・MVP | HOLD / 中心候補。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/483/files)（7件）。関連Conversation記録 [7120468008](https://github.com/1kz-ma1/HINANEX/pull/483#issuecomment-7120468008)、[7120650114](https://github.com/1kz-ma1/HINANEX/pull/483#issuecomment-7120650114)、[7120927222](https://github.com/1kz-ma1/HINANEX/pull/483#issuecomment-7120927222)

<details>
<summary>パス・変更行数</summary>

- `frontend/prototypes/f05-flood-journey/mj01-shell/README.md`（added、+27/−0）
- `frontend/prototypes/f05-flood-journey/mj01-shell/app.js`（added、+84/−0）
- `frontend/prototypes/f05-flood-journey/mj01-shell/browser-http.test.cjs`（added、+254/−0）
- `frontend/prototypes/f05-flood-journey/mj01-shell/fixtures.js`（added、+31/−0）
- `frontend/prototypes/f05-flood-journey/mj01-shell/index.html`（added、+43/−0）
- `frontend/prototypes/f05-flood-journey/mj01-shell/model.js`（added、+61/−0）
- `frontend/prototypes/f05-flood-journey/mj01-shell/model.test.js`（added、+57/−0）

</details>

## PR 465

**[#465](https://github.com/1kz-ma1/HINANEX/pull/465) docs(strategy): オーナー判断台帳 v0.1（既決・保留・公開ゲートの横断整理）**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | Shared・判断台帳。判断索引と11/24決裁4件を保持 |
| base | `main` @ `51cf0150b388d249702b198ed2c52689a50a8381` |
| HEAD | `docs/owner-decision-register-20261120` @ `8ef00d1eb7dec144aa94fdb611b82c464a351eef` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...8ef00d1eb7dec144aa94fdb611b82c464a351eef) ahead 2 / behind 10 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/45314132298/job/138176738211) |
| 前提・契約 | 個別の決裁コメント、Ownerレビュー |
| Owner・独立QA | Owner採用待ち。追補の#428実行HOLD表記は当時のもの |
| 安全・非公開・公開条件 | 決裁・原本受入・公開の記録を別管理 |
| 未検証・次の最小作業 | 履歴を保ったまま司令塔レビューで#428統合後とWP-001参照を整理 |
| 暫定分類・MVP | FIX候補 / 運用。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/465/files)（1件）。

<details>
<summary>パス・変更行数</summary>

- `docs/strategy/HINANEX_OWNER_DECISION_REGISTER_20261120.md`（added、+132/−0）

</details>

## PR 436

**[#436](https://github.com/1kz-ma1/HINANEX/pull/436) feat(gis): F13 clarify flood evidence and unknown states in F01**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | E・F13。F01洪水根拠・未確認表示と独立スモーク |
| base | `main` @ `427a6f09ef436abe34a755f1f7bdfb31f20bae89` |
| HEAD | `feature/e-f13-flood-evidence-20261118` @ `bbdef1f05852e1582b86be72dafae05d2f74131a` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...bbdef1f05852e1582b86be72dafae05d2f74131a) ahead 16 / behind 39 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/44221598401/job/134524541491) |
| 前提・契約 | F04/F07のコード依存なし。F04とGIS試験入口が重複 |
| Owner・独立QA | Mac v1.1 75項目と3画面を限定受入。物理端末・公式GSI取得未実施 |
| 安全・非公開・公開条件 | 実GSIの版、範囲、安全、実配布・公開受入は別 |
| 未検証・次の最小作業 | 隔離候補QAとmain差分の再監査。展示採用範囲を決定 |
| 暫定分類・MVP | HOLD / 補助候補。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/436/files)（8件）。関連Conversation記録 [7027778378](https://github.com/1kz-ma1/HINANEX/pull/436#issuecomment-7027778378)、[7027870457](https://github.com/1kz-ma1/HINANEX/pull/436#issuecomment-7027870457)、[7028558118](https://github.com/1kz-ma1/HINANEX/pull/436#issuecomment-7028558118)

<details>
<summary>パス・変更行数</summary>

- `gis/docs/F13_FLOOD_EVIDENCE_VISIBILITY_20261118.md`（added、+87/−0）
- `gis/gis/css/map_first.css`（modified、+6/−2）
- `gis/gis/index.html`（modified、+8/−4）
- `gis/gis/js/hazard_information.js`（modified、+37/−8）
- `gis/tests/guided_tour_compare.test.js`（modified、+1/−1）
- `gis/tests/hazard_information.test.js`（modified、+52/−2）
- `gis/tests/hazard_information_browser.js`（modified、+26/−2）
- `gis/tests/map_controller.test.js`（modified、+7/−4）

</details>

## PR 432

**[#432](https://github.com/1kz-ma1/HINANEX/pull/432) feat(gis): F04 S2 compare fictional timeline steps (stacked on #430)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | E・F04 S2。架空タイムラインの二時点差分 |
| base | `feature/e-f04-synthetic-timeline-s1-20261117` @ `6b1eb875ea69768829cfdf6abf019f931bd73f36` |
| HEAD | `feature/e-f04-s2-change-comparison-20261117` @ `23e738b803464617d09d1973659659053401924e` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...23e738b803464617d09d1973659659053401924e) ahead 2 / behind 42 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/44021716716/job/133832491592) |
| 前提・契約 | stack親#430。S1 UI・固定合成データ |
| Owner・独立QA | 独立localhost Chrome記録あり。物理・採用未確認 |
| 安全・非公開・公開条件 | 非公開、現実洪水予測と切り離す |
| 未検証・次の最小作業 | S1採否後にstack更新、独立Browser・配布境界 |
| 暫定分類・MVP | DEFER候補 / 追加展示。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/432/files)（10件）。関連Conversation記録 [6939115468](https://github.com/1kz-ma1/HINANEX/pull/432#issuecomment-6939115468)

<details>
<summary>パス・変更行数</summary>

- `gis/prototypes/f04-synthetic-timeline/README.md`（modified、+35/−0）
- `gis/prototypes/f04-synthetic-timeline/comparison-app.js`（added、+141/−0）
- `gis/prototypes/f04-synthetic-timeline/comparison-model.js`（added、+144/−0）
- `gis/prototypes/f04-synthetic-timeline/index.html`（modified、+59/−0）
- `gis/prototypes/f04-synthetic-timeline/style.css`（modified、+34/−0）
- `gis/prototypes/f04-synthetic-timeline/test-browser.cjs`（modified、+2/−1）
- `gis/prototypes/f04-synthetic-timeline/test-comparison-browser.cjs`（added、+113/−0）
- `gis/prototypes/f04-synthetic-timeline/test-comparison-keyboard.cjs`（added、+98/−0）
- `gis/prototypes/f04-synthetic-timeline/test-comparison-node.cjs`（added、+190/−0）
- `gis/tests/map_controller.test.js`（modified、+2/−0）

</details>

## PR 430

**[#430](https://github.com/1kz-ma1/HINANEX/pull/430) feat(gis): private F04 synthetic flood timeline S1 (NO-GO)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | E・F04 S1。操作可能な架空洪水の模式グリッド |
| base | `main` @ `6047bcbc1918e19721885385c85fc74cf7b9b156` |
| HEAD | `feature/e-f04-synthetic-timeline-s1-20261117` @ `6b1eb875ea69768829cfdf6abf019f931bd73f36` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...6b1eb875ea69768829cfdf6abf019f931bd73f36) ahead 1 / behind 42 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/44020029227/job/133827044632) |
| 前提・契約 | コード前提なし。#432の親 |
| Owner・独立QA | 独立hosted Chrome記録あり。物理・採用未確認 |
| 安全・非公開・公開条件 | 合成・ローカル。Render対象外の構造と実配布は別 |
| 未検証・次の最小作業 | 展示採否を確定。採用時はmain同期、ガードと試験重複を確認 |
| 暫定分類・MVP | DEFER候補 / 追加展示。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/430/files)（9件）。関連Conversation記録 [6938811601](https://github.com/1kz-ma1/HINANEX/pull/430#issuecomment-6938811601)

<details>
<summary>パス・変更行数</summary>

- `gis/prototypes/f04-synthetic-timeline/README.md`（added、+46/−0）
- `gis/prototypes/f04-synthetic-timeline/app.js`（added、+87/−0）
- `gis/prototypes/f04-synthetic-timeline/index.html`（added、+59/−0）
- `gis/prototypes/f04-synthetic-timeline/style.css`（added、+16/−0）
- `gis/prototypes/f04-synthetic-timeline/synthetic-data.js`（added、+23/−0）
- `gis/prototypes/f04-synthetic-timeline/test-browser.cjs`（added、+97/−0）
- `gis/prototypes/f04-synthetic-timeline/test-node.cjs`（added、+151/−0）
- `gis/prototypes/f04-synthetic-timeline/timeline-model.js`（added、+130/−0）
- `gis/tests/map_controller.test.js`（modified、+3/−0）

</details>

## PR 429

**[#429](https://github.com/1kz-ma1/HINANEX/pull/429) feat(frontend): independent F09 preparedness checklist prototype (#423)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・F09。保存しない備えチェックリスト |
| base | `shared/f09-unpublished-render-guard-20261117` @ `ee3b341a0f9bb553b6dbb0aba7fc32d3ece4d228` |
| HEAD | `feature/b-f09-preparedness-20261117` @ `a315f5a04bbc6ff76aa891aadbbc130b446c0658` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...a315f5a04bbc6ff76aa891aadbbc130b446c0658) ahead 4 / behind 9 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/44663648984/job/136047606027) |
| 前提・契約 | stack親#428はsquash済み。#423 |
| Owner・独立QA | P2非公開試作のみ採用。旧stackで独立QAあり |
| 安全・非公開・公開条件 | 出典、表示、実機、公開は未受入 |
| 未検証・次の最小作業 | main基準で本体だけを再準備し8資材、除外、CIを独立再確認 |
| 暫定分類・MVP | FIX候補 / P2任意。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/429/files)（8件）。関連Conversation記録 [6938286295](https://github.com/1kz-ma1/HINANEX/pull/429#issuecomment-6938286295)、[7028842690](https://github.com/1kz-ma1/HINANEX/pull/429#issuecomment-7028842690)

<details>
<summary>パス・変更行数</summary>

- `frontend/docs/F09_PREPAREDNESS_CHECKLIST_PROTOTYPE_20261117.md`（added、+73/−0）
- `frontend/package.json`（modified、+2/−2）
- `frontend/prototypes/f09-preparedness/app.js`（added、+112/−0）
- `frontend/prototypes/f09-preparedness/index.html`（added、+30/−0）
- `frontend/prototypes/f09-preparedness/model.js`（added、+58/−0）
- `frontend/prototypes/f09-preparedness/styles.css`（added、+6/−0）
- `frontend/tests/f09-preparedness-browser.cjs`（added、+184/−0）
- `frontend/tests/f09-preparedness.test.js`（added、+61/−0）

</details>

## PR 396

**[#396](https://github.com/1kz-ma1/HINANEX/pull/396) feat(d): derive R0 Niigata candidate GSI tile plan from official DMS anchor**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・R0計画。新潟候補公的位置から明示タイル計画 |
| base | `feature/d-r0-gsi-four-cell-batch-20261116` @ `c9948eb7e6a8479a65315ddfb7694e4e490a4be3` |
| HEAD | `feature/d-r0-niigata-anchor-plan-20261116` @ `67a1bbf8668f66a578d24a141db55b0a28a98faa` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...67a1bbf8668f66a578d24a141db55b0a28a98faa) ahead 15 / behind 67 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43795501649/job/133063281015) |
| 前提・契約 | stack親#390、さらに#379。#395/#388 |
| Owner・独立QA | D Mac報告あり。人間受入なし |
| 安全・非公開・公開条件 | 施設・行政界・公開に昇格しない |
| 未検証・次の最小作業 | R0採用後、根拠版と4セル承認を照合 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/396/files)（3件）。

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/GSI_R0_NIIGATA_CANDIDATE_20261116.md`（added、+92/−0）
- `pipeline/src/hinanex/gsi_r0_anchor_plan.py`（added、+169/−0）
- `pipeline/tests/test_gsi_r0_anchor_plan.py`（added、+152/−0）

</details>

## PR 393

**[#393](https://github.com/1kz-ma1/HINANEX/pull/393) test(c): audit GSI R0 four hazard/tile raw sources and opt-in HTTPS replay**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | C・R0独立検証。4セル照合と任意HTTPS独立リプレイ |
| base | `feature/c-h0-skhb02-https-replay-20261116` @ `d069644d9cc6b07107d41be47b8e47327d46dc33` |
| HEAD | `feature/c-r0-four-cell-https-replay-20261116` @ `85369d478671b02a006afbb5162972febf9e6177` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...85369d478671b02a006afbb5162972febf9e6177) ahead 17 / behind 64 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43990409762/job/133729226107) |
| 前提・契約 | stack親#385。データは#390 |
| Owner・独立QA | #401で原本バイト3/4一致報告。A洪水の順序差と原本SHA不一致 |
| 安全・非公開・公開条件 | 人間承認・公開0。原本Git外 |
| 未検証・次の最小作業 | D/C原本・receiptで起因と厳格一致基準を審査 |
| 暫定分類・MVP | HOLD / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/393/files)（6件）。関連Conversation記録 [6907707354](https://github.com/1kz-ma1/HINANEX/pull/393#issuecomment-6907707354)

<details>
<summary>パス・変更行数</summary>

- `validation/docs/GSI_R0_A_FLOOD_MISMATCH_DIAGNOSTIC_20261116.md`（added、+138/−0）
- `validation/docs/GSI_R0_FOUR_CELL_C_REPLAY_20261116.md`（added、+80/−0）
- `validation/validation/diagnose_gsi_r0_a_flood_delta.py`（added、+252/−0）
- `validation/validation/test_diagnose_gsi_r0_a_flood_delta.py`（added、+452/−0）
- `validation/validation/test_verify_gsi_r0_four_cell_replay.py`（added、+365/−0）
- `validation/validation/verify_gsi_r0_four_cell_replay.py`（added、+450/−0）

</details>

## PR 390

**[#390](https://github.com/1kz-ma1/HINANEX/pull/390) feat(d): opt-in GSI R0 four-cell source capture matrix (two tiles x two hazards)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・R0取得。2×2明示取得と未承認台帳 |
| base | `feature/d-h0-gsi-dual-hazard-preflight-20261113` @ `14e758553460c0f7ff11e122d413fc1dc927fd55` |
| HEAD | `feature/d-r0-gsi-four-cell-batch-20261116` @ `c9948eb7e6a8479a65315ddfb7694e4e490a4be3` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...c9948eb7e6a8479a65315ddfb7694e4e490a4be3) ahead 10 / behind 67 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43791982616/job/133052260379) |
| 前提・契約 | stack親#379。C照合#393 |
| Owner・独立QA | Mac D 4/4は報告値。C・人間別 |
| 安全・非公開・公開条件 | 既定dry-run。原本Git外。公開HOLD |
| 未検証・次の最小作業 | 再開時に親と#401の受入条件を確定 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/390/files)（3件）。

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/GSI_R0_FOUR_CELL_BATCH_20261116.md`（added、+90/−0）
- `pipeline/src/hinanex/gsi_r0_pilot_batch.py`（added、+286/−0）
- `pipeline/tests/test_gsi_r0_pilot_batch.py`（added、+276/−0）

</details>

## PR 387

**[#387](https://github.com/1kz-ma1/HINANEX/pull/387) test(c): preflight draft S0→UI synthetic display projection**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | C・D03。S0からの合成表示草案を独立検証 |
| base | `docs/s0-ui-display-contract-proposal-20261116` @ `a258df11595fe2082b9e0ce02e2f5157e2bbd767` |
| HEAD | `feature/c-s0-ui-display-draft-preflight-20261116` @ `290cc1b693b781da5d7760bd3b7864b77269a4aa` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...290cc1b693b781da5d7760bd3b7864b77269a4aa) ahead 3 / behind 62 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43791529999/job/133050824044) |
| 前提・契約 | stack親#386。S0 #376/#384 |
| Owner・独立QA | 草案のC検証。Option B v1.0.1の再監査は別 |
| 安全・非公開・公開条件 | 合成限定、B接続・正式Contract未採用 |
| 未検証・次の最小作業 | 追補を独立再監査し、最終草案に対するC試験を合意 |
| 暫定分類・MVP | HOLD / 正式接続時必須。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/387/files)（4件）。

<details>
<summary>パス・変更行数</summary>

- `validation/docs/S0_UI_DISPLAY_DRAFT_C_PREFLIGHT_V01.md`（added、+38/−0）
- `validation/fixtures/s0_ui_display_draft_preflight_v01.json`（added、+544/−0）
- `validation/validation/test_verify_s0_ui_projection_draft.py`（added、+188/−0）
- `validation/validation/verify_s0_ui_projection_draft.py`（added、+246/−0）

</details>

## PR 386

**[#386](https://github.com/1kz-ma1/HINANEX/pull/386) docs(shared): propose S0 synthetic-only UI display boundary v0.1**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | Shared・D03。S0→UI 14キー表示草案と設計論点 |
| base | `main` @ `d461f5912216b54d3f30a2833eb12c08860b4e74` |
| HEAD | `docs/s0-ui-display-contract-proposal-20261116` @ `1847a67fbea13e9dad8ad4565da5876b25073550` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...1847a67fbea13e9dad8ad4565da5876b25073550) ahead 3 / behind 62 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/44681892106/job/136106997697) |
| 前提・契約 | S0 #376/#384。#387独立C |
| Owner・独立QA | DECISION-003でB案は設計第一候補。v1.0監査のP1/P2残件 |
| 安全・非公開・公開条件 | 合成のみ。実接続・採用・公開はHOLD |
| 未検証・次の最小作業 | 固定原本・v1.0.1を独立再監査。信頼確立等とD/B/C承認を整理 |
| 暫定分類・MVP | HOLD / 正式接続時必須。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/386/files)（2件）。関連Conversation記録 [7120367201](https://github.com/1kz-ma1/HINANEX/pull/386#issuecomment-7120367201)、[7120650654](https://github.com/1kz-ma1/HINANEX/pull/386#issuecomment-7120650654)、[7120927778](https://github.com/1kz-ma1/HINANEX/pull/386#issuecomment-7120927778)

<details>
<summary>パス・変更行数</summary>

- `docs/strategy/S0_UI_DISPLAY_PROJECTION_DRAFT_V01.schema.json`（added、+183/−0）
- `docs/strategy/S0_UI_DISPLAY_PROJECTION_PROPOSAL_V01.md`（added、+143/−0）

</details>

## PR 385

**[#385](https://github.com/1kz-ma1/HINANEX/pull/385) test(c): independently replay GSI skhb02 HTTPS bytes against H0 raw receipt**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | C・H0。skhb02独立HTTPSバイト照合 |
| base | `main` @ `c5ec8848c9902567fed10d47b7d1142472550ac7` |
| HEAD | `feature/c-h0-skhb02-https-replay-20261116` @ `d069644d9cc6b07107d41be47b8e47327d46dc33` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...d069644d9cc6b07107d41be47b8e47327d46dc33) ahead 4 / behind 64 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43788788588/job/133042285717) |
| 前提・契約 | データ依存#379の原本・receipt。#380 |
| Owner・独立QA | Macで別HTTPS一致と報告。WP-001は実バイト未取得 |
| 安全・非公開・公開条件 | 施設同一性・利用条件・公開HOLD |
| 未検証・次の最小作業 | 採用時に独立証跡と人間承認を回収 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/385/files)（3件）。関連Conversation記録 [6905337162](https://github.com/1kz-ma1/HINANEX/pull/385#issuecomment-6905337162)

<details>
<summary>パス・変更行数</summary>

- `validation/docs/GSI_SKHB02_INDEPENDENT_HTTPS_REPLAY_20261116.md`（added、+78/−0）
- `validation/validation/test_verify_gsi_skhb02_https_replay.py`（added、+197/−0）
- `validation/validation/verify_gsi_skhb02_https_replay.py`（added、+254/−0）

</details>

## PR 379

**[#379](https://github.com/1kz-ma1/HINANEX/pull/379) feat(d): add offline GSI skhb01/skhb02 hazard source preflight (H0)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・H0。公式GSI 1タイルの明示取得・構造検査 |
| base | `main` @ `55bbf7251e84ca4f375bb265b37f595027781b8c` |
| HEAD | `feature/d-h0-gsi-dual-hazard-preflight-20261113` @ `14e758553460c0f7ff11e122d413fc1dc927fd55` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...14e758553460c0f7ff11e122d413fc1dc927fd55) ahead 6 / behind 67 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43365390606/job/131688472759) |
| 前提・契約 | #378、C #385。#390の親 |
| Owner・独立QA | D Mac取得報告。独立受入別 |
| 安全・非公開・公開条件 | オプトイン・原本Git外・公開HOLD |
| 未検証・次の最小作業 | 親の必要性を判断し、D/C原本受領範囲を固定 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/379/files)（5件）。関連Conversation記録 [6905031129](https://github.com/1kz-ma1/HINANEX/pull/379#issuecomment-6905031129)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/GSI_H0_DUAL_HAZARD_PREFLIGHT_20261113.md`（added、+112/−0）
- `pipeline/src/hinanex/gsi_hazard_acquisition.py`（added、+217/−0）
- `pipeline/src/hinanex/gsi_hazard_preflight.py`（added、+206/−0）
- `pipeline/tests/test_gsi_hazard_acquisition.py`（added、+202/−0）
- `pipeline/tests/test_gsi_hazard_preflight.py`（added、+211/−0）

</details>

## PR 371

**[#371](https://github.com/1kz-ma1/HINANEX/pull/371) feat(frontend): F05 local-only safe F01→F02 navigation prototype (#362)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・F05 B1。地図→明示地域→F02手動導線 |
| base | `main` @ `f13ab2035c51cde0084d1463036f3148ff1b8ecc` |
| HEAD | `feature/b-f05-flood-journey-local-prototype-20261113` @ `469224f341669453293ff6d3f1de216f5806b828` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...469224f341669453293ff6d3f1de216f5806b828) ahead 18 / behind 3 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/44681860254/job/136106894436) |
| 前提・契約 | 統合済#357/#377。#362/#373、新ガード#482 |
| Owner・独立QA | 独立B1 QA受入を維持。最新再監査で公開除外漏れ |
| 安全・非公開・公開条件 | 追加Browser QAが既存ガード対象外、公開NO-GO |
| 未検証・次の最小作業 | #482独立Shared是正後、非force追従、同HEAD試験、6資材の配布除外 |
| 暫定分類・MVP | HOLD / 再利用候補。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/371/files)（6件）。関連Conversation記録 [7031548538](https://github.com/1kz-ma1/HINANEX/pull/371#issuecomment-7031548538)、[7119963653](https://github.com/1kz-ma1/HINANEX/pull/371#issuecomment-7119963653)、[7121704791](https://github.com/1kz-ma1/HINANEX/pull/371#issuecomment-7121704791)

<details>
<summary>パス・変更行数</summary>

- `frontend/docs/F05_MINIMAL_JOURNEY_20261113.md`（added、+82/−0）
- `frontend/prototypes/f05-flood-journey/README.md`（added、+25/−0）
- `frontend/prototypes/f05-flood-journey/index.html`（added、+129/−0）
- `frontend/src/f05-journey-model.js`（added、+31/−0）
- `frontend/tests/f05-journey-http-browser.test.cjs`（added、+106/−0）
- `frontend/tests/f05-journey.test.js`（added、+59/−0）

</details>

## PR 367

**[#367](https://github.com/1kz-ma1/HINANEX/pull/367) docs(a): record F02 Edogawa source license evidence and pending human gates**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | A・F02。CSV権利・表示・原本証跡 |
| base | `main` @ `57f0fc12ecb08d0e74fa4b36434674add8939135` |
| HEAD | `feature/a-f02-edogawa-reuse-review-20261113` @ `517aae6205e6b03e4a153d936dfa632f0cd00e5e` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...517aae6205e6b03e4a153d936dfa632f0cd00e5e) ahead 6 / behind 72 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43371946441/job/131709483371) |
| 前提・契約 | #366、#365との証拠関係 |
| Owner・独立QA | 技術監査と人間レビュー提出。Owner範囲と個別権利が未確定 |
| 安全・非公開・公開条件 | CSV固有例外、PNG、クレジット、公開HOLD |
| 未検証・次の最小作業 | 人間の受領範囲と権利根拠を署名記録 |
| 暫定分類・MVP | HOLD / 実データ利用時。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/367/files)（2件）。

<details>
<summary>パス・変更行数</summary>

- `data-research/docs/F02_EDOGAWA_CSV_RIGHTS_ACTUAL_SCAN_20261113.md`（added、+52/−0）
- `data-research/docs/F02_EDOGAWA_REUSE_SOURCE_PRE_REVIEW_20261113.md`（added、+185/−0）

</details>

## PR 365

**[#365](https://github.com/1kz-ma1/HINANEX/pull/365) test(c): independently audit F02 Edogawa CSV against D RegionExport**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | C・F02。CSVからD RegionExportへの独立全行照合 |
| base | `main` @ `e0d6f7a01644948acc8be787b727b22c926b2442` |
| HEAD | `feature/c-f02-edogawa-source-export-audit-20261113` @ `992d6d27e84acccd14364baae26010f29c5ce9a2` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...992d6d27e84acccd14364baae26010f29c5ce9a2) ahead 8 / behind 73 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/43346432345/job/131627958450)、[test FAILURE](https://github.com/1kz-ma1/HINANEX/actions/runs/43346432345/job/131626806071) |
| 前提・契約 | #364、既存#357。D v0.9 |
| Owner・独立QA | 技術照合記録あり。同HEADの失敗・成功両方を保持 |
| 安全・非公開・公開条件 | データ一致と権利、施設安全、公開は独立 |
| 未検証・次の最小作業 | 照合対象原本・版を受領。CI失敗/成功とC受入を照合 |
| 暫定分類・MVP | HOLD / 実データ利用時。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/365/files)（4件）。関連Conversation記録 [6841355869](https://github.com/1kz-ma1/HINANEX/pull/365#issuecomment-6841355869)

<details>
<summary>パス・変更行数</summary>

- `validation/docs/F02_EDOGAWA_PUBLICATION_GATE_20261113.md`（added、+60/−0）
- `validation/docs/F02_EDOGAWA_SOURCE_EXPORT_AUDIT_20261113.md`（added、+52/−0）
- `validation/validation/test_verify_f02_edogawa_source_export.py`（added、+134/−0）
- `validation/validation/verify_f02_edogawa_source_export.py`（added、+252/−0）

</details>

## PR 361

**[#361](https://github.com/1kz-ma1/HINANEX/pull/361) docs(strategy): establish two-track ownership for flood experience and platform coverage (#360)**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | Shared・運用。旧2トラックの運用草案 |
| base | `main` @ `e0d6f7a01644948acc8be787b727b22c926b2442` |
| HEAD | `docs/two-track-ownership-20261111` @ `e7e96d6f5825c6f73d70a89e884feab3e5e67ae4` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...e7e96d6f5825c6f73d70a89e884feab3e5e67ae4) ahead 2 / behind 73 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/42954199014/job/130305305483) |
| 前提・契約 | 同じロードマップを#344も変更。#360実決裁 |
| Owner・独立QA | 歴史的Owner決裁あり。文書PR未採用 |
| 安全・非公開・公開条件 | 文書。現行Scope Guardと人間決裁維持 |
| 未検証・次の最小作業 | 旧決裁を保持し、WP-001との差分を司令塔判定 |
| 暫定分類・MVP | CLOSE候補 / 履歴。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/361/files)（2件）。

<details>
<summary>パス・変更行数</summary>

- `docs/strategy/HINANEX_THREE_AXIS_ROADMAP_2027-02-09.md`（modified、+13/−0）
- `docs/strategy/HINANEX_TWO_TRACK_OWNERSHIP_20261111.md`（added、+75/−0）

</details>

## PR 350

**[#350](https://github.com/1kz-ma1/HINANEX/pull/350) docs(frontend): F02 #348 班員提出ZIPの検収結果と統合ゲートを記録**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・F02検収。#348提出ZIPの検収・統合ゲート |
| base | `main` @ `3b60051a306fc0c3e01d9a1ba6f213992d9b3f22` |
| HEAD | `feature/b-f02-issue348-prototype-review-20261104` @ `fe8dced441dc5a57cffc604ce9859be4b2d030f3` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...fe8dced441dc5a57cffc604ce9859be4b2d030f3) ahead 1 / behind 77 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/41764430577/job/126359351655) |
| 前提・契約 | 後続#351/#357。仕様草案#346 |
| Owner・独立QA | 成果のソースは統合済み、元ZIP現物は未取得 |
| 安全・非公開・公開条件 | 原本・実機・機能公開の別条件 |
| 未検証・次の最小作業 | #351にない検収証跡だけを索引に保全して処分判定 |
| 暫定分類・MVP | CLOSE候補 / 履歴。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/350/files)（1件）。

<details>
<summary>パス・変更行数</summary>

- `frontend/docs/F02_ISSUE348_SUBMISSION_REVIEW_20261104.md`（added、+80/−0）

</details>

## PR 346

**[#346](https://github.com/1kz-ma1/HINANEX/pull/346) docs(shared): 19機能の将来仕様と単一の優先順位マスターを整備**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | Shared・仕様。19機能の将来仕様と優先順位案 |
| base | `main` @ `0461aae50a83bb4b77388a061966959d1096257e` |
| HEAD | `docs/feature-specs-20261030` @ `2b7ddb858e008a3da6c1391ecff39356d5630b17` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...2b7ddb858e008a3da6c1391ecff39356d5630b17) ahead 44 / behind 78 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/42937452491/job/130250931290) |
| 前提・契約 | main 3軸ロードマップ、#344/#361と競合の可能性 |
| Owner・独立QA | 提案。全19機能の包括採用なし |
| 安全・非公開・公開条件 | 公開・安全・個別採用は機能ごと |
| 未検証・次の最小作業 | 必要な仕様だけ現行Owner決裁と対照し確定 |
| 暫定分類・MVP | HOLD / 優先度の参照。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/346/files)（23件）。

<details>
<summary>パス・変更行数</summary>

- `docs/strategy/features/01_HAZARD_INFORMATION.md`（added、+72/−0）
- `docs/strategy/features/02_SHELTER_REFERENCE.md`（added、+55/−0）
- `docs/strategy/features/03_PRE_EVENT_PREPARATION.md`（added、+44/−0）
- `docs/strategy/features/04_FLOOD_TIMELINE.md`（added、+40/−0）
- `docs/strategy/features/05_INTEGRATED_JOURNEY.md`（added、+45/−0）
- `docs/strategy/features/06_OFFICIAL_ALERTS.md`（added、+62/−0）
- `docs/strategy/features/07_REFERENCE_ROUTE.md`（added、+40/−0）
- `docs/strategy/features/08_OFFLINE_MODE.md`（added、+40/−0）
- `docs/strategy/features/09_PREPAREDNESS_CHECKLIST.md`（added、+40/−0）
- `docs/strategy/features/10_FAMILY_CONTACT.md`（added、+40/−0）
- `docs/strategy/features/11_ACCESSIBILITY_I18N.md`（added、+40/−0）
- `docs/strategy/features/12_FAVORITE_PLACES.md`（added、+40/−0）
- `docs/strategy/features/13_DATA_STATUS_UI.md`（added、+40/−0）
- `docs/strategy/features/14_REGIONAL_DATA_COVERAGE.md`（added、+40/−0）
- `docs/strategy/features/15_CONTROLLED_CONTRIBUTION.md`（added、+40/−0）
- `docs/strategy/features/16_POST_DISASTER_SUPPORT.md`（added、+40/−0）
- `docs/strategy/features/17_TRAINING_DRILL.md`（added、+40/−0）
- `docs/strategy/features/18_SHELTER_OPERATIONS.md`（added、+40/−0）
- `docs/strategy/features/19_OPERATIONS_REVIEW.md`（added、+40/−0）
- `docs/strategy/features/DATA_STATES_AND_GATES.md`（added、+47/−0）
- `docs/strategy/features/FEATURE_PRIORITY_MASTER.md`（added、+105/−0）
- `docs/strategy/features/FEATURE_TEMPLATE.md`（added、+54/−0）
- `docs/strategy/features/README.md`（added、+58/−0）

</details>

## PR 344

**[#344](https://github.com/1kz-ma1/HINANEX/pull/344) docs(strategy): 体験先行・必要データ収集フェーズへの移行**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | Shared・戦略。体験先行・必要データ収集への移行案 |
| base | `main` @ `e696b2d035995011f7eae1698da7654eab9ddbb4` |
| HEAD | `docs/experience-first-plan-20261030` @ `b63b857be4ac7272f857081a14ef00075228e0d4` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...b63b857be4ac7272f857081a14ef00075228e0d4) ahead 1 / behind 79 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40994202271/job/123863407766) |
| 前提・契約 | main 3軸ロードマップ、#346/#361、#305 |
| Owner・独立QA | 旧案。体験優先はWP-001の基準で継承 |
| 安全・非公開・公開条件 | 文書、個別公開を承認しない |
| 未検証・次の最小作業 | 現行で失われる記述の有無を比較し索引化 |
| 暫定分類・MVP | CLOSE候補 / 履歴。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/344/files)（1件）。

<details>
<summary>パス・変更行数</summary>

- `docs/strategy/HINANEX_THREE_AXIS_ROADMAP_2027-02-09.md`（modified、+55/−14）

</details>

## PR 339

**[#339](https://github.com/1kz-ma1/HINANEX/pull/339) docs(data): 平針南コミュニティセンター Phase A調査の統合受領記録**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | A・名古屋。平針南の人間Phase A調査受領記録 |
| base | `main` @ `e696b2d035995011f7eae1698da7654eab9ddbb4` |
| HEAD | `feature/a-hirabari-minami-phasea-synthesis-20261030` @ `522018180971f8776b8f74e93a24480c423bb84c` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...522018180971f8776b8f74e93a24480c423bb84c) ahead 2 / behind 79 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/41749620867/job/126311188084) |
| 前提・契約 | #323/#286、別Phase B |
| Owner・独立QA | 班員の調査受領に限定。所在地入口の採否は別 |
| 安全・非公開・公開条件 | 位置・通行・安全の昇格なし |
| 未検証・次の最小作業 | 人間Phase Bと原本版を照合する時点で再開 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/339/files)（2件）。

<details>
<summary>パス・変更行数</summary>

- `data-research/reviews/2026-10-30-hirabari-minami-phase-a-human-confirmation-addendum.md`（added、+91/−0）
- `data-research/reviews/2026-10-30-hirabari-minami-stage9-phase-a-consolidation.md`（added、+69/−0）

</details>

## PR 325

**[#325](https://github.com/1kz-ma1/HINANEX/pull/325) [C][Draft] GSI全国CSVとGeoJSONの6桁丸め差を実座標相違から区別**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | C・GSI精度。CSV/GeoJSONの6桁丸め差分類 |
| base | `main` @ `b5ca9d00d55ee8ff3b597a7ac8b5b2d8818c7c77` |
| HEAD | `feature/c-gsi-csv-six-decimal-source-precision-20261027` @ `fc9adbc4b7af7ad205a65ed5e11b188345dd33ac` |
| 状態 | Ready for review。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...fc9adbc4b7af7ad205a65ed5e11b188345dd33ac) ahead 1 / behind 122 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40427528173/job/121936914857) |
| 前提・契約 | #316、市川GSI観測 |
| Owner・独立QA | 旧実原本再照合記録。現行版の再検証なし |
| 安全・非公開・公開条件 | 許容精度を施設同一性・位置承認に使わない |
| 未検証・次の最小作業 | 同版の原本を入手して適用ケースを固定 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/325/files)（3件）。関連Conversation記録 [6431029230](https://github.com/1kz-ma1/HINANEX/pull/325#issuecomment-6431029230)

<details>
<summary>パス・変更行数</summary>

- `validation/docs/GSI_CSV_GEOJSON_CANDIDATE_REPLAY_20261026.md`（modified、+11/−1）
- `validation/validation/compare_gsi_csv_geojson_candidates.py`（modified、+11/−4）
- `validation/validation/test_compare_gsi_csv_geojson_candidates.py`（modified、+27/−0）

</details>

## PR 324

**[#324](https://github.com/1kz-ma1/HINANEX/pull/324) [D][Draft] 名古屋P1 ABR重複参照点のローカル匿名来歴診断**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・名古屋。ABR重複参照点の匿名来歴診断 |
| base | `feature/d-nagoya-geocoding-pilot-20261021` @ `14e11116265208e3cd27afe72f02b7248c65ca9b` |
| HEAD | `feature/d-nagoya-stage9-abr-duplicate-diagnostic-20261026` @ `e59e96bbb96388a115591bb70cbb86ae77382e2a` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...e59e96bbb96388a115591bb70cbb86ae77382e2a) ahead 81 / behind 186 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40429148866/job/121942304289) |
| 前提・契約 | stack親#283、関連#323 |
| Owner・独立QA | Mac匿名診断の申告。PRIVATE原本未取得 |
| 安全・非公開・公開条件 | 外部送信や位置・入口承認なし |
| 未検証・次の最小作業 | #283採否後、匿名証拠のみ独立照合 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/324/files)（2件）。関連Conversation記録 [6430985658](https://github.com/1kz-ma1/HINANEX/pull/324#issuecomment-6430985658)、[6431074254](https://github.com/1kz-ma1/HINANEX/pull/324#issuecomment-6431074254)

<details>
<summary>パス・変更行数</summary>

- `pipeline/diagnose_nagoya_stage9_duplicate_abr.py`（added、+199/−0）
- `pipeline/tests/test_nagoya_stage9_duplicate_abr.py`（added、+163/−0）

</details>

## PR 323

**[#323](https://github.com/1kz-ma1/HINANEX/pull/323) docs(D): 名古屋P1 Stage 8目視記録とStage 9人間主導の位置受入手順**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・名古屋。Stage8/9目視・人間による位置受入手順 |
| base | `main` @ `b5ca9d00d55ee8ff3b597a7ac8b5b2d8818c7c77` |
| HEAD | `feature/d-nagoya-stage8-stage9-review-20261026` @ `b87929e036bd018e8ab9e1fe1c4a1d6e8ec4f34a` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...b87929e036bd018e8ab9e1fe1c4a1d6e8ec4f34a) ahead 16 / behind 122 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40979502982/job/123815725713) |
| 前提・契約 | #286、#283/#293/#292関連 |
| Owner・独立QA | Phase A/B進捗記録。最終位置未承認 |
| 安全・非公開・公開条件 | 人間審査・原本・公開が別 |
| 未検証・次の最小作業 | 最新レビュー票と位置判定責任者を確定 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/323/files)（6件）。関連Conversation記録 [6461724833](https://github.com/1kz-ma1/HINANEX/pull/323#issuecomment-6461724833)、[6461930090](https://github.com/1kz-ma1/HINANEX/pull/323#issuecomment-6461930090)、[6511792755](https://github.com/1kz-ma1/HINANEX/pull/323#issuecomment-6511792755)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/NAGOYA_STAGE8_STAGE9_HUMAN_LOCATION_REVIEW_20261026.md`（added、+260/−0）
- `pipeline/docs/NAGOYA_STAGE9_HIRABARIMINAMI_PHASE_A_ASSIGNMENT_20261028.md`（added、+58/−0）
- `pipeline/docs/NAGOYA_STAGE9_HIRABARIMINAMI_PHASE_B_AFTER_A_20261028.md`（added、+57/−0）
- `pipeline/docs/NAGOYA_STAGE9_OMORI_ELEMENTARY_PHASE_B_REVIEW_20261030.md`（added、+62/−0）
- `pipeline/docs/NAGOYA_STAGE9_PUBLIC_EVIDENCE_SURVEY_20261027.md`（added、+170/−0）
- `pipeline/docs/NAGOYA_STAGE9_REVIEW_GATE_CHECKLIST_20261027.md`（added、+50/−0）

</details>

## PR 318

**[#318](https://github.com/1kz-ma1/HINANEX/pull/318) [D][Draft] Location Verification Phase 2：敷地・入口候補の空間照合と審査キュー**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・位置証拠。敷地・入口候補空間照合と審査キュー |
| base | `feature/d-location-verification-triage-20261026` @ `b0c78f5be13fe034b6ecd554ed97282a8d24adcb` |
| HEAD | `feature/d-location-evidence-overlay-20261026` @ `f9f06a3867108fa048d38225e2ff13db76e8f05c` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...f9f06a3867108fa048d38225e2ff13db76e8f05c) ahead 4 / behind 133 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40266965137/job/121391363553) |
| 前提・契約 | stack親#317。#316は調査資料 |
| Owner・独立QA | 合成と既報CI。実ポリゴン・入口の独立検証なし |
| 安全・非公開・公開条件 | 実座標・誘導・公開禁止 |
| 未検証・次の最小作業 | 親と人間の地域・形状・入口の証拠が揃ってから再試験 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/318/files)（3件）。関連Conversation記録 [6408002215](https://github.com/1kz-ma1/HINANEX/pull/318#issuecomment-6408002215)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/LOCATION_VERIFICATION_ENGINE_PHASE2_20261026.md`（added、+38/−0）
- `pipeline/src/hinanex/location_evidence_overlay.py`（added、+250/−0）
- `pipeline/tests/test_location_evidence_overlay.py`（added、+142/−0）

</details>

## PR 317

**[#317](https://github.com/1kz-ma1/HINANEX/pull/317) [D][Draft] Location Verification Engine Phase 1：位置証拠の自動振り分け・誘導禁止ゲート**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・位置証拠。位置証拠の振り分け・誘導抑止 |
| base | `main` @ `879a9a0b76febd65ed7cdef2d44c3982ca01ed98` |
| HEAD | `feature/d-location-verification-triage-20261026` @ `b0c78f5be13fe034b6ecd554ed97282a8d24adcb` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...b0c78f5be13fe034b6ecd554ed97282a8d24adcb) ahead 1 / behind 133 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40265155845/job/121385838662) |
| 前提・契約 | #316の証拠に依存、コードは独立 |
| Owner・独立QA | 合成/旧rawパイロット。人間照合待ち |
| 安全・非公開・公開条件 | 位置・安全の判定フラグは保留 |
| 未検証・次の最小作業 | C人間証拠と行の結び付けを確認 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/317/files)（3件）。関連Conversation記録 [6407729672](https://github.com/1kz-ma1/HINANEX/pull/317#issuecomment-6407729672)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/LOCATION_VERIFICATION_ENGINE_PHASE1_20261026.md`（added、+41/−0）
- `pipeline/src/hinanex/location_verification.py`（added、+260/−0）
- `pipeline/tests/test_location_verification.py`（added、+139/−0）

</details>

## PR 316

**[#316](https://github.com/1kz-ma1/HINANEX/pull/316) [C][Draft] 市川市skhb02実データ29件の市公式資料との文字列照合（28一致・1保留）**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | C・市川。29件の文字列照合、28一致・1保留 |
| base | `main` @ `879a9a0b76febd65ed7cdef2d44c3982ca01ed98` |
| HEAD | `feature/c-ichikawa-skhb02-text-audit-20261026` @ `231dd89e4b5b8134369d16dc97943f26446936be` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...231dd89e4b5b8134369d16dc97943f26446936be) ahead 2 / behind 133 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40262736056/job/121378384092) |
| 前提・契約 | #317の証拠候補、#333関連 |
| Owner・独立QA | AI転記と画像目視記録。原本バイト・人間受入が不足 |
| 安全・非公開・公開条件 | 河川敷を座標や入口に確定しない |
| 未検証・次の最小作業 | 公式PDF・対象行を人間が照合 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/316/files)（6件）。関連Conversation記録 [6407044114](https://github.com/1kz-ma1/HINANEX/pull/316#issuecomment-6407044114)、[6407369180](https://github.com/1kz-ma1/HINANEX/pull/316#issuecomment-6407369180)、[6407414588](https://github.com/1kz-ma1/HINANEX/pull/316#issuecomment-6407414588)

<details>
<summary>パス・変更行数</summary>

- `validation/docs/ICHIKAWA_SKHB02_29_AI_TEXT_CROSSCHECK_20261026.md`（added、+100/−0）
- `validation/reference/ichikawa_skhb02_20261026_AI_UNREVIEWED.json`（added、+274/−0）
- `validation/reference/ichikawa_skhb02_20261026_SCREENSHOT_VISUAL_REVIEW_UNAPPROVED.json`（added、+387/−0）
- `validation/validation/compare_ichikawa_skhb02_text.py`（added、+190/−0）
- `validation/validation/test_compare_ichikawa_skhb02_text.py`（added、+108/−0）
- `validation/validation/test_ichikawa_skhb02_screenshot_review_manifest.py`（added、+67/−0）

</details>

## PR 311

**[#311](https://github.com/1kz-ma1/HINANEX/pull/311) [E][Draft] 事前入力を本人操作で端末内保存・削除するプライバシー基盤**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | E・F03。端末内保存/削除の別実装候補 |
| base | `main` @ `4c5baf5d5658cbb1361e47b983cbe08ba9622743` |
| HEAD | `feature/e-pre-event-local-optin-20261026` @ `4d22b2d649f169bf35448c7591f2ada21946dde3` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...4d22b2d649f169bf35448c7591f2ada21946dde3) ahead 1 / behind 149 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/40252894541/job/121348415579) |
| 前提・契約 | 統合済#306。F03/P-02 #359の仕様との差 |
| Owner・独立QA | 正式採用・端末永続・独立プライバシー確認待ち |
| 安全・非公開・公開条件 | 同意・端末内のみ、GPS等の追加不可 |
| 未検証・次の最小作業 | 保存キー、TTL、項目、明示読込をOwner決裁 |
| 暫定分類・MVP | HOLD / 任意。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/311/files)（4件）。

<details>
<summary>パス・変更行数</summary>

- `gis/docs/PRE_EVENT_PREPARATION_PRIVACY_20261026.md`（added、+21/−0）
- `gis/gis/js/pre_event_preparation.js`（added、+113/−0）
- `gis/tests/facility_list.test.js`（modified、+2/−0）
- `gis/tests/pre_event_preparation.test.js`（added、+99/−0）

</details>

## PR 304

**[#304](https://github.com/1kz-ma1/HINANEX/pull/304) [D][Draft] 洪水RegionExportの独立照合情報による整合検査（#301）**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・洪水監査。独立ピンとSHAによるRegionExport整合事前検査 |
| base | `feature/d-flood-selection-read-model-20261023` @ `cdee2b22fd967efb760489038a43eae1f1e36b6b` |
| HEAD | `feature/d-flood-export-integrity-preflight-20261023` @ `1ef150962f3c4eea0e81cc5ba1b8706dc59fe8f0` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...1ef150962f3c4eea0e81cc5ba1b8706dc59fe8f0) ahead 2 / behind 179 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39901395586/job/120243563805) |
| 前提・契約 | stack親#302。A/Cの原本意味照合 |
| Owner・独立QA | 合成検証。実RegionExport独立受入なし |
| 安全・非公開・公開条件 | オフライン。公式適合や安全を承認しない |
| 未検証・次の最小作業 | #302と実データ経路の必要性を判定 |
| 暫定分類・MVP | DEFER候補 / 実データ拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/304/files)（4件）。関連Conversation記録 [6357622107](https://github.com/1kz-ma1/HINANEX/pull/304#issuecomment-6357622107)

<details>
<summary>パス・変更行数</summary>

- `pipeline/audit_flood_export_selection.py`（added、+29/−0）
- `pipeline/docs/FLOOD_EXPORT_PREFLIGHT_20261023.md`（added、+48/−0）
- `pipeline/src/hinanex/flood_export_preflight.py`（added、+128/−0）
- `pipeline/tests/test_flood_export_preflight.py`（added、+161/−0）

</details>

## PR 302

**[#302](https://github.com/1kz-ma1/HINANEX/pull/302) [D][Draft] 洪水Scenarioの条件抽出・証跡照合read model（#301 Phase 1）**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・洪水抽出。洪水条件抽出読取モデル・証跡照合 |
| base | `main` @ `b679e8fc82a79ae93c7c919d44a90d5b42e1b677` |
| HEAD | `feature/d-flood-selection-read-model-20261023` @ `cdee2b22fd967efb760489038a43eae1f1e36b6b` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...cdee2b22fd967efb760489038a43eae1f1e36b6b) ahead 1 / behind 179 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39893395502/job/120218121813) |
| 前提・契約 | #301、契約 v0.9、#304の親。S1合成は別系列 |
| Owner・独立QA | 合成CI。A/C出典・位置、人間承認なし |
| 安全・非公開・公開条件 | UNKNOWN維持。consumerは別審査 |
| 未検証・次の最小作業 | 正式S1と役割が重なる範囲を確認 |
| 暫定分類・MVP | DEFER候補 / 実データ拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/302/files)（3件）。関連Conversation記録 [6356442211](https://github.com/1kz-ma1/HINANEX/pull/302#issuecomment-6356442211)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/SCENARIO_SELECTION_READ_MODEL.md`（added、+27/−0）
- `pipeline/src/hinanex/scenario_selection.py`（added、+184/−0）
- `pipeline/tests/test_scenario_selection.py`（added、+188/−0）

</details>

## PR 298

**[#298](https://github.com/1kz-ma1/HINANEX/pull/298) [B][Draft] 名古屋P1施設別PDF差分を班員レビューUIの優先確認キューへ接続**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・名古屋。オフラインレビューUIにPDF差分キュー |
| base | `feature/b-offline-team-review-20261022` @ `37aa6ab9374739c0045497a94db816cadeda169b` |
| HEAD | `feature/b-nagoya-diff-review-queue-20261022` @ `3c3e238410a75865ce95acce4b8baadbc98cba1c` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...3c3e238410a75865ce95acce4b8baadbc98cba1c) ahead 22 / behind 180 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39769042764/job/119791647307) |
| 前提・契約 | stack親#292。データ#296/#297→#295/#293/#283 |
| Owner・独立QA | 固定JSONの技術試験。人間PDF受入なし |
| 安全・非公開・公開条件 | ローカル、座標と安全フラグ昇格なし |
| 未検証・次の最小作業 | provider schemaと端末内動作を独立検証 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/298/files)（4件）。関連Conversation記録 [6339394859](https://github.com/1kz-ma1/HINANEX/pull/298#issuecomment-6339394859)

<details>
<summary>パス・変更行数</summary>

- `frontend/README.md`（modified、+10/−0）
- `frontend/docs/NAGOYA_PDF_DIFF_REVIEW_QUEUE_ACCEPTANCE_20261022.md`（added、+50/−0）
- `frontend/team-review.html`（modified、+174/−3）
- `frontend/tests/team-review.test.js`（modified、+131/−0）

</details>

## PR 297

**[#297](https://github.com/1kz-ma1/HINANEX/pull/297) [D][Draft] 名古屋P1の改版検知を合成PDF8シナリオで検証**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・名古屋。合成PDFの改版検知8シナリオ |
| base | `feature/d-nagoya-facility-change-triage-20261022` @ `fc28999ff5b3228c0e48fe479d198ef4269dce0d` |
| HEAD | `feature/d-nagoya-pdf-synthetic-mutations-20261022` @ `c629c38f4fb7d84b34511016f4edf7c0bd15318c` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...c629c38f4fb7d84b34511016f4edf7c0bd15318c) ahead 100 / behind 186 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39764823302/job/119777556085) |
| 前提・契約 | stack親#296→#295→#293→#283 |
| Owner・独立QA | Mac合成8ケース報告。実市版の独立再検証なし |
| 安全・非公開・公開条件 | 合成で実施設改版を判定しない |
| 未検証・次の最小作業 | 親採用後、合成ケースを必要な範囲で移す |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/297/files)（3件）。関連Conversation記録 [6338781701](https://github.com/1kz-ma1/HINANEX/pull/297#issuecomment-6338781701)、[6339223203](https://github.com/1kz-ma1/HINANEX/pull/297#issuecomment-6339223203)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/NAGOYA_SYNTHETIC_PDF_MUTATION_ACCEPTANCE_20261022.md`（added、+61/−0）
- `pipeline/manual_accept_nagoya_synthetic_pdf.py`（added、+189/−0）
- `pipeline/tests/test_nagoya_pdf_facility_change_triage.py`（modified、+52/−0）

</details>

## PR 296

**[#296](https://github.com/1kz-ma1/HINANEX/pull/296) [D][Draft] 名古屋P1の公式PDF行差分を施設別の確認候補に分離**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・名古屋。公式PDF行差分の施設別確認候補 |
| base | `feature/d-nagoya-official-source-watch-20261022` @ `e99d71b210a783bdbbb71aea5f0568768f57db31` |
| HEAD | `feature/d-nagoya-facility-change-triage-20261022` @ `fc28999ff5b3228c0e48fe479d198ef4269dce0d` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...fc28999ff5b3228c0e48fe479d198ef4269dce0d) ahead 97 / behind 186 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39763258863/job/119772381818) |
| 前提・契約 | stack親#295→#293→#283。#298が利用 |
| Owner・独立QA | Mac CLI報告。公式PDFの独立受入未確認 |
| 安全・非公開・公開条件 | 差分は人間確認候補 |
| 未検証・次の最小作業 | 親と再現可能な合成/公式版の対応を確認 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/296/files)（4件）。関連Conversation記録 [6332065617](https://github.com/1kz-ma1/HINANEX/pull/296#issuecomment-6332065617)、[6338541771](https://github.com/1kz-ma1/HINANEX/pull/296#issuecomment-6338541771)、[6338633100](https://github.com/1kz-ma1/HINANEX/pull/296#issuecomment-6338633100)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/NAGOYA_OFFICIAL_PDF_FACILITY_ROW_TRIAGE_20261022.md`（added、+62/−0）
- `pipeline/requirements_nagoya_pdf_triage.txt`（added、+1/−0）
- `pipeline/tests/test_nagoya_pdf_facility_change_triage.py`（added、+168/−0）
- `pipeline/triage_nagoya_pdf_facility_changes.py`（added、+296/−0）

</details>

## PR 295

**[#295](https://github.com/1kz-ma1/HINANEX/pull/295) [D][Draft] 名古屋の公式PDF5件を手動再取得しバイト更新だけ検出する独立検証**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・名古屋。固定PDF 5件の明示バイト比較 |
| base | `feature/d-nagoya-team-review-json-20261022` @ `4257937e056be5468d2eb2fc68a93a22be9fd5eb` |
| HEAD | `feature/d-nagoya-official-source-watch-20261022` @ `e99d71b210a783bdbbb71aea5f0568768f57db31` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...e99d71b210a783bdbbb71aea5f0568768f57db31) ahead 90 / behind 186 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39715946434/job/119617957130) |
| 前提・契約 | stack親#293→#283。#296の親 |
| Owner・独立QA | Mac手動報告。原本・版の独立確認未実施 |
| 安全・非公開・公開条件 | 明示取得、未審査baseline、公開なし |
| 未検証・次の最小作業 | 承認済取得範囲と親ブランチ採否を確定 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/295/files)（3件）。関連Conversation記録 [6331817532](https://github.com/1kz-ma1/HINANEX/pull/295#issuecomment-6331817532)、[6331937103](https://github.com/1kz-ma1/HINANEX/pull/295#issuecomment-6331937103)

<details>
<summary>パス・変更行数</summary>

- `pipeline/check_nagoya_official_pdf_updates.py`（added、+215/−0）
- `pipeline/docs/NAGOYA_ADDRESS_GEOCODING_PILOT_20261021.md`（modified、+23/−0）
- `pipeline/tests/test_nagoya_official_pdf_byte_watch.py`（added、+95/−0）

</details>

## PR 293

**[#293](https://github.com/1kz-ma1/HINANEX/pull/293) [Draft][D] Stage-7 PRIVATE → team-shareable review JSON**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・名古屋。PRIVATE台帳から共有可能JSONを生成 |
| base | `feature/d-nagoya-geocoding-pilot-20261021` @ `14e11116265208e3cd27afe72f02b7248c65ca9b` |
| HEAD | `feature/d-nagoya-team-review-json-20261022` @ `4257937e056be5468d2eb2fc68a93a22be9fd5eb` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...4257937e056be5468d2eb2fc68a93a22be9fd5eb) ahead 84 / behind 186 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39713964757/job/119611566523) |
| 前提・契約 | stack親#283。#292のJSON参照 |
| Owner・独立QA | 技術CIとP1照合報告。人間位置判定なし |
| 安全・非公開・公開条件 | PRIVATE原本非共有、共有項目と権限を別審査 |
| 未検証・次の最小作業 | 最小共有JSONの境界と漏えい防止を再監査 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/293/files)（5件）。関連Conversation記録 [6328252988](https://github.com/1kz-ma1/HINANEX/pull/293#issuecomment-6328252988)、[6331561898](https://github.com/1kz-ma1/HINANEX/pull/293#issuecomment-6331561898)

<details>
<summary>パス・変更行数</summary>

- `pipeline/docs/NAGOYA_ADDRESS_GEOCODING_PILOT_20261021.md`（modified、+70/−0）
- `pipeline/export_nagoya_team_review_json.py`（added、+173/−0）
- `pipeline/nagoya_team_review_official_sources.py`（added、+52/−0）
- `pipeline/tests/test_nagoya_team_review_export.py`（added、+118/−0）
- `pipeline/tests/test_nagoya_team_review_official_sources.py`（added、+56/−0）

</details>

## PR 292

**[#292](https://github.com/1kz-ma1/HINANEX/pull/292) [Draft][B] Offline team review HTML + JSON import/export**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | B・名古屋。オフラインHTMLとレビューJSON入出力 |
| base | `main` @ `6b71b0bc88174ed888e146cdcbc1560e7cb04214` |
| HEAD | `feature/b-offline-team-review-20261022` @ `37aa6ab9374739c0045497a94db816cadeda169b` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...37aa6ab9374739c0045497a94db816cadeda169b) ahead 17 / behind 180 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39715884308/job/119617755849) |
| 前提・契約 | 固定JSON契約、#293と関連。#298の親 |
| Owner・独立QA | 班員作業支援。独立実機受入未確認 |
| 安全・非公開・公開条件 | 作業記録を一般公開・配布しない |
| 未検証・次の最小作業 | 正式共有用途が決まれば保存/入出力を再点検 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/292/files)（7件）。関連Conversation記録 [6328252362](https://github.com/1kz-ma1/HINANEX/pull/292#issuecomment-6328252362)、[6331561244](https://github.com/1kz-ma1/HINANEX/pull/292#issuecomment-6331561244)、[6331816965](https://github.com/1kz-ma1/HINANEX/pull/292#issuecomment-6331816965)

<details>
<summary>パス・変更行数</summary>

- `frontend/README.md`（modified、+32/−0）
- `frontend/docs/TEAM_REVIEW_ACCEPTANCE_20261022.md`（added、+37/−0）
- `frontend/index.html`（modified、+1/−0）
- `frontend/mock/team-review-example.json`（added、+82/−0）
- `frontend/scripts/build-check.js`（modified、+11/−0）
- `frontend/team-review.html`（added、+424/−0）
- `frontend/tests/team-review.test.js`（added、+268/−0）

</details>

## PR 289

**[#289](https://github.com/1kz-ma1/HINANEX/pull/289) ci(shared): one-click opt-in Nagoya 50-site ABR real-data pilot**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | Shared・名古屋CI。ABR 50件手動CI |
| base | `main` @ `308da83f3e7a1731837d9a437d8446e8429b09a1` |
| HEAD | `feature/nagoya-abr-manual-runner-20261021` @ `fd06cf01816d968c99b3418d977f03c0fedc71c4` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...fd06cf01816d968c99b3418d977f03c0fedc71c4) ahead 1 / behind 183 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39537338027/job/119016916718) |
| 前提・契約 | 実行前提#283。#286 |
| Owner・独立QA | CIの構文/検査記録。新規実行なし |
| 安全・非公開・公開条件 | 実データ・候補点・Artifact制限 |
| 未検証・次の最小作業 | 再開時に手動実行主体、範囲、出力制限を承認 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/289/files)（1件）。関連Conversation記録 [6307115575](https://github.com/1kz-ma1/HINANEX/pull/289#issuecomment-6307115575)

<details>
<summary>パス・変更行数</summary>

- `.github/workflows/nagoya-abr-50-pilot.yml`（added、+154/−0）

</details>

## PR 283

**[#283](https://github.com/1kz-ma1/HINANEX/pull/283) feat(d): opt-in 50-site Nagoya address geocoding pilot with ABR provenance**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・名古屋。ABR最大50施設の明示検証 |
| base | `main` @ `56a2bc1f50d83e4e784d07101d435e069b0204ca` |
| HEAD | `feature/d-nagoya-geocoding-pilot-20261021` @ `14e11116265208e3cd27afe72f02b7248c65ca9b` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...14e11116265208e3cd27afe72f02b7248c65ca9b) ahead 73 / behind 186 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39624889137/job/119307487374) |
| 前提・契約 | コード前提なし。#286 |
| Owner・独立QA | #323等のレビューとは別。旧端末実行報告 |
| 安全・非公開・公開条件 | 位置候補のまま隔離。本番・自動取得なし |
| 未検証・次の最小作業 | 代表原本と人間位置受入の範囲を確定 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/283/files)（25件）。関連Conversation記録 [6306536105](https://github.com/1kz-ma1/HINANEX/pull/283#issuecomment-6306536105)、[6306963441](https://github.com/1kz-ma1/HINANEX/pull/283#issuecomment-6306963441)、[6307242308](https://github.com/1kz-ma1/HINANEX/pull/283#issuecomment-6307242308)

<details>
<summary>パス・変更行数</summary>

- `pipeline/.gitignore`（modified、+3/−0）
- `pipeline/compare_nagoya_gsi_offline.py`（added、+333/−0）
- `pipeline/create_nagoya_independent_review_queue.py`（added、+316/−0）
- `pipeline/diagnose_nagoya_address_mismatch.py`（added、+265/−0）
- `pipeline/diagnose_nagoya_chome_stage4_reference_screen.py`（added、+264/−0）
- `pipeline/diagnose_nagoya_kanji_chome_stage3.py`（added、+272/−0）
- `pipeline/diagnose_nagoya_text_difference_stage2.py`（added、+226/−0）
- `pipeline/docs/HANDOFF_E.md`（modified、+1/−0）
- `pipeline/docs/NAGOYA_ADDRESS_GEOCODING_PILOT_20261021.md`（added、+441/−0）
- `pipeline/geocode_nagoya_pilot.py`（added、+309/−0）
- `pipeline/refine_nagoya_gsi_stage7.py`（added、+301/−0）
- `pipeline/report_nagoya_geocoding_pilot.py`（added、+201/−0）
- `pipeline/tests/test_nagoya_address_mismatch_diagnostic.py`（added、+255/−0）
- `pipeline/tests/test_nagoya_chome_stage4_reference_screen.py`（added、+150/−0）
- `pipeline/tests/test_nagoya_geocoding_pilot.py`（added、+211/−0）
- `pipeline/tests/test_nagoya_geocoding_report.py`（added、+105/−0）
- `pipeline/tests/test_nagoya_gsi_offline.py`（added、+142/−0）
- `pipeline/tests/test_nagoya_gsi_stage6.py`（added、+149/−0）
- `pipeline/tests/test_nagoya_gsi_stage7.py`（added、+134/−0）
- `pipeline/tests/test_nagoya_independent_review_queue.py`（added、+132/−0）
- `pipeline/tests/test_nagoya_kanji_chome_stage3.py`（added、+147/−0）
- `pipeline/tests/test_nagoya_stage7_private_viewer.py`（added、+161/−0）
- `pipeline/tests/test_nagoya_text_difference_stage2.py`（added、+152/−0）
- `pipeline/triage_nagoya_gsi_stage6.py`（added、+247/−0）
- `pipeline/view_nagoya_stage7_private.py`（added、+226/−0）

</details>

## PR 282

**[#282](https://github.com/1kz-ma1/HINANEX/pull/282) docs(shared): adopt feature-first execution without fixed A-E ownership**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | Shared・運用。feature-firstとA–E責務の旧規範変更案 |
| base | `main` @ `56a2bc1f50d83e4e784d07101d435e069b0204ca` |
| HEAD | `docs/feature-first-workflow-20261021` @ `b32f7f188ed7b80873df865871a0d9c1a5f38505` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...b32f7f188ed7b80873df865871a0d9c1a5f38505) ahead 3 / behind 187 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39526786215/job/118983206718) |
| 前提・契約 | #361/#344/WP-001と運用が重複 |
| Owner・独立QA | 現行root AGENTSの改訂として未採用 |
| 安全・非公開・公開条件 | 保護やA–E Scope Guard変更は今回外 |
| 未検証・次の最小作業 | 採用する考え方のみ運用文書へ参照し規範変更は別判断 |
| 暫定分類・MVP | CLOSE候補 / 履歴。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/282/files)（3件）。

<details>
<summary>パス・変更行数</summary>

- `AGENTS.md`（modified、+25/−39）
- `CONTRIBUTING.md`（modified、+11/−34）
- `docs/strategy/HINANEX_THREE_AXIS_ROADMAP_2027-02-09.md`（modified、+8/−1）

</details>

## PR 272

**[#272](https://github.com/1kz-ma1/HINANEX/pull/272) feat(D): offline three-region RegionExport replay delta comparison**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | D・3地域。スナップショット差分比較 |
| base | `main` @ `8615c0060a02f9c824ebc846dcf930b042a29a6f` |
| HEAD | `feature/d-replay-delta-review-20261019` @ `5d536dba975796f3537ba12661d6450342669a65` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...5d536dba975796f3537ba12661d6450342669a65) ahead 6 / behind 195 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39199705711/job/117889940159) |
| 前提・契約 | #264/#265/#266/#268、#270/#271 |
| Owner・独立QA | オフライン技術証跡。実再生成/人間採用は保留 |
| 安全・非公開・公開条件 | UNKNOWN維持。原本更新・公開を行わない |
| 未検証・次の最小作業 | A/C採用版固定後、必要な差分機能を再試験 |
| 暫定分類・MVP | DEFER候補 / 拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/272/files)（3件）。関連Conversation記録 [6259561034](https://github.com/1kz-ma1/HINANEX/pull/272#issuecomment-6259561034)、[6259695667](https://github.com/1kz-ma1/HINANEX/pull/272#issuecomment-6259695667)

<details>
<summary>パス・変更行数</summary>

- `pipeline/compare_three_region_replays.py`（added、+237/−0）
- `pipeline/docs/FINAL_THREE_REGION_REPLAY_COMPARE_20261019.md`（added、+47/−0）
- `pipeline/tests/test_compare_three_region_replays.py`（added、+295/−0）

</details>

## PR 271

**[#271](https://github.com/1kz-ma1/HINANEX/pull/271) docs(A): Edogawa seven-source original provenance and human approval ledger**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | A・江戸川。7原本の版・来歴・人間承認台帳 |
| base | `main` @ `5058fe7247a7e9fde0ea81868c059b9c589b63a5` |
| HEAD | `feature/a-edogawa-source-provenance-20261019` @ `48d65621e100d2069ee09b42564c3d595cf345c6` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...48d65621e100d2069ee09b42564c3d595cf345c6) ahead 3 / behind 189 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/39376844767/job/118476787913) |
| 前提・契約 | #264/#265、#268。#272に関連 |
| Owner・独立QA | 旧Captainの文書限定判断と実行阻止を別記 |
| 安全・非公開・公開条件 | 原本・意味解釈・権利の承認待ち |
| 未検証・次の最小作業 | 個別出典署名と最新mainの資料比較で採否判断 |
| 暫定分類・MVP | HOLD / 実データ拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/271/files)（2件）。関連Conversation記録 [6258854269](https://github.com/1kz-ma1/HINANEX/pull/271#issuecomment-6258854269)、[6284362569](https://github.com/1kz-ma1/HINANEX/pull/271#issuecomment-6284362569)、[6284381938](https://github.com/1kz-ma1/HINANEX/pull/271#issuecomment-6284381938)

<details>
<summary>パス・変更行数</summary>

- `data-research/scenarios/2026-10-19-edogawa-seven-source-ai-prereview.md`（added、+49/−0）
- `data-research/scenarios/2026-10-19-edogawa-seven-source-provenance-handoff.md`（added、+49/−0）

</details>

## PR 136

**[#136](https://github.com/1kz-ma1/HINANEX/pull/136) test(c): time-aware Edogawa identity evidence, URL collision guard and official source archive**

| 項目 | 調査結果 |
| --- | --- |
| 領域・実装 | C・江戸川。施設同一性とURL衝突の旧横断検証 |
| base | `main` @ `520ff4176b9eb35522b04210ce54454c848728df` |
| HEAD | `feature/c-edogawa-water-ledger-review-20261010` @ `3e8cb82f51ddea4bf88dd12eb6221af0c06232a6` |
| 状態 | Draft。 [main比較](https://github.com/1kz-ma1/HINANEX/compare/62557a665f59254755a696e2e89292035ea4f6c2...3e8cb82f51ddea4bf88dd12eb6221af0c06232a6) ahead 92 / behind 380 |
| exact-HEAD required CI | [test SUCCESS](https://github.com/1kz-ma1/HINANEX/actions/runs/38343713895/job/115120210216) |
| 前提・契約 | #133/#134/#137/#141。#221で分割方針 |
| Owner・独立QA | 独立C技術証跡あり。人間署名未了、mainに分割成果 |
| 安全・非公開・公開条件 | UNKNOWN・URL共通による施設同一化を禁止 |
| 未検証・次の最小作業 | 分割済み差分と未取り込みの回帰だけを対照して処分判断 |
| 暫定分類・MVP | CLOSE候補 / 実データ拡張。根拠は上記の鮮度・前提・証拠・スコープ。 |

[変更ファイル](https://github.com/1kz-ma1/HINANEX/pull/136/files)（42件）。関連Conversation記録 [6135761960](https://github.com/1kz-ma1/HINANEX/pull/136#issuecomment-6135761960)、[6136190749](https://github.com/1kz-ma1/HINANEX/pull/136#issuecomment-6136190749)、[6284205855](https://github.com/1kz-ma1/HINANEX/pull/136#issuecomment-6284205855)

<details>
<summary>パス・変更行数</summary>

- `validation/README.md`（modified、+159/−1）
- `validation/reviews/2026-10-10-edogawa-water-join-snapshot-audit.md`（added、+175/−0）
- `validation/reviews/2026-10-13-2026-external-internal-flood-site-edition-audit.md`（added、+39/−0）
- `validation/reviews/2026-10-13-edogawa-campus-era-original-audit.md`（added、+33/−0）
- `validation/reviews/2026-10-13-edogawa-site-identity-and-flood-semantics-gates.md`（added、+59/−0）
- `validation/reviews/2026-10-13-edogawa-three-source-reconciliation-priority.md`（added、+55/−0）
- `validation/reviews/2026-10-13-gsi-original-to-current-d-evidence-audit.md`（added、+40/−0）
- `validation/reviews/2026-10-13-old-shimokamata-demolition-contract-status-gates.md`（added、+61/−0）
- `validation/reviews/2026-10-13-old-shimokamata-inquiry-packet.json`（added、+52/−0）
- `validation/reviews/2026-10-13-shimokamata-official-inquiry-protocol.md`（added、+28/−0）
- `validation/reviews/2026-10-13-shimokamata-three-state-evidence-demo-contract.md`（added、+56/−0）
- `validation/validation/archive_edogawa_guidance.py`（added、+208/−0）
- `validation/validation/archive_edogawa_official_sources.py`（added、+273/−0）
- `validation/validation/audit_gsi_edogawa_original.py`（added、+269/−0）
- `validation/validation/build_edogawa_identity_review_packet.py`（added、+367/−0）
- `validation/validation/build_shimokamata_evidence_demo.py`（added、+231/−0）
- `validation/validation/build_shimokamata_review_readiness.py`（added、+145/−0）
- `validation/validation/compare_edogawa_official_revisions.py`（added、+217/−0）
- `validation/validation/test_edogawa_2026_water_site_revisions.py`（added、+110/−0）
- `validation/validation/test_edogawa_campus_history.py`（added、+158/−0）
- `validation/validation/test_edogawa_council_vote.py`（added、+111/−0）
- `validation/validation/test_edogawa_demolition_contract.py`（added、+102/−0）
- `validation/validation/test_edogawa_guidance_archive.py`（added、+113/−0）
- `validation/validation/test_edogawa_identity_review_packet.py`（added、+277/−0）
- `validation/validation/test_edogawa_official_archive_content.py`（added、+155/−0）
- `validation/validation/test_edogawa_official_reply_intake.py`（added、+197/−0）
- `validation/validation/test_edogawa_official_revisions.py`（added、+149/−0）
- `validation/validation/test_edogawa_official_snapshot_archive.py`（added、+207/−0）
- `validation/validation/test_edogawa_priority_identity.py`（added、+186/−0）
- `validation/validation/test_edogawa_three_source_review.py`（added、+155/−0）
- `validation/validation/test_edogawa_water_join.py`（added、+187/−0）
- `validation/validation/test_gsi_edogawa_original.py`（added、+155/−0）
- `validation/validation/test_shimokamata_evidence_demo.py`（added、+152/−0）
- `validation/validation/test_shimokamata_review_readiness.py`（added、+130/−0）
- `validation/validation/validate_edogawa_official_archive.py`（added、+220/−0）
- `validation/validation/verify_edogawa_2026_water_site_revisions.py`（added、+201/−0）
- `validation/validation/verify_edogawa_campus_history.py`（added、+271/−0）
- `validation/validation/verify_edogawa_council_vote.py`（added、+167/−0）
- `validation/validation/verify_edogawa_demolition_contract.py`（added、+151/−0）
- `validation/validation/verify_edogawa_official_reply_intake.py`（added、+211/−0）
- `validation/validation/verify_edogawa_three_source_review.py`（added、+248/−0）
- `validation/validation/verify_edogawa_water_join.py`（added、+505/−0）

</details>
