# C独立検証：2019年5月発行表記の江戸川区水害ハザードマップ別コピー

**2026-10-13 / 未承認 / 2019年のas-of入力採用なし**

- Aの発見・原本候補: [PR #153](https://github.com/1kz-ma1/HINANEX/pull/153)
- Shared取得CI: [PR #154](https://github.com/1kz-ma1/HINANEX/pull/154)
- 計画: [Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142)

## 独立監査の目的

東京都立紅葉川高校の公式サイト上のPDFは、目視で「2019年5月発行」の地図表記を確認できる。一方、**PDFの内部作成日時は2020-08-21**、HTTP Last-Modifiedは2020-08-23と取得原本上で観測された。これはそのデジタルファイルのコンテナが災害後に作られたことを示す**メタデータ**であり、地図の図版そのものが2019年に存在しなかったことの証明にはならない。PDFメタデータは後から編集可能であり、絶対的な発行証明ではない。

本CチェックはAの取得プログラムをimportせず、ZIP内の**生PDFのSHA-256**、公式PDF URL、構造、PDF metadata `creationDate`、ページ数・ラスタ画像数・抽出可能テキスト長を確認する。PDF画像の文字はOCRしない。文字が機械抽出不可の場合は `map_visual_text_review_required=true` とする。

## 実際の初期観測（C手動ローカル調査）

- SHA-256: `60efaf0c3b47d5bd06ad2330e0dafda1dfccb17b0ab5a8737cd91d0578eb5dca`
- サイズ: 839,166 bytes、1 page、PDF 1.4、画像1枚、テキスト抽出0文字。
- PDF `CreationDate: D:20200821165450+00'00'`。当日以前に存在した**元の紙地図**や冊子の内容と同じだったかは未確定。
- HTTP `Last-Modified: Sun, 23 Aug 2020 23:20:30 GMT`（現在配信サーバー上の情報であり、2019公開の証拠ではない）。
- Actions原本取得は #154（raw artifact 14日保存、2026-10-27まで）。Cの**自動監査**とCの**人による地図ラベル解釈**は区別。

## 結論と実機表示の制約

1. 資料自体を `2019年5月発行表記の地図の別コピー候補` と分類する。2019-10-12に同一PDFが配信されたとは主張しない。
2. PDFの作成日時2020年を、地図発行2019年と混同しない。`pdf_container_metadata_indicates_post_event=true` は**警告**であり、2019内容の否定でも洪水予測の不一致でもない。
3. PDFの地図の凡例や施設点を機械的に読み取って予測入力・施設の座標や洪水安全性へ使わない。OCRで埋めない。2019施設IDを後年名簿と自動joinしない。
4. `historical_version_verified=false`、`asof_input_approved=false`、`facility_identity_approved=false`、`prediction_accuracy_evaluated=false` は変更しない。
5. 次の受入要件は、2019年に配布された当時版の保管記録または独立の版・内容照合、Cの目視確認、2019施設マスターIDと当時の地図凡例に対する自治体公式の意味確認。
6. 発表では**「旧版らしい地図も見つけられるが、デジタル再掲された日時と版の正当性を区別して採用保留する」**例として使用可能。T1/T2の予測成功・失敗には計上しない。

## 実行

```bash
python -m unittest discover -s validation/validation -p 'test_audit_edogawa_2019_map_copy.py' -v
python -m pip install 'pymupdf==1.26.4'
python validation/validation/audit_edogawa_2019_map_copy.py \
  --archive-zip /secure/edogawa-2019-map-UNREVIEWED.zip \
  --report /secure/C_map_UNAPPROVED.json
```

CI単体テストは合成PDF検証器を使用し実データを模倣しただけ。本物のPDFに対する監査をCが行うときは、PDFそのものとSHAの再計算が必須。出力の成功は**自動検査成功**であり人の正式承認ではない。

スコープ: `validation/**` のみ。Shared Contract、DのScenario、GIS、Render、災害情報の安全区分に変更なし。
