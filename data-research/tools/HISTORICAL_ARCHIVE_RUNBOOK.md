# 2019年台風19号・江戸川区 A公式原本アーカイブ Runbook

**Status: tooling implemented; original HTTPS execution only after GitHub Actions success; NO historical-as-of or C semantic approval.**

## 対象

`data-research/scenarios/2019-typhoon19-edogawa-source-candidates.json` 内の候補から、次の5件のみを原本固定対象とする。

- 東京都 第23報（2019-10-12 16:00公表表記、12:00時点の48か所）
- 東京都 第36報（2019-10-12 21:00公表表記、15:00時点の73か所）
- 東京都 第49報（2019-10-13 02:00公表表記、00:00時点の98か所）
- 江戸川区 2019-11-01区長回顧（イベント全体105施設、単一時点とは異なる）
- 江戸川区 学校避難所対応まとめPDF（事後検証候補であり、当時の入力ではない）

気象庁の事後レポートや未取得・404の区施設PDFは今回の取得対象外。現在の URL を取得できても、**そのページの2019年の内容が当時そのまま存在した証拠にはならない**。出典ページが2026年に更新されている場合、当時入力へ使わない。

## 操作手順（Python 3.12、stdlibのみ）

```sh
python -m unittest discover -s data-research/tests -p 'test_archive_historical_edogawa.py' -v
python data-research/tools/archive_historical_edogawa.py \
  --ledger data-research/scenarios/2019-typhoon19-edogawa-source-candidates.json \
  --out-dir /tmp/hinanex-historical-UNREVIEWED
python data-research/tools/archive_historical_edogawa.py \
  --ledger data-research/scenarios/2019-typhoon19-edogawa-source-candidates.json \
  --verify-dir /tmp/hinanex-historical-UNREVIEWED
```

- ネットワークが使えないローカル環境では取得を成功と偽装せず、ネットワーク有効な専用 GitHub Actions runner を別 shared PR で用いる。
- Raw HTML/PDFはGit管理内に置かず、Actions の短期private artifactのみに保存。artifactには`manifest.json`とオリジナル5件が入る。
- 空でない出力フォルダーへの上書きを拒否。HTTPS公式hostと候補ID、HTTP 200、URLリダイレクト禁止、HTML/PDF signature、取得サイズ上限、bytes+SHA256を確認。
- `manifest.json` の `claimed_published_at_jst` は候補台帳のメモであり、当時の配信内容を証明するものではない。HTTP `Date`/`Last-Modified`も通常は現在の配信に関する情報。予測入力`release_time <= as_of`の根拠にはできない。
- Manifestの`historical_as_of_approved=false`、`facility_pairs_approved=0`、`prediction_accuracy_evaluated=false`は固定。不足時に値を補完しない。

## Cへの引渡しと停止条件

Cが同じartifactの**原本bytesから独立に**SHA/shape/行・施設の計測値・時間・比較母集団を検証する。Aの確認プログラムが成功しただけでは独立監査にならない。Cレビューレポートが揃うまで`MATCH/MISMATCH`実績を追加しない。

**停止**: タイムスタンプの矛盾、年度の相違、偽HTML・PDF、HTTPの失敗、redirect、改ざん、source ID/URL変化、非適切な施設joinを確認したら、別の値を捏造して通さず差分と原因をIssue #142へ記録する。

契約への影響: なし。D RegionExport、C評価、B/E画面、既存洪水Scenarioは変更しない。
