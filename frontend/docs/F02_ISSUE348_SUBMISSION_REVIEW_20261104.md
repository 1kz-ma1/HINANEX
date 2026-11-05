# F02 / Issue #348 班員提出物レビュー・受入管理記録

- 記録日: 2026-11-04
- 対象: 班員提出 `frontend.zip`、F02「避難施設の独立した一覧・詳細UI」
- Issue: https://github.com/1kz-ma1/HINANEX/issues/348
- 位置付け: **REVIEWED / PROTOTYPE-ONLY / NOT INTEGRATION READY**
- 検査基準: `AGENTS.md`、`frontend/AGENTS.md`、Issue #348、[F02提案仕様](https://github.com/1kz-ma1/HINANEX/blob/docs/feature-specs-20261030/docs/strategy/features/02_SHELTER_REFERENCE.md)
- 仕様書の効力: F02提案仕様を含む PR #346 は Draft・未統合。将来仕様の採用承認や本番接続はこのレビューに含まない。
- 提出ZIP SHA-256: `a66e3ef0307a721d1a44bf49ffd52002d99e095d29a39179ac352e7b4aa18a9a`
- 作業開始時点 main: `e60a886e323e0b39187f63d493286eebbf3208b8`

## 受領内容（提出物の事実）

ZIP の `frontend/prototypes/f02-shelter-explore/` に次の成果物が含まれる。

- `index.html`、`styles.css`、`app.js`、`model.js`、`fixtures.js`
- `package.json`、`tests/f02-model.test.cjs`
- `README.md`、`TEST_REPORT.md`、`browser_test_results.json`
- `screenshots/desktop-list.png`、`desktop-detail.png`、`mobile-list.png`、`mobile-detail.png`

ZIP の `__MACOSX/` および `._*` は macOS 由来のメタデータで、取り込み対象外。

## 仕様との適合（ソース・画面・提出報告の確認）

| 項目 | 検収観点 | 判定 |
| --- | --- | --- |
| 独立した一覧・詳細 | 固定2件比較や既存GISと未接続 | 確認 |
| 架空データだけ | 架空地域・施設、`example.invalid`、リンク無効 | 確認 |
| 検索・地域選択 | 検索文字種の正規化、地域間の自動名寄せなし | 確認 |
| 欠損と異常の分離 | UNKNOWN、座標なし、資料未取得、0件、検索0件、疑似読込エラー | 確認 |
| 誤認防止 | 合成・安全非保証の固定注意、原記号の独自判定なし | 確認 |
| キーボード・小画面 | コードと提出スクリーンショットで確認 | 一部確認。実機・読み上げは未確認 |
| Contract | RegionExport、Schema、実API、F01、F03、F05には未接続 | 確認 |

本レビューの「確認」は **独立試作としての挙動・構造** のみを指し、公式施設指定・災害時の安全性・開設可否・位置承認を意味しない。

## テスト結果の区別

### Passed（オーナー側の再実行）

- ZIP 展開検査: `unzip -t frontend.zip` → エラーなし
- Node.js `v22.16.0`: `node --test tests/*.test.cjs` → **10 / 10 PASS**
- `npm run lint`（3 JS ファイルの `node --check`）→ **PASS**
- 静的ソース点検: 実在施設、実API呼出、推測座標、他担当領域への変更なし
- 提出された desktop/mobile の4画面キャプチャを目視確認

### Passed（班員の提出報告、独立再実行ではない）

- Chromium の `page.set_content` を使った表示・操作検証: 提出報告上 12 / 12 PASS
- `file://` または `localhost` の外部CSS/JS実読込に対する E2E 成功は報告されていない

### Failed

- オーナー側の Node.js / 構文検査: 0 件

### Not run / Blocker

- 実URL経由での HTML/CSS/JS 読込、リポジトリCI、最新mainでの回帰
- Windows Chrome/Edge、iOS Safari、Android Chrome、スクリーンリーダー実機
- 実API・RegionExport・既存GISの接続（この試作の範囲外）
- 本体への正式採用・本番表示許可
- このレビュー文書は**受領ZIPのソースやPNGそのものをGitHubに追加した証明ではない**。実装ファイルの取り込みは別途必要

## 受入判定と次のゲート

**独立試作として内容を検収し、仕様上の明白な逸脱は見つからなかった。GitHubへのソース取り込み・main統合は未了。**

1. 本レビュー記録とZIPの同一性をハッシュで追跡可能にする。
2. `frontend/prototypes/f02-shelter-explore/` へソース・テスト・画面証拠を変更最小限で取り込み、`__MACOSX` を除外する。異なる担当領域には変更しない。
3. 実URLでの読み込み、PC/スマホ操作、必要なアクセシビリティ確認を追加実施。
4. 最新mainとの整合性、CI required check `test`、PR差分を確認し、Merge Captain が最終判断する。
5. D Contract マッピングと実施設データ接続は **別の設計判断・別スライス** とする。F02試作の受領をF05統合許可とみなさない。

**禁止**: 未確認座標の補完、安全・開設・災害適合の推定、公式意味の独自変換、Draft仕様を既成事実化すること。

## レビュー上の推奨処理

- Issue #348 は元の Done 条件（提出物の検収・オーナー確認）に従って扱い、いきなり本番機能を Done としない。
- 本レビューだけでは `merge: ready` を付与しない。mainは変更しない。
- 作業の進捗表現は `SUBMISSION_REVIEWED`（提出物点検済み）とし、`INTEGRATION_READY` と区別する。
