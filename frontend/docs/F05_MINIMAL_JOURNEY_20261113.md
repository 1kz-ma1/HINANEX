# F05/P0 B最小導線：受入メモ（Issue #362）

## ユーザー操作

1. F01 GISは常に独立入口。GIS側のデータ/洪水ラスタ/出典/取得エラーを維持。
2. F05ローカル試作で江戸川区13123を本人が明示選択。位置/GPS/地図のviewport/ハザード/施設IDは渡さない。
3. HTTP loopbackでのみF02非公開read-only画面への明示リンク。一般公開originではF02へリンクしない。JSONエラーはF02自身に任せる。
4. F05側には施設比較・安全認定・開設中表示・経路・外部API・F03保存はない。参考経路は未提供と明示。

## 主な実装と受入条件

- frontend/src/f05-journey-model.js : 明示地域コードとloopback originだけの純粋判定
- frontend/prototypes/f05-flood-journey/index.html : local-only UI。本人操作がないとF02へのhrefなし。公式情報はユーザークリックのみに限定
- frontend/tests/f05-journey.test.js : 非ローカルorigin、偽origin、未選択/地域不一致、旧選択破棄、施設ID未連携、誤認防止のテスト
- Schema/D Contract/E GIS/A/C/実データに変更なし
- F01、F02は別画面のまま動作。表示誤解の確認はChrome/Safari/Android実機の独立受入とする

## 確認の区分

- Implementation: Draft試作、main未統合
- Test Passed: main追従HEAD `731bf9e4e9df65383575d2ac3d2587a756bec30c` の [required test #43791774940](https://github.com/1kz-ma1/HINANEX/actions/runs/43791774940) SUCCESS。本文更新後の最新HEADは別途再テストする
- Independent Data Review: C全行照合は別（元CSV再配信や施設安全の証明ではない）
- Published: **NO**。独立Deployガード [PR #377](https://github.com/1kz-ma1/HINANEX/pull/377) は2026-11-16にmain統合済み。実RenderデプロイSHA `d461f5912216b54d3f30a2833eb12c08860b4e74` をログで確認済み。デプロイ後のF05 HTMLとF02 HTMLの404確認は [Issue #373](https://github.com/1kz-ma1/HINANEX/issues/373#issuecomment-6905481203)。**ただしこのF05ソースはmain未統合のため、実ソース込みの最終非配信受入は未実施**
- Owner approval: WIP順序/実装採用/公開範囲は未決定。#360の現行規則を維持

## 次に必要なゲート

- [ ] オーナー：#362 Bの初期スライスとして採用する判断
- [ ] exact HEAD required test SUCCESS
- [x] F05独立試作に対するDeploy除外ガードがmain先行統合（PR #377）
- [ ] Renderの実配信コミット照合とF05試作・モデルJSの直接GETが404/非配信であることを記録（Issue #373）
- [x] ローカルChrome 320/390/1440幅・キーボード・外部自動通信ゼロ等の基本14項目（**ユーザー申告PASS**、[Issue #372](https://github.com/1kz-ma1/HINANEX/issues/372#issuecomment-6906107953)）。独立HAR・物理端末・最新ローカルcheckout SHAの照合は未実施
- [ ] 必要ならE側F01入口変更を別Issue/PRで採用
- [ ] #366原CSV再配信/第三者権利など、公開ゲートを別承認

**この文書・PRは公式の避難先を認定せず、一般公開の同意でもない。**

## 2026-11-16 main追従・レビュー追補

- B Draft PR #371はmain `c65fe1d4f19db2ddd907df8d8556bdedcd2a40d7` （Deploy #377まで含む）をブランチへ取り込み、F05の実装差分は引き続きB `frontend/**` 内の5ファイルのみ。
- 実装の静的検査：本人選択した江戸川区13123 + HTTP loopback以外ではF02 hrefが生成されず、公式洪水データ・施設ID・位置・安全・開設・経路を推測しない。
- **追加受入が必要：** F05試作そのものの実HTTP Chrome（320/390/1440px）/キーボード操作/遷移/外部通信のテスト。既存F02/F03 Chrome成功は代替にならない。F05テストはNodeモデル・HTML静的検証のみ。
- 最新mainでの必須CIの実行結果は、この追補とは独立にPR #371の本文へ記録。Render本番相当HTTPは依然NOT_VERIFIED。

## 2026-11-16 F05最終コードレビューに向けた受入境界

- **実装/安全範囲:** ローカルHTTPでのみ本人選択の江戸川区13123からF02への手動導線を表示する。F01は別入口のまま。施設安全・開設・災害適合・経路推測・F03保存・自動外部APIは実装しない。
- **人間操作:** F05-01〜14はユーザーによるChrome手動テストのPASS報告。F02のJSON 404は当初観測されたが、後日のF05-14再テストPASS申告に加え、ユーザーが提示したChrome Network画面で `edogawa.json` の **HTTP 200（fetch、236 kB）を目視確認**した（[Issue #372追補](https://github.com/1kz-ma1/HINANEX/issues/372#issuecomment-6906212613)）。ただし原JSONの内容・Schema互換・Cによる原本/施設行の独立承認は、このNetwork画面のみでは証明されない。
- **Render:** #377の静的非公開ガードはmain統合済みで、デプロイ後のF05 HTMLとF02 HTMLが404。しかし#371をmainに取り込んだ後に実F05資材が配信されないことは未確認であり、公開安全上は別途確認する。
- **正式承認:** Issue #362でOwnerの初期Bスライス採用・WIP判断が明示されていない。共同Merge Captainの通常PR統合判断権限と、特定スライスの採用判断は区別する。**Draft/merge blocked、公式CSV権利・施設安全・一般公開NO-GO**を維持する。

## 2026-11-17 受入履歴と統合範囲の整理（最新CIはPR本文で管理）

- **B1の状態:** F05/B1 [PR #371](https://github.com/1kz-ma1/HINANEX/pull/371) は **Draft / merge: blocked / source NOT MERGED**。B担当から採用希望を表明済みだが、[Issue #362](https://github.com/1kz-ma1/HINANEX/issues/362#issuecomment-6933939711)のOwner本人による初期WIP・採用スライスの明示回答は未確認。共同Merge Captainの通常のPR統合権限は、この個別仕様承認を代行しない。
- **関連B2:** 施設の合成2件比較・本人の一時選択 [PR #399](https://github.com/1kz-ma1/HINANEX/pull/399) は **mainにソースだけ統合済み**（commit `b7b7070e787d42c2e2eb4835d898a4ad71da31a7`）。このB2はF05/B1で実データと自動接続されず、F05/B1の導線にも組み込まれない。B2のChrome 22/22 PASSは別のユーザー報告であり、B1の14/14 PASSと混同しない。
- **テスト履歴:** 旧HEAD `ab6c60b56ce689184442c2156320332f2627287f` では[required test #43812754659](https://github.com/1kz-ma1/HINANEX/actions/runs/43812754659) SUCCESS、Frontend 118/118、GIS 24/24、Scope Guard PASS。**本書類を更新した新HEADのrequired testは再実行して記録する**。以前の「追加受入が必要」という節は更新前の履歴であり、F05-01〜14のユーザー報告は[#372](https://github.com/1kz-ma1/HINANEX/issues/372#issuecomment-6906107953)に記録済み（独立HAR、最新checkout SHA照合、物理端末はNOT_RUN）。
- **非公開:** [Deploy #377](https://github.com/1kz-ma1/HINANEX/pull/377)は `prototypes/f05-flood-journey/**` とB1モデル・テスト・本書類を公開バンドルから除外。実B1ソースのmain統合後Render HTTP 404は **NOT_VERIFIED**。B2ソース統合後のRender LIVE SHA＋対象5ファイルの404も[Issue #373](https://github.com/1kz-ma1/HINANEX/issues/373#issuecomment-6933981069)で未確認。
- **最終判断:** 本文中の過去main・HEAD・検証予定は当時の履歴。最新の`main`追従・CI・GitHubレビューはPR #371の末尾とCI runに記録する。コードmain統合と実施設の公式安全認定・CSV利用許諾・一般公開を区別する。

## 2026-11-20 Owner採用・統合前残余QAの追補（現行判断）

> 本節は2026-11-20時点の**最新判断**です。上記の「Owner採用未決定」「追加受入が必要」等は当時の監査履歴として残しており、現在の承認状態を表しません。

- **Owner仕様採用：ADOPTED_FOR_B1_SCOPE。** [Issue #362の2026-11-20採用記録（@1kz-ma1）](https://github.com/1kz-ma1/HINANEX/issues/362#issuecomment-7030901882)。B担当の江戸川区 `13123` 本人選択＋HTTP loopback時のみF02 read-onlyへの手動リンク、F01独立入口、F07「参考経路は未提供」を承認。これは**PR #371のmainマージ・Render公開・実データ安全承認ではない**。
- **スライス間境界：** B2の合成Fixture比較・本人一時選択は別スライス。B1→B2の新規導線、F02 RegionExport実データのB2連携、F01ハザード/施設ID自動join、GIS側入口変更、GPS・保存・外部API・開設/安全/災害適合推定・実経路は引き続き対象外。今回のB1ローカル仕様を**2027-02-09学内MVP全体の最終公開方式**に一般化しない。
- **固定ソース受入基点：** PR #371 HEAD `da5f0b4f4a2bf294462efbe6fc4d34bfd173dfaf`。実ページ `index.html` Git blob `fb32b71d5ce457ccbdb34d8281c2babdbcab677d`、モデル `4673c0491b580a71a43cbebc13b5b146fd702256`、Nodeテスト `b4cd8095804c4d2338cd63e7d0ac4cdaf19fbfa6` を隔離取得し、それぞれのGit blob再計算で一致。
- **この固定ソースの独立実行：** `node --test frontend/tests/f05-journey.test.js` **5/5 PASS**。隔離Python HTTPサーバーで実HTMLとモデルJSのHTTP 200・応答バイトの原本一致を確認（2件PASS）。
- **独立実HTTP Chrome B1 E2E：NOT_RUN（環境制約）。** Chromium 144を起動したが、管理ポリシー `URLBlocklist=["*"]` により最初の `http://127.0.0.1:<port>/frontend/prototypes/f05-flood-journey/index.html` への移動が `net::ERR_BLOCKED_BY_ADMINISTRATOR` で失敗。試験のために管理ポリシーを解除・回避せず停止。地域変更/解除、Tab/Enter、320/390/1440pxのChrome実画面、F01/F02クリック遷移、非loopbackのChrome実挙動、ブラウザNetwork/Storage/HAR/スクリーンショットは**今回の独立ChromeでPASS未取得**。既存の[#372 DQA-004 14/14人間申告PASS](https://github.com/1kz-ma1/HINANEX/issues/372#issuecomment-6906107953)・F02/B2の別HTTP Chrome CI PASS・B1 Node PASSを代替証拠と偽らない。
- **前回HEADのCI（履歴）：** [`da5f0b4...` required test SUCCESS #44678596404](https://github.com/1kz-ma1/HINANEX/actions/runs/44678596404)：Frontend 133/133、GIS Node 39/39、Deploy 21/21、F02/B2 Chrome CI・Scope Guard等PASS。**本追補コミットの最終HEADでrequired testを改めて照合**すること。
- **非公開：** `deploy/build_staging.py` のF05/B1モデル・ページ・テスト・文書、および `prototypes/f05-flood-journey/**`（B2含む）の除外は維持。コード統合後の実Render LIVE非配信（Issue #373）、iOS/Android/Safari・読上げ（Issue #372）、CSV権利/実施設承認（Issue #366）は別ゲート、**NOT_VERIFIED / NO-GO**。
- **現在の統合準備判定：** `CAPTAIN_REVIEW_CANDIDATE_WITH_OPEN_EVIDENCE / MERGE_HOLD`。人間Merge Captain本人が、独立B1 Chrome未実施の残余リスクをHOLD/DEFERRED/必要追加証拠として明示決定するまで`MERGE`の代理承認はしない。PRはDraft・`merge: blocked`を維持。
