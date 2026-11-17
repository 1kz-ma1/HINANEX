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
