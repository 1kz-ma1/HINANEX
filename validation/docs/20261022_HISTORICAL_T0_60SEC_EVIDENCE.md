# C / 10月22日中間発表 — 公式原本からのT0独立監査 60秒エビデンスシート

**この成果物はCの発表用検証記録。Bの製品画面ではない。#89の基礎受入完了・被災リスクや避難所安全性・災害予測精度を証明しない。**

コード: `validation/validation/generate_20261022_t0_evidence_brief.py`。

## 生成元（すべてGitHub ActionsのC独立監査）

| 監査 | 公式原本 | ソースの独立検証 | 14日非公開成果物 |
|---|---|---|---|
| 2019台風19号の学校避難所対応 | [江戸川区PDF](https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf) | [run 38344307696](https://github.com/1kz-ma1/HINANEX/actions/runs/38344307696) | `edogawa-2019-school-roster-C-UNAPPROVED-38344307696` |
| 小松川第二中学校の校舎運営 | [江戸川区・2019/3更新表示HTML](https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html) | [run 38350260260](https://github.com/1kz-ma1/HINANEX/actions/runs/38350260260) | `edogawa-2019-campus-C-UNAPPROVED-38350260260` |
| 学校/夜間学級の別掲載 | [江戸川区2018年8月20日広報](https://www.city.edogawa.tokyo.jp/documents/26598/300820.pdf) | [run 38349472925](https://github.com/1kz-ma1/HINANEX/actions/runs/38349472925) | `edogawa-2018-night-campus-C-UNAPPROVED-38349472925` |
| 横断C検証（施設建物の未確定） | 前3件の独立Cレポートを再照合 | [run 38351185440](https://github.com/1kz-ma1/HINANEX/actions/runs/38351185440) | `edogawa-2019-shelter-building-C-BLOCKED-38351185440` |

このC用生成プログラムは4つのartifact ZIPを**別々に**読み込む。原本のSHA、CスキーマID、C判定、出典の運用番号の65/66、26,761人、通常205・夜間11、別校舎の地区、当日建物ID未確定を独立再確認する。さらに**横断監査が使用した元C JSONのSHA256と、今回受け取った同じC JSONのハッシュが一致するかを再計算**し、混在した異なる実行時点の証拠を受理しない。

## 実行方法

```sh
python -m unittest discover -s validation/validation -p 'test_generate_20261022_t0_evidence_brief.py' -v
python validation/validation/generate_20261022_t0_evidence_brief.py \
 --school-zip /private/school-C.zip \
 --campus-zip /private/campus-C.zip \
 --newsletter-zip /private/newsletter-C.zip \
 --cross-zip /private/cross-C.zip \
 --out-dir /private/20261022_evidence
```

出力:

- `C_20261022_evidence_manifest.json`: T0の機械原本照合・T1の未評価・T2の未実行、分母は`null`、根拠と監査run URL
- `C_20261022_60sec_guide.md`: 60秒の説明台本。根拠を確認した範囲と限界
- `C_20261022_offline_evidence.html`: **Cの技術検証シート**。ネットワーク不要でPCのブラウザから開ける。正式B/EライブUIではない

## 7分発表内での活用（約60秒）

1. 原本で追跡した学校避難所の情報：65運用グループ、66明細、26,761人
2. 間違いが起こりうる箇所：同一報告番号2の通常205/夜間11は2つの明細
3. 2019更新表示の公式校舎資料：通常は小松川2丁目、夜間は平井3丁目、**学校として使われた場所**
4. 最後に**建物対応0件承認**とT1=NOT_EVALUABLE、T2=NOT_RUNを示す。「知らないことを知らないまま残す」を実証

### 自動テストの合格・失敗の意味

- 成功：ソース独立C監査の整合・原本ハッシュ・Cレポートの関係が矛盾しない。**T0の機械照合成功**。
- 失敗：夜間明細を消す、通常校舎所在地を当日の205人の避難建物として確定する、T1予測一致を追加する、C報告の一部を別runへ差し替える、Cステータスを勝手に承認する等を発見。
- 非実施：各施設の当日建物単位の公式ログ、2019版の初回公表履歴と人間によるC承認、Dのas-of推論、避難行動評価、現地でのB/E表示確認、#89の全6項目の最終受入。

**新しく見つかった公式学校日記 (#174) は原本未アーカイブ・C独立監査未実施**のため、このT0完了扱いの表示に含まない（紹介するなら「次の調査候補」と明示）。

## 発表前の実機チェックリスト

- [ ] GitHub Actionsで実際の4 artifactsを使用した生成が完了（CI jobの結果で確認）
- [ ] Edgeで生成されたHTMLをローカルから開き、文字化けと折返しを確認
- [ ] 60秒台本を読み、全体7分の配分に収まるか計測
- [ ] GIS本編 [90秒デモ](https://github.com/1kz-ma1/HINANEX/blob/main/gis/docs/DEMO_ACCEPTANCE_20261022.md) を実機操作し、地図タイル失敗時の録画を準備
- [ ] [Issue #89](https://github.com/1kz-ma1/HINANEX/issues/89) のA/D/C/E/B全体の項目を**別々に**実機受入。C証拠シートでは埋めない

10/19以降は新規デモ要素を増やさず、10/20–21はネットワーク/オフライン両経路の本番練習に専念する。
