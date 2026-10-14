# C — 2019年台風19号・小松川第二中学校「学校の校舎」と「当日避難した建物」の横断監査

2026-10-13 / **実際の205人・夜間11人の避難先建物はともにUNKNOWN、正式な施設同一性リンクは0件。**

検証器: `validation/validation/verify_2019_event_shelter_building_lineage.py`。
A Evidenceの候補台帳: [#171](https://github.com/1kz-ma1/HINANEX/pull/171)。
過去の独立監査: 2018年広報[#166](https://github.com/1kz-ma1/HINANEX/pull/166) / 2019年3月表示の区の校舎改築ページ[#169](https://github.com/1kz-ma1/HINANEX/pull/169) / 2020年災害後事後報告[#159](https://github.com/1kz-ma1/HINANEX/pull/159)。

## 新しいC横断判定

3つの**異なる原本に対する独立監査済みレポート**を読む。Aの抽出/アーカイブ処理には依存しない。
- 校舎の公式記載は **通常＝小松川2丁目10番2号、夜間＝平井3丁目**。原本HTMLの監査レポートは両者を異なる**学校運営地区**と認識する一方、`actual_shelter_used_building_for_205`と`...11`は`null`。
- 江戸川区2018年広報は通常課程・夜間学級を別行で記載。**この掲載区分自体は災害当日の建物の証拠ではない。**
- 2020年作成の学校避難所事後報告は**学校運用番号2、通常205／夜間11**、65運用グループ／66実績明細／26,761人を公式原本と独立照合済み。2行を「1建物」とみなさない。
- 後年版の[避難所開設・運営マニュアル](https://www.city.edogawa.tokyo.jp/documents/557/hinanjo.pdf)の検索索引には通常No.2、夜間No.3の設備行が掲載。ただし**2020・2022年の改訂**が入っているため、2019年時点の設備・開設状況に遡及して使用禁止。取得・SHA固定が未完了。
- 後年の[学校沿革](https://edogawa.schoolweb.ne.jp/1320032/page/frm4cd26abc60641)が旧平井校舎を「平井3丁目20番1号」と呼ぶことは、**夜間11人の当日の避難場所の確定根拠ではない**。

Cは出典URL+raw SHA256+各Cレポートのsource role/評価フラグと原文に対応する数値を突き合わせる。汚染を検出したらexit 1。正常な資料の組合せでも、当日建物が未確認なので**exit 2 / `BLOCKED_ACTUAL_EVENT_SHELTER_BUILDING_LINK__NEEDS_OFFICIAL_OPERATION_LOG`** を返す。exit 2はテスト実行そのものの失敗ではなく、事実の不足を正しく拒否するための想定結果。

## 2019年の施設同一性を承認するには

**本検証器にfake trueフラグを入れて解除することは禁止**。新しい公式原本が必要。

- 2019-10-12に施設ごとの**実際の開設/受入建物を識別できる運用日誌**・施設別報告・受入台帳を取得し、表にある通常205／夜間11と**どの建物か**を直接関連付ける。
- その原本の日付・版・作成者、施設位置ID、当時の建物状態をAで収集し、Cが独立に人手レビューする。
- 2019時点の施設マスターに学校名のみで自動joinせず、旧校舎/新校舎/2023統合校舎を区別する。
- 過去の災害予測T1/T2（MATCH/MISMATCH）は独立した予測ロジックが実装され、当時利用可能な入力が承認されるまでは**0件**。

## 実行

```bash
python -m unittest discover -s validation/validation -p 'test_verify_2019_event_shelter_building_lineage.py' -v
python validation/validation/verify_2019_event_shelter_building_lineage.py \
 --a-ledger /private/A_2019_shelter_building_candidates.json \
 --c-campus-report /private/C_2019_campus.json \
 --c-newsletter-report /private/C_2018_school.json \
 --c-ops-report /private/C_2020_postevent_school.json \
 --out /private/C_2019_building_link_BLOCKED.json
```

この出力は**内部Cレポート**であり、RegionExportやGISに新たな安全/危険判定を追加する契約ではない。発表では「校舎の位置は分かっても、当日の避難先まで自動推測しない」を説明する実例としてのみ使う。Merge Captainのmain統合承認まではDraft/blocked。
