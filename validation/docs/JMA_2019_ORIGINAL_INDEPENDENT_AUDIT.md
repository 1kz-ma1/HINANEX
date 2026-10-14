# C 独立監査 — 2019年10月9・10・11日 気象庁資料

**状態: C machine audit design; HTML/PDF currently served bytes only, NOT 2019 publication/edition approval.**

A原本取得: [#150](https://github.com/1kz-ma1/HINANEX/pull/150)、ネットワーク収集: [#151](https://github.com/1kz-ma1/HINANEX/pull/151)、調査: [#149](https://github.com/1kz-ma1/HINANEX/pull/149)、as-of入力検証: [#148](https://github.com/1kz-ma1/HINANEX/pull/148)、発表計画: [#142](https://github.com/1kz-ma1/HINANEX/issues/142)。

## 何を独立確認するか

A取得の6ファイル（3 HTML+3 PDF）を、一切A実装をimportせずに再ハッシュ・URL照合。
- 3 HTML: 気象庁公式URL、2019の各日付、台風19号本文、対応する添付PDFリンクを独立確認。
- 3 PDF: ファイルheaderに加え、PyMuPDFでPDFの本文を読み、`2019-10-09 14:00`、`2019-10-10 14:00`、`2019-10-11 11:00`の文字列が元PDFに記載されているかを確認（PDFの基準時刻/文書時刻であり**実際にオンライン公開された時刻ではない**）。
- manifest は参考として照合するが、Aの承認フラグを信頼しない。独立Cレポートは強制的に `asof_input_approved=false`、`publication_instant_independently_approved=false` を維持。

Cが言える結論は **「現在配信される気象庁資料のHTML/PDF原本が同一の公式記事・発表日と対応し、ハッシュが整合する」**まで。アーカイブの採集は2026-10-13であり、**2019年当時に同一版が存在したか、最初の公開時刻、当時有効な局所情報、予測の当たり外れは未承認**。

## 実行

```bash
python -m unittest discover -s validation/validation -p "test_audit_jma_2019_originals.py" -v
python -m pip install "pymupdf==1.26.4"
python validation/validation/audit_jma_2019_originals.py \
 --archive-zip /secure/jma-2019-originals-UNREVIEWED.zip \
 --report /secure/C_jma_2019_UNAPPROVED.json
```

CIユニットテストは**合成PDF reader**を注入しネットワークもPDF依存ライブラリも不要で実行する。本物の6件に対するC実施には上記PyMuPDFを入れ、実際のZIPを指定する。

## 人間による受入のために残る証拠

- 2019年当時に公開・配布された、時刻/版に紐づく独立の配信履歴や公文書等。現在のHTTP Date、URLファイル名、現在PDFに見える日時をその代わりにしない。
- 2019年の江戸川区で有効だった施設マスター、地図の当時版と観測・運用実績の独立TRUTH。
- JMAの予報は地域規模の災害予測であり、施設単位の開設可否・安全性を直接予測しない。T1/T2は独立した評価対象として設計する。

**CI緑、原本一致を根拠に現在の `UNKNOWN` を勝手に `CANDIDATE/EXCLUDED` に更新しない。**
