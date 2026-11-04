# F02 / Issue #348 — 受領後の独立検収（2026-11-04）

- 提出ZIP SHA-256: `a66e3ef0307a721d1a44bf49ffd52002d99e095d29a39179ac352e7b4aa18a9a`
- 位置付け: **合成fixtureを利用する独立Prototype**。正式な施設・開設状況・災害適合性・位置承認ではありません。
- 検収記録: [PR #350](https://github.com/1kz-ma1/HINANEX/pull/350)（Draft／レビュー記録のみ）。
- 依頼元: [Issue #348](https://github.com/1kz-ma1/HINANEX/issues/348)。
- 参照Draft仕様: [PR #346](https://github.com/1kz-ma1/HINANEX/pull/346)。採用済み正本ではありません。

## 再実行したテスト（レビュアー）

**Passed:**
- `unzip -t frontend.zip`：成功
- `node --test tests/*.test.cjs`：10 / 10 PASS
- `npm run lint`：JavaScript構文チェック PASS
- ソースの確認：固定架空データ、`example.invalid`、実API・外部データ接続なし。
- 同梱の4画面スクリーンショットを確認（提出者による実行証拠。実機検証の代わりではない）。

**Failed:** 再実行したNode.jsテスト・構文検査に失敗はありません。

**Not run:**
- 実URLからのChromium E2E：実行環境の`net::ERR_BLOCKED_BY_ADMINISTRATOR`でlocalhostへのページ遷移がブロック。**PASSとは主張しません**。
- Windows Chrome/Edge、iOS Safari、Android Chrome、スクリーンリーダーの実機テスト。
- 実APIやD Contractとの接続、既存GISとの統合（意図的にスコープ外）。
- 本PRのGitHub required CI：PR作成後に確認。

**提出者の報告に限る:** `page.set_content` を用いたChromium 12/12 PASS。URLからのCSS/JS取得を含むE2Eではありません。

## Integration gate

本PRの目的は **受領した独立Prototypeを追跡可能にすること** であり、本番UIへの採用ではありません。

- 元のコード・テストに最小限の追加のみ（このレビュー文書）。
- 既存アプリ、F01洪水、F03保存、F05統合、GIS、D Contract、Schemaは変更しない。
- `UNKNOWN`、座標なし、元資料未取得、地域記録0件、検索0件、模擬取得失敗をそれぞれ別状態として保持。
- `main`へのマージには、最新main／required CI／依存PR／実際の利用者体験を確認する。
- ソース実装が検収済みでも、避難施設データの公開許可や位置承認にはならない。
