# C独立監査 — 2019年台風19号・江戸川区学校避難所事後名簿

**2026-10-13 / CODE PROPOSED / NO HUMAN SOURCE SEMANTIC APPROVAL / post-event TRUTH only**

- 公式PDF: https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf
- SHA256: `89fc7de1810685aaf48a5c6fd6f4c79d6888e1ffb3d6314756fa5665d652b380`（現在固定済み原本）
- A抽出: [PR #156](https://github.com/1kz-ma1/HINANEX/pull/156) / 進捗 [Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142)
- A PDF原本アーカイブ: [PR #146](https://github.com/1kz-ma1/HINANEX/pull/146)（証拠は2026-10-27まで）
- このCは**Aの抽出プログラムをimportしない**。

## 検証対象と独立照合

PDFページindex=2（印刷ページ2）の学校避難所表について、Cが原本から**直接文字情報と位置を再抽出**し、AのJSONと比較する。

1. 文字ラベルと行位置、3区分の明細数を独立確認。
2. 表に印字された番号（小学校1–42、中学校1–21、その他1–2）と、Aのsource-group番号を独立照合。
3. 各行の避難者、職員参集、職員総数、参集率の数値を元PDFのセルと直接照合。
4. 中学校番号2が**通常205人 + 夜間11人 = 1運用グループの2明細**となることを検証（グループとしての216人）。そのほかの番号は1明細ずつ。
5. 42+21+2=65グループ、42+22+2=66詳細行、19,061+7,564+136=26,761避難者、職員601/789を監査。人数の欠損・改ざん・重複・夜間行の欠落を拒否。
6. source SHA、施設IDが全てnull、評価用の旧→現行施設joinが未承認であることをゲートする。

これらは**源データと抽出結果の一致（T0）を確かめるための機械的テスト**であって、実際の2019年時点での予測、各校の洪水時の安全性、開設時刻、施設名改称・移転後の同一性を認定するものではない。

## 受入制約

元PDFは災害後の作成で、2020年1月作成と記録されている。従って`evidence_role=POST_EVENT_TRUTH_CANDIDATE_ONLY`、`historical_asof_input_approved=false`、`physical_facility_pairs_approved=0`、`prediction_accuracy_evaluated=false`を固定。

**65のoperational source units != 65 physical buildings.** 小松川二中夜間の別明細、葛西小・中学校の複合名、旧学校施設があり、現在のRegionExport 152施設との名称推測joinは禁止。東京都の時点別開設数48/73/98は「学校65グループ」と母集団・時刻・集計定義が異なる。差を予測エラーとしない。

## 実行方法

```bash
python -m unittest discover -s validation/validation -p 'test_audit_edogawa_2019_school_roster.py' -v
python -m pip install 'pymupdf==1.26.4'
python validation/validation/audit_edogawa_2019_school_roster.py \
 --source-pdf /private/edogawa-school-ops-review.pdf \
 --a-roster-json /private/edogawa-2019-operational-roster-UNREVIEWED.json \
 --report /private/C_edogawa_school_roster_UNAPPROVED.json
```

C専用offline unittestは合成文字・表を用いるだけ。実物のPDFとA結果を同じhosted runnerで独立突合する必要がある。CI成功のみで`C_APPROVED`や安全性判定に昇格しない。

次は2019年当時に実際に公表済みだった学校施設名簿・公式防災計画の版をA側で特定し、**Cの人間による原本・版・施設同一性レビュー**が済んだ対象だけT1予測照合に採用する。2019の公式地図については#153–155の別版検証を維持する。
