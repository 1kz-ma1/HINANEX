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
