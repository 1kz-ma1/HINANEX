# C 独立監査 — 2019年江戸川区の公式原本アーカイブ

Status: **implemented independent byte + HTML label/row verification; independent C human acceptance still NOT performed.**

- 対象: [A候補 #144](https://github.com/1kz-ma1/HINANEX/pull/144)、[A原本取得 #145](https://github.com/1kz-ma1/HINANEX/pull/145)、[shared実行 #146](https://github.com/1kz-ma1/HINANEX/pull/146) の短期UNREVIEWEDアーティファクト。
- 目的: Aの取得側コードをimportせず、原本のSHA256とサイズを再計算する。東京都第23/36/49報の**HTML文面の発表日時・避難所開設時点・江戸川区の行**を独立に抽出する。
- 判定対象外: 江戸川区2019事後回顧の105施設と学校PDFの意味・施設同一性・公開当時の原本版・気象や避難安全性・2019年当時利用可能な入力・将来予測の当たり外れ。

## 実行例（Python 3.12 / 標準ライブラリ）

```sh
python -m unittest discover -s validation/validation -p 'test_historical_edogawa_archive.py' -v
python validation/validation/audit_historical_edogawa_archive.py \
  --archive-zip /secure/edogawa-2019-originals-UNREVIEWED.zip \
  --report /secure/reviews/edogawa-C-unapproved.json
```

アーティファクトに含まれる公式原本は短期保管し、Git管理下へ追加しない。取得結果を差し替えず、正規化前のバイトで監査する。

成功出力は`C_INDEPENDENT_BYTE_AND_HTML_CHECKS_PASSED__UNREVIEWED`。**これは「公式資料の現在取得された原本の行・時刻・ハッシュが整合した」だけで、当時の予測入力として承認したことを意味しない。** 自動レポートも`historical_as_of_approved=false`、`facility_pairs_approved=0`、`replay_match_or_mismatch_approved=false`。

承認前の停止条件: HTML上の行・公表/観測時刻・出典の矛盾、HTTPレスポンス変更、PDF再発行の疑い、施設識別子未承認、2019当時版の立証不足、post-event入力混入。人が根拠資料の時点・版とT1比較対象を承認するまで、D/B/E側の予測成功・失敗表示は許可しない。

既存の`RegionExport`/Scenario/Schema・安全区分は不変。Issue #142 / #89を継続。
