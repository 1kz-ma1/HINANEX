# A — 2019年台風19号・江戸川区の学校避難所「事後」運用名簿の抽出

**作業日:** 2026-10-13 / **分類: post-event TRUTH candidate; 2019-10-12 replay INPUTとして使用禁止**

公式原本: https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf

元PDFは [A/Sharedの原本保存 PR #145/#146](https://github.com/1kz-ma1/HINANEX/pull/146) のoriginal artifactでハッシュ固定済み（2026-10-27まで保存）。今回の対象SHA256:

`89fc7de1810685aaf48a5c6fd6f4c79d6888e1ffb3d6314756fa5665d652b380`

取得したPDFの内部メタデータは **2020-01-06作成**、**2020-01-10更新**、全18ページ。報告書は2019年10月の出来事を**後からまとめた資料**。現行江戸川区の案内ページが2026年に更新されているため、PDFのイベント前公表は主張しない。翌日の避難開設数を予測入力へ戻すことは厳禁。

## 報告書の注意点（PDFページ3・内部index=2）

- 小学校42グループの避難者**19,061人**、中学校21グループの**7,564人**、その他2グループの**136人** = 運用グループ**65**、避難者**26,761人**。
- 実際の表には、**66行の個別明細**が存在。中学校の番号**2**（小松川第二中学校）には**通常205人と夜間11人の2行**があり、単純に1行=1施設だと66施設という誤りを作る。中学校の他20グループは各1行。
- `葛西小・中学校`は学校名の複合施設として記録される。名前や中点で勝手に2施設へ分割しない。
- `旧平井二小学校` / `旧清新第二小学校`が「その他」に2レコード。2026年の学校一覧と自動joinすることは禁止。
- 職員参集数は全体601/789（小学校397/512、中学校192/261、その他12/16）。これも行の欠落を検出するための出典ベース整合チェックになる。
- 同一性が確認できないものは`facility_id=null`、`normalized_facility_id=null`、`facility_identity_review_state=NOT_REVIEWED`。この`65`はPDF側の運用集計単位であり、物理的な施設IDの種類・数ではない。

## A実装

`data-research/tools/extract_edogawa_2019_school_roster.py` は**PyMuPDFのPDF内部の文字データ＋行座標**のみを読み、原本レコードを意味推測なしに抽出する。OCR・geocoding・施設名の正規化は行わない。左表42、右上表21（22明細）、右下表2を元の番号に沿って検査。付属の夜間レコードを同一グループにまとめるが名前・個別人数は別々に残す。

```bash
python -m pip install 'pymupdf==1.26.4'
python -m unittest discover -s data-research/tests -p 'test_extract_edogawa_2019_school_roster.py' -v
python data-research/tools/extract_edogawa_2019_school_roster.py \
 --source-pdf /private/edogawa-school-ops-review.pdf \
 --out /private/edogawa-2019-school-operational-rows-UNREVIEWED.json
```

原本がSHA違いの場合はハード停止し、別版を同じ原本として黙認しない。JSONには`source_page_index` / `source_y_pt` / `printed_name` / `source_group_id` / `source_detail_id` / `evacuees_reported` / `municipal_staff_attended` / `municipal_staff_total`と不採用フラグを出す。Raw PDF/抽出JSONをmainや公開デモ画面へ無断commitせず、短期Actions artifactでCの独立確認へ引き渡す。

## 未来情報混入を防ぐ境界

- このPDFは事後TRUTH候補であって、開設判断を事前予測するINPUTではない。
- 65は`RegionExport`の現行152施設、都速報の48/73/98「避難所箇所数」と**異なる時間・範囲/集計対象**。そのまま差分を予測失敗件数として表示しない。
- ページの記録は「開設時刻」「施設安全性」「洪水時の適合性」を施設ごとに確定しない。報告書の総括13:40の開設完了を、65レコードのすべてに共通する個別開設日時と補完しない。
- 必須の後続：**C独立のPDF→抽出照合**、2019時点の施設マスターと公開履歴、同一性の人間承認、T1対象の定義。B/Eにはまだ「2019予測成功/失敗」ラベルを出さない。

参考: [Replay計画 #142](https://github.com/1kz-ma1/HINANEX/issues/142)、[同一性 #134](https://github.com/1kz-ma1/HINANEX/issues/134)、[基礎DoD #89](https://github.com/1kz-ma1/HINANEX/issues/89)。
