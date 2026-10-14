# C独立監査 — 2019年3月更新の江戸川区学校校舎ページ／災害時の避難所建物は別

公式ページ: https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html

**状態**: CのHTML原本検査を実装。**当時のWeb版の真正性未承認／台風19号当日の避難所施設同一性はUNKNOWN／予測実績0件**。

関連 [A原本候補 #168](https://github.com/1kz-ma1/HINANEX/pull/168)、[2018年の広報証拠 #165–167](https://github.com/1kz-ma1/HINANEX/pull/167)、[事後65グループ/66明細 #156/#159](https://github.com/1kz-ma1/HINANEX/pull/159)、[Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142)。

## Cが現行公式ページから独立確認する項目

| 項目 | 原文に確認すること | まだ確認しないこと |
|---|---|---|
| ページ時点 | 更新日：2019年3月1日 | その日と完全同一byteがWeb公開されていたこと |
| 通常課程 | 2018年4月から新校舎、区内**小松川2丁目** | 台風19号時の避難者205人がこの新校舎内にいたこと |
| 新校舎施設概要 | **小松川2丁目10番2号** | 夜間学級の住所 |
| 夜間学級 | **平井3丁目で学校運営** | 平井3丁目より細かな住居表示／夜間避難者11人の滞在建物 |
| 2019年時点の通常・夜間の学校運営地区 | **異なる2地区である旨のページ記載** | 2019年10月12日に別々の建物が避難所として開いていたか |

出典ページのHTMLにある**当時の校舎運営**の主張と、災害後に編集された**実際の避難所利用（205人/11人）**の事実は概念が別。Cの解析で`source_states_different_school_operation_districts=true`でも、`actual_shelter_used_building_for_205=null`および`..._11=null`を維持。

## 監査と停止条件

- Aの取得コードはimportせず、Cが保存HTMLの**生byte SHA256**を再計算。公式URL、更新日、通常課程の所在地、夜間学級の平井3丁目、2018年4月からの新校舎運営を本文から検証。
- 変更・欠損・URL差替・偽C承認をfail-closed。夜間の細住所、緯度経度、統合校舎ID等を推測しない。
- 現在Webサイトの表示上の更新日は2019年3月1日でも、原本HTMLの当時の版と公表時刻は**C人間監査による別確認が必要**。成功ステータスは現在取得されたHTML原本の内容一致（T0）だけを指す。
- Cは出典ページを根拠に施設の安全性、開設状況、T1/T2 MATCH/MISMATCH、予測時点データ適格性を自動承認しない。

```sh
python -m unittest discover -s validation/validation -p 'test_audit_edogawa_2019_campus_source.py' -v
python validation/validation/audit_edogawa_2019_campus_source.py \
  --archive-zip /private/2019-campuses-html-UNREVIEWED.zip \
  --report /private/C_school_campuses_2019_UNAPPROVED.json
```

C outputは `C_PAGE_CAMPUS_CLAIMS_VERIFIED__SHELTER_SITE_UNAPPROVED` を用いる。出力CSV等から現在の避難所施設IDへ自動joinしない。独立した2019-10-12当日の避難所指定施設名簿と具体的な建物使用記録を見つけた場合のみ個別レビューへ進む。
