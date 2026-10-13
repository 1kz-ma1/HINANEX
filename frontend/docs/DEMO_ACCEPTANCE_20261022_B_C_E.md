# HINANEX 2026-10-22 — B/E 統合デモ受入チェック（B担当記録）

## 目的と範囲

10月22日の7分間の中間発表に向けて、Bの地域分析画面、Cの教育用資料表示、EのGIS画面を**同じ配布候補**で検証するためのチェックシート。

この文書はB担当の表示・導線の受入記録であり、DのRegionExport、EのGIS処理、Cの独立承認を変更・代替しない。最新の証拠なしにチェック欄をPASSにしない。

## 実施前条件

- [ ] 実行対象のbranch/commit SHAと `main` SHAを記録する
- [ ] Dの3地域JSONが元データであり、合成mockに自動fallbackしていないことを確認する
- [ ] ブラウザ・画面サイズ・日時・環境（ローカル/一時バンドル/Render）を記録する
- [ ] 出典、UNKNOWN、0とnullの区別、施設開設状況は未確認との表示を維持する

## B表示の実機受入

| 番号 | 操作と期待値 | 判定 |
|---|---|---|
| B1 | `/frontend/` を開き、江戸川区 `13123` を選択。Dの元Capability、Evidence、Metric `0` と `null` の区別を確認 | NOT RUN |
| B2 | 新潟市 `15100` に切替。遅延した前地域の読込結果で上書きされないことを確認 | NOT RUN |
| B3 | 名古屋市 `23100` に切替。取得件数は自治体全施設数と誤記せず、地理座標の欠損を架空のピンに変換しない | NOT RUN |
| B4 | 各地域の「地図へ戻る」リンクで地域コードが保持される。Eが実際に受け取った後の地図動作はEが受入 | NOT RUN |
| B5 | 証拠事例 `/frontend/evidence-case.html` は別画面で、3状態・4固定出典と最後のUNKNOWN・教育用免責を表示 | AUTOMATED PASS / MANUAL NOT RUN |
| B6 | 改変JSON（OPEN・私的情報・未知フィールド）を選ぶと旧表示を消し、明示エラーを示す | AUTOMATED PASS / MANUAL NOT RUN |
| B7 | PC 1365×900、モバイル390×844で横スクロールやキーボード操作障害がない | AUTOMATED PASS / REAL DEVICE NOT RUN |

## Eとの連携チェック（E担当の受入とは別）

- [ ] 江戸川区 152件・座標152の表示と緑Dクラスタを確認（過去のE実機証跡を今回のPASSへ流用しない）
- [ ] 新潟市 566件・座標566を確認
- [ ] 名古屋市 1602件・座標0を確認し、GIS一覧へ安全に退避できる
- [ ] 洪水ScenarioのUNKNOWNが安全・危険・開設可否へ変換されていない
- [ ] GPS拒否の後も手動座標探索へ復帰できる
- [ ] 外部洪水タイル欠損は独立した配信問題として表示し「浸水なし」と表示しない
- [ ] 90秒デモの同一ブランチ・同一環境での実機リハーサル（E: `gis/docs/DEMO_ACCEPTANCE_20261022.md`）

## 現時点の自動証跡（2026-10-13）

- B `#164` のRender相当3地域デプロイ前ビルド: https://github.com/1kz-ma1/HINANEX/actions/runs/38351800159 （SUCCESS）
- C実生成公開教育JSON → Bの厳格Consumer、Chromium・WebKit、axe自動検査: PR #164の記録を参照
- CのオフラインT0証拠シート生成: https://github.com/1kz-ma1/HINANEX/actions/runs/38352174169 （SUCCESS、**B/Eの画面受入ではない**）

自動テストの緑色は**本番ステージングが更新された証明ではない**。現行Renderは`main`連動のため、Merge Captainの許可前にマージ・デプロイしない。

## 2026-10-13 B実ブラウザ自動テストの実行境界

B専用スクリプト `frontend/scripts/three-region-demo-browser-smoke.mjs` を、共有CI #139の**Render相当の一時配布物**でChromium実行する。BのGitHub required CI成功はスクリプトの構文・単体テスト確認であり、実ブラウザ検証の代用にしない。

```sh
# #139 の共有CI内。Renderデプロイなし。一時HTTPサーバーを8765で起動後に実行。
node b-render-candidate/frontend/scripts/three-region-demo-browser-smoke.mjs \
  "$RUNNER_TEMP/hinanex-render-predeploy-dist" \
  "$RUNNER_TEMP/render-predeploy-three-region-screens"
```

このテストがPASSすれば、次を**自動検証としてのみ**記録可能：

- 3地域の実D JSON切替、1つの選択状態、概要表示、合成mock自動fallbackなし、洪水Scenario UNKNOWNと免責
- Bの地域コード付きGIS URLとローカル同梱E HTMLへのHTTPアクセス（**E地図の動作受入ではない**）
- 不一致のD地域JSON投入で既存概要を消去・エラー化し、正常JSONへ復帰可能
- PC Chromium 1365×900で横幅溢れなし、JavaScript pageerrorなし

未検証として残す：B1のMetric `0/null` とEvidence全表示の目視、B2のネットワーク競合再現、B3の地図上の座標欠損処理（E領域）、Eの地図レイヤー・クラスタ・GPS拒否・90秒デモ、スマホの3地域切替、実Render、Edge実機・Safari・VoiceOver、#89の全体受入。

CIのURL、最終コミット、スクリーンショットartifactと結果を**実行後**に追記する。UNKNOWNや2019年の未確定施設同一性を正式承認へ昇格させない。

## 記録欄（各項目ごとに記入）

- 実施日/時刻、検証者：
- ブランチとコミット SHA：
- 配布候補と環境：
- PCブラウザと画面サイズ：
- スマートフォン/支援技術：
- PASS：
- FAIL（再現手順、Console/Network、添付証跡）：
- NOT RUN（理由）：
- 制約/依存PRと対応Issue：

## 発表時の表現

「確認できた事実を出典付きで表示し、判断できないものはUNKNOWNのまま残す」ことをデモする。**現在安全な避難所の推奨、2019年の予測的中率、正式な施設同一性の承認は主張しない**。

Issue #89 の全体受入、Cによる人手承認、Eの最終GIS検査、Merge Captainの統合判断は独立した未完了ゲート。
