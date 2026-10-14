# C 独立監査：2018年広報「小松川第二／夜間学級」から物理施設IDを自動確定しない

**状態：C機械検査コード／実PDFはshared CIで検証予定／2019年の施設同一性・安全性ともに未承認。**

公式一次資料: [広報えどがわ 平成30年8月20日号](https://www.city.edogawa.tokyo.jp/documents/26598/300820.pdf) 印刷2面（PDF index=1）の「区立中学校 学校公開・説明会」。

関連: [Aの出典調査 #165](https://github.com/1kz-ma1/HINANEX/pull/165)、[2020年事後報告の65運用グループ/66明細 #156](https://github.com/1kz-ma1/HINANEX/pull/156)、[過去災害検証 #142](https://github.com/1kz-ma1/HINANEX/issues/142)、[施設同一性 #134](https://github.com/1kz-ma1/HINANEX/issues/134)。

## Cで独立検証する内容
- Aのダウンロード処理をimportせず、保存されたPDF原本バイトを再ハッシュ・公式URL・元記事の日付・ページ本文を独立検査。
- 「小松川第二」と「小松川第二 夜間学級」が**別掲載されている**ことを検査。夜間学級の文字列を除去しても別の「小松川第二」記述が存在する必要がある。
- 出典の意味は「2018年の学校案内上の別項目」であり、「2019年10月に二つの避難所が開いていた」「物理校舎のIDが等しい/異なる」ではない。
- Aの`school_night_physical_site_equivalence=true/false`のような主張は機械検査で拒否。**`null`（不明）を維持**する。
- 2020年災害対応の通常205・夜間11は事後運用TRUTHであり、この2018年の資料に戻して入力しない。

## 公式沿革の扱い
学校の[沿革（後年更新）](https://edogawa.schoolweb.ne.jp/1320032/page/frm4cd26abc60641)では、2018年4月に通常課程が新校舎へ移り夜間学級は旧校舎に残った旨が検索結果に記載。ただし直接アクセス403であり原本は独立確認できていない。また[江戸川区の統合後の説明（2024年更新）](https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/togo/komatugawatiiki.html)は2023統合の説明であり、**2019当時の公表原本・個別避難施設場所を自動承認するための証拠ではない**。

## テストと実データ実行
```sh
python -m unittest discover -s validation/validation -p 'test_audit_edogawa_2018_school_identity.py' -v
python -m pip install 'pymupdf==1.26.4'
python validation/validation/audit_edogawa_2018_school_identity.py \
 --archive-zip /private/2018-kouhou-UNREVIEWED.zip \
 --report /private/C_2018_school_identity_UNAPPROVED.json
```

合成テスト（2行・夜間行欠落・通常行欠落・承認偽装・改ざん・余分なZIPメンバー）と実PDFの検証結果は区別する。出力 `C_2018_SCHOOL_LABELS_AND_ORIGINAL_BYTES_VERIFIED__IDENTITY_NOT_APPROVED` は**PDF原本に含まれる表記のT0検証**であり、2019年の施設位置・予測精度・避難判断に使えるという意味ではない。

**次ゲート：** 2019年に有効だった通常/夜間の校舎の公的地番・統合前後の配置を、2019当時の公式資料と独立確認する。物理建物が同じ/異なるか、避難所としてどう使われたかは依然`UNKNOWN`であり人手レビューが必要。
