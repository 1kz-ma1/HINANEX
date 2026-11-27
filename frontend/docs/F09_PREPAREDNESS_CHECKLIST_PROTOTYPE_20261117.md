# F09 平時の備えチェックリスト — 独立非公開Frontend Prototype

- 記録: 2026-11-17
- Status: **IMPLEMENTED ON FEATURE BRANCH / PROTOTYPE ONLY / NOT PUBLIC / NOT APPROVED**
- Issue: [#423](https://github.com/1kz-ma1/HINANEX/issues/423)
- Reference: Draft PR [#346](https://github.com/1kz-ma1/HINANEX/pull/346) の `docs/strategy/features/09_PREPAREDNESS_CHECKLIST.md` は **FUTURE DESIGN / PROPOSED**。main正式仕様ではない。今回の最小スライスはオーナー依頼で独立着手したもので、**F09の優先度P2を変更しない**。
- Precondition: [shared guard PR #428](https://github.com/1kz-ma1/HINANEX/pull/428) が配布非公開を担保するまで、feature branchからmainへの単独統合禁止。

## 利用者ができること（今回実装）

1. `frontend/prototypes/f09-preparedness/index.html` で一般家庭の準備項目10個を3分類で閲覧。
2. 各項目のチェックと解除、`準備済み/未準備`表示を切り替え。
3. `チェックした件数/全数`、進捗率（四捨五入した操作項目割合）を確認。
4. `未準備だけ表示`で残項目に絞り込み、`すべて表示`へ戻る。
5. `すべて解除`でチェックを0へ戻す。チェック0の状態ではボタンを無効化。
6. Tabによるフォーカス移動、Spaceでチェック、Enterで解除ボタン。画面幅320/390/1440pxを対象にスクロール可能なレスポンシブUI。

**非目標:** 現在地、実災害、避難先・経路の安全判定、自治体ごとの必須要請、医薬品・健康・家族情報、認証、通信、自動または手動保存、F03 Contractの採用、F05ナビ統合。

## State contract / error and UX behavior

- `model.js`の`createChecklist()`が各画面インスタンス専用`Set<string>`を所有。固定IDを受ける`setChecked(id, boolean)`は不明なID、不正な型を拒否（false）し、既存状態を保持。重複操作は冪等。
- `snapshot()`はチェック件数、全10、未チェック件数、割合、チェック済みIDのコピーを返す。
- ページの再読み込みや閉鎖で初期化。状態はCookie、localStorage、sessionStorage、IndexedDB、URL、サーバー、ログ、ネットワークに書き込まない。外部リンクは利用者が明示選択したときのみ遷移。
- DOMの全描画更新はしない。既存チェックボックスの`checked`と表示を更新。未準備フィルタで操作対象が非表示になった場合は別の未準備項目、なければフィルタボタンへフォーカス移動。
- `%=`はチェック項目数÷全項目数×100。**安全度、達成保証、災害準備十分性の指標ではない。** 項目のチェックは自己申告で検証しない。
- 初期値: 0/10 (0%)。リセット: 0/10 (0%)。すべてチェック: 10/10 (100%) でも十分性を保証しない。

## 出典・内容範囲（2026-11-17に参照）

- 発行元：**内閣官房／首相官邸**。
- 対象：一般家庭の平時の備え（家具転倒防止、食料・飲料、携帯トイレ、非常持出袋、ライト、情報手段、連絡方法、地域の避難先・経路確認など）。
- 出典：首相官邸「災害への備え 事前にできること」 https://www.kantei.go.jp/jp/headline/bousai/sonae.html
- 親ページ：首相官邸「防災の手引き」 https://www.kantei.go.jp/jp/headline/bousai/index.html — **最終更新日: 令和8年10月（2026年10月）**。参照した子ページ独自の更新日・公開日は記載を確認できず **UNKNOWN**。親の更新日を子ページの日付として扱わない。
- 利用条件：首相官邸「コピーライトポリシー」 https://www.kantei.go.jp/jp/terms.html — **最終更新日 2025年3月31日**。特記がない内閣官房コンテンツはPDL1.0。出典、再編集した旨・主体（HINANEX）を明示。第三者権利・例外別条件は別途確認が必要。国の作成した未加工原本だと偽らない。官邸写真・ロゴ・原文全文を取り込まず、事実に沿った短い項目へ再編集したもの。
- 適用範囲：上記一般向け参考情報の**一部の独立例示**。公式の網羅的なチェック表、自治体の義務、個別事情への十分な備えを示さない。出典と利用条件の一次C独立レビュー・公開受入は未実施。**本機能の一般配信は許可されていない**。

## 配信・責務境界

- 変更は **frontend/** のみ。`frontend/prototypes/f09-preparedness/**`は既存BのindexやF05画面からリンクされず、ローカルでのみアクセスする。
- Render staging builderは `frontend/**` を通常配信するため、ガードPR #428でF09のディレクトリ全部、`frontend/tests/f09-preparedness.*`、本ドキュメントを**明示除外**する。mainへの統合順序: shared #428 → main確認 → B Featureを最新mainへリベース/追従 → テスト → 人間Merge Captain判断。
- F03保存Contract、D RegionExport/Schema、F05、E GIS、C Validationを一切変更しない。
- 一般公開は別のオーナー許可/出典再審査/公開PRを要する。main統合とRender一般公開は別。

## 試験手順・判定記録

```sh
cd frontend
node --test tests/f09-preparedness.test.js
node tests/f09-preparedness-browser.cjs
# GitHub Actions CIでは真のHTTP読み込みを要求し、代替DOM注入で成功扱いしない。
npm test
npm run lint
npm run build
```

| Case | 初期観測（2026-11-17） | 留保 |
| --- | --- | --- |
| 初期0 / 10、チェック・解除、全解除、100%、不正ID | PASS: Node 22、unit 6/6 | GitHub CI最新HEADは別途確認 |
| Chromium DOMとTab/Space/Enter、絞り込み、フォーカス | PASS: Linux Chromium（合成DOM注入） | 管理環境のローカルHTTPナビゲーションは **BLOCKED** |
| 320px / 390px / 1440px、横はみ出しなし | PASS: Chromium CDP実計測 | 物理端末はNOT_RUN |
| HTTP再読込後0件、HTTPで無保存 | **BLOCKED**: `ERR_BLOCKED_BY_ADMINISTRATOR` | CIで真のHTTP受入が必要。新DOMセッションで0件はPASS |
| HTML/CSS/JSの外部配信阻止 | **NOT_RUN**: CI shared #428が必要 | 担当外 `deploy/**` を本PRで変更しない |
| iPhone Safari / Android端末 / 支援技術 | **NOT_RUN** | QA #372で要調整 |

**QA:** 実機検証は #372 の定期QA運用で `DEFERRED`として管理。端末/OS/ブラウザ、人間担当、対象HEAD、実施日を決めるまではPASSにしない。

## 将来拡張（今回の実装外）

- 自己選択項目や任意カテゴリー、人数に応じたカスタマイズ（個人情報取得と安全指標化を避ける設計審査が先）
- 手動保存・明示復元・削除（F03のキーやSchemaを流用せず、独立の同意/保存設計）
- 公的一次資料の版固定とC独立原本受入後の出典表示強化
- 多言語・読み上げ/支援技術による実機受入

## 2026-11-27 レビュー指摘への是正（#429）

- #428はmainへ統合済み。今回最新mainを取り込んでbaseをmainへ変更。F09の8 frontendパスだけを維持し、deploy/契約・F05には変更なし。
- フィルタ名「未準備だけ表示」は固定、aria-pressedと「表示：…」で状態を表示。解除でボタンが無効になる場合はフィルタへフォーカスを移す。全件チェック時の未準備フィルタ空表示、解除後の復帰を実HTTPテストに追加。
- メモリのみの契約：新document/再読込で0件。BFCacheのpersisted pageshowでもチェックとフィルタを初期化し、通常pageshowではブラウザフォーム復元をモデル状態に再同期する。チェックボックスのautocompleteはoff。実BFCache成立時のみPASSとし、新documentになった履歴移動は別のPASS、BFCache自体はNOT_RUN。
- ブラウザQAはHTTPのみ（DOM注入fallbackを撤去）。listen・起動・CDP HTTP/open/send/closeの有限期限、pending拒否、全資源のfinally、cleanup失敗を非0終了にする。共有http-chromeの停止/プロファイル削除を再利用。欠落binary・spawn error・早期起動終了・cleanupエラーの負例を追加。
- 再読込は実URL、readyState、pageshow、旧document sentinel消滅、loaderId変更と0件/無保存を確認。実履歴復帰とBFCacheを区別する。
- 実候補checkoutのfrontendコピーを既存Deploy builderで検査するテストを追加。7個の非公開実ファイルが存在すること、コピー先で全件不在、既存除外維持、公開対照5個のSHA-256一致を確認する。package.jsonは現行配布方針でコピーされ、F09 test/lintの文字列参照が残る（製品/QA/仕様本体ではない）。厳密な参照ゼロは未承認、Shared/Owner判断を要する。全体Render LIVE・公式データ生成とは別試験。
- DQA-009は#372に繰越。出典C独立受入、一般公開許可、Render LIVEは未確認。新HEADのCI/実HTTP結果はPRに追記し、旧CIを流用しない。P2維持、Draft/HOLD。
