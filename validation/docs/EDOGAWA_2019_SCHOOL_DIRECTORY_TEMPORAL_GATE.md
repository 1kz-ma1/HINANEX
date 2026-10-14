# C 独立時点監査 — 2019年台風19号に使う学校名簿の資料公開ウィンドウ

Status: **C temporal preflight implemented; zero real school roster inputs approved / zero physical facility identities approved.**

関連: [Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142)、[A名簿候補PR #161](https://github.com/1kz-ma1/HINANEX/pull/161)、[事後名簿 #156](https://github.com/1kz-ma1/HINANEX/pull/156)、[C as-of gate #148](https://github.com/1kz-ma1/HINANEX/pull/148)。

## 時点別の評価

災害当時の比較基準 `as_of_jst=2019-10-12T09:00:00+09:00` に対し、以下の**観測された公表日時の精度**を守る。

| 出典 | 時刻の根拠 | C 判定 | 実際の2019年施設入力として使えるか |
|---|---|---|---|
| 東京都2017年度中学校一覧 | データAPIカタログ Created=2018-03-30（元URLは旧HTTP） | `PRIOR_PERIOD_CATALOGUED__VERSION_NOT_VERIFIED`、2017→2019 staleness | NO |
| 東京都2018年度学校一覧 | 都立図書館目録: 刊行2018年10月 | `PRIOR_PERIOD_CATALOGUED__VERSION_NOT_VERIFIED` | NO |
| 東京都2019年度学校一覧 | 都立図書館目録: 刊行2019年10月、**10月12日をまたぐ** | `WINDOW_SPANS_ASOF__PUBLICATION_INSTANT_UNKNOWN` | NO |
| 江戸川区2019年11月適正配置の考え方 | 原資料は災害後の2019年11月 | `AFTER_ASOF__REFERENCE_ONLY` | NO |

**キー判断:** 2019年10月発行という公表月を、勝手に10月1日公開にするのは未来情報の混入。2017年版のカタログが2018年作成でも、2019年にまだ同一施設・同一校舎/住所・夜間学級であったことを証明しない。

## 監査器

`validation/validation/historical_school_directory_gate.py` はAの公開候補データ（**原本そのものではない**）に対して、Cが別に保持した公式資料のURL・候補識別子・資料の公開ウィンドウのルールを照合する。

- 全候補に対し `replay_input_state=BLOCKED` を明示
- データ源の不明・無承認 `raw_sha256=null`、施設identity不明、時点連続性不明を維持
- 公開日が古いものも `historical version/2019 continuity` に承認されるまで候補扱い
- 同月の時点跨ぎを `DATE_WINDOW_OVERLAPS_DISASTER` で拒否
- 災害後の資料を `POST_EVENT_PUBLICATION` として隔離
- データをすり替える / 出典の時刻を勝手に狭める / 合成承認フラグを立てる操作に fail closed
- `eligible_historical_input_source_ids=[]`、`approved_facility_identity_pairs=0`、`predictive_match_or_mismatch_approved=false` を固定

### 使用

```bash
python -m unittest discover -s validation/validation -p 'test_historical_school_directory_gate.py' -v
python validation/validation/historical_school_directory_gate.py \
 --ledger /secure/2019-typhoon19-edogawa-school-roster-candidate-ledger.json \
 --out /secure/2019-school-roster-C-TEMPORAL-BLOCKED.json
```

**exit status 2 = expected BLOCKED**（受入の失敗ではなく未知時点を安全に保留）、`1` = 不正入力・契約違反、`0` は今回の4候補では発生しない。

このスクリプト自体は「C承認を作る」ものではない。原本・配布履歴・同一性の人間による独立確認が整った場合は、**別の新しいsource version / approval contract** を設計し、旧reportに承認を偽造しない。

## 前提と後続

A: **2018年10月の学校一覧の正確な個別学校名・住所**を含む資料を実際に取得、版を固定し、2019年10月11日までの改称・移転・閉校と夜間学級/校舎を追跡する。2017年の旧CSV URLは直接取得失敗だけで自治体が非公開と断定しない。

C: 2019の事後65運用グループ / 66明細を当時学校名簿と関連づける際、名称の一致だけで物理施設リンクを承認しない。 `下小岩小学校`の校舎/所在地変化や`小松川第二中学校【夜間】`の別行を必ず境界として確認。

D/B/E: 正式な歴史版入力とCの承認済みfacility identityが揃うまで、T1/T2を予測結果として示さない。現在の `RegionExport` / `flood_shelter_selection` / CANDIDATE・EXCLUDED・UNKNOWN のContractは無変更。

10月22日の中間発表では、**“調査日・刊行月・原本の公開時刻は別物”** と、2019年10月の月単位資料を安全に保留できる例として説明できる。これはT0 / safety guardの信頼性実証であり予測精度とは別。

### Primary evidence
- 東京都APIカタログ: https://spec.api.metro.tokyo.lg.jp/spec/t000021d1700000002-c0aa9217b65291115b9a588fc71b0c81-0?lang=en
- 都立図書館2021年目録: https://www.library.metro.tokyo.lg.jp/search/research_guide/tokyo/monthly/202103/index.html
- 江戸川区2019年11月配置資料: https://www.city.edogawa.tokyo.jp/documents/8888/r1gakkoutekiseihaitinokanngaekata.pdf
