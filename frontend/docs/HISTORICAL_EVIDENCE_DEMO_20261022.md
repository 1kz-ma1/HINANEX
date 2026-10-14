# 2019年台風19号・江戸川区 / 発表用3ケース説明画面

`/frontend/historical-evidence-demo.html` を開く。**地域移動デモとは別機能**であり、D RegionExport・GIS・洪水ラスタ・開設状況を変更しない。ケースはC-owned `/evidence/2019_edogawa_evidence_cases.json`（#226 / #227）からのみ取得する。配布ファイルが無い・整合しないときは画面を表示せず、偽の結果へfallbackしない。

| ケース | 本当に示すこと | 示さないこと |
| --- | --- | --- |
| ① T0 | 公式事後原本→抽出の65/66/26761はC機械検証済み | 予測MATCHではない |
| ② T1 | 205/11の当日避難先建物は未特定、比較不可 | 保留が当たった/危険の証明ではない |
| ③ TEST | 合成入力の不当な明細削除・建物確定をCが拒否 | 実災害の予測MISMATCHではない |

ボタンの選択はUI表示だけを変更し、Cの判定を再計算しない。25秒×3ケースの自動進行＋約15秒導入＝約90秒の発表パート。手動ケース選択、一時停止、次へ、リセットを実装。ページ非表示で再生停止。原本とC監査のURLへ安全にリンク。

## 動作・確認
- `npm test` → C deck contract negative testsとHTMLガード（Node.js 22）。
- `npm run build` / `npm run lint` → 静的ファイル・構文を検証。
- `python deploy/build_staging.py --skip-pipeline` → D成果物が存在する環境で配布物を組み立てる（C JSONは通常のDとは別）。
- 配布は `/frontend/historical-evidence-demo.html`、JSONは `/evidence/2019_edogawa_evidence_cases.json`。
- 実機のEdge/スマホ/90秒発話/Render HTTPS/外部リンクの可用性は、人間による別途受入を要する。
