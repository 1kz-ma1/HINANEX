# F02 / Issue #348 テスト報告 — 2026-11-04

## 検証した対象

- 独立フォルダ: `frontend/prototypes/f02-shelter-explore/`
- GitHub: `1kz-ma1/HINANEX` のmain・既存GISへの変更なし
- データ: すべて合成fixture。実在施設・公式出典は**不使用**
- ブラウザ: ヘッドレスChromium、Desktop 1440×1000 / Mobile相当 390×844（Playwrightのビューポートエミュレーション）。

## Passed（自動）

Node.js 22.16.0: `node --test tests/*.test.cjs` -> **10 / 10 PASS**

| ID | テスト | 結果 |
|---|---|---|
| T01 | 地域別の施設件数（別地域を自動名寄せしない） | PASS |
| T02 | 施設名検索と文字種正規化 | PASS |
| T03 | 全レコードが架空、URLが無効 | PASS |
| T04 | UNKNOWNと座標欠損を補完しない | PASS |
| T05 | 元資料未取得と座標欠損の区別 | PASS |
| T06 | 地域0件、検索0件、読込エラーの区別 | PASS |
| T07 | エラー状態を0件より優先 | PASS |
| T08 | 公開日不明を最新と言わない | PASS |
| T09 | 有効な実座標を使わない（ダミーは0,0） | PASS |
| T10 | 5種類の属性別確認理由が存在 | PASS |

`node --check app.js model.js fixtures.js`（個別実行） -> **PASS**

## Passed（ブラウザ表示・操作）

| ID | ブラウザ検証 | 結果 |
|---|---|---|
| B01 | 初期の4件表示 | PASS |
| B02 | 合成データと安全非保証の固定警告 | PASS |
| B03 | 詳細、出典、版の表示 | PASS |
| B04 | 検索で座標なしの施設が表示される | PASS |
| B05 | 検索結果0件の表示 | PASS |
| B06 | 地域内の合成記録0件の表示 | PASS |
| B07 | 模擬データ読込エラーの別表示 | PASS |
| B08 | 元資料未取得の表示 | PASS |
| B09 | キーボードEnter、詳細見出しへのフォーカス移動 | PASS |
| B10 | JavaScript実行時例外なし | PASS |
| B11 | 390pxで横スクロールなし | PASS |
| B12 | モバイル幅で詳細表示 | PASS |

**実行制約:** この環境ではChromiumが`file://`およびlocalhostへのページ遷移を管理者設定で拒否したため、ブラウザテストでは同一のHTML/CSS/JSをin-memoryで`page.set_content`して検証しました。実際のURL遷移・個別CSS/JSファイルの読込を通したE2Eテストの成功を主張するものではありません。コード構文と表示・操作は確認済みです。

## スクリーンショット

- `screenshots/desktop-list.png` — PC 一覧
- `screenshots/desktop-detail.png` — PC 詳細
- `screenshots/mobile-list.png` — モバイル幅 一覧
- `screenshots/mobile-detail.png` — モバイル幅 詳細

## Failed

- 自動テストでの最終残存エラー: **0件**。
- 開発中に検索文字種のテストが1件失敗したため、NFKC + カタカナ→ひらがな正規化を追加して再実行。最終10/10 PASS。

## Not run / 追加確認が必要

- Windows 11 のChrome/Edgeで解凍したファイルを開く操作、および実機でのコンソール確認。
- iOS Safari、Android Chrome、スクリーンリーダーVoiceOver/NVDA/TalkBackによる読み上げ検査。
- ネットワーク由来の実際のAPI読込失敗（**APIを実装していないため**、試作品ではシミュレーション）。
- RegionExport/D Contract 連携、既存のGIS統合、CI/testチェック、main同期、PRレビュー。
- 実データの公式出典・公開日・安全性・人間の根拠承認（本試作の範囲外）。

## Done判定に対する提出状況

- 合成データの一覧→詳細: 実装・画面確認済み
- 正常/欠損/異常の3系統: モックケースで確認済み
- README/TEST_REPORT/スクリーンショット: 同梱
- オーナーの受入と実機検証: **未了**（Integration ready / Merge ready ではない）

## 2026-11-11 オーナー側・実HTTP Chrome回帰（別テスト）

- **新規**：`tests/f02-http-browser.test.cjs` をGitHubの`B Frontend tests`から自動実行（Node22 + headless Chrome、CDP、標準HTTPサーバー）。前掲の提出者によるin-memoryのB01〜B12と区別する。
- **GitHub CIでPASS（初回追加HEAD）**：PR #351 のHEAD `b36b2ea6bf45d43c3f8b12ecc4508a151d2fb05b`、[required test run #42935557252](https://github.com/1kz-ma1/HINANEX/actions/runs/42935557252)。ログに `F02_REAL_HTTP` 3系統が出力され、HTML/CSS/JSの実HTTP読込、合成データ安全注意、詳細選択とフォーカス復元、検索/0件/模擬エラー、320/390/1440px横はみ出し・JS例外なしを確認。これは**実HTTP URLのChromium E2E**で、以前の`page.set_content`とは異なる。
- **最新main同期**：main `ee9116519300780a1712c3b062e0fca6ac7e33cd`（#353統合後）をF02ブランチへ非破壊Mergeし、F02フォルダだけの17ファイル変更を維持。同期後HEAD `0aee4535dd436ca8691aa342553b1a70812bc4ab`。この記録の追記コミットを含む**最新HEADのCIが必要**。過去SHAのPASSをそのまま新HEADへ流用しない。
- **NOT_RUN／対象外**：Safari/Android物理端末、Windows Chrome/Edge、VoiceOver/NVDA、実施設ソース・座標・災害条件の公式承認、RegionExport接続、GIS/F05への統合、Renderの人間確認。
- **状態**：`INDEPENDENT_PROTOTYPE_VERIFIED_IN_CHROME_HTTP`（独立合成試作の自動検証）。**本番施設表示・避難安全性や主UIへの採用は未承認**、Draft PRとIssue #348は継続する。
