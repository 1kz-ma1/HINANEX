# A Evidence — 2019年台風19号の205人・11人を受け入れた「建物」の立証状況

**2026-10-13調査 / ACTUAL EVACUATION BUILDING = UNKNOWN / 物理避難所リンク承認0 / T1予測評価0**

対象: `junior_high:02` にまとめられた通常205人と夜間11人は**事後報告の2明細**。運用グループ番号が同じでも同じ建物ではない可能性を排除できない。

| Source | 出典と時点 | 直接裏付けられる内容 | 裏付けられない内容 |
|---|---|---|---|
| 江戸川区の[2019年3月更新表示の校舎改築説明](https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html) | 表示日2019-03-01、A raw+C automated T0 #168–170 | 通常課程は小松川2丁目10番2号の新校舎／夜間学級は平井3丁目で学校運営 | 台風当日の205人/11人それぞれの「避難者を受け入れた建物」 |
| 江戸川区の[2018年8月20日広報](https://www.city.edogawa.tokyo.jp/documents/26598/300820.pdf) | 印字2018-08-20、A raw+C automated T0 #165–167 | 学校公開一覧が小松川第二・同夜間学級を別々の掲載項目として扱う | 校舎の建物住所・当時避難所の開設 |
| 江戸川区の[2020年作成・台風19号学校避難所事後記録](https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf) | POST_EVENT_TRUTH、A raw+C automated T0 #156/#159/#160 | `junior_high:02` に通常205人／夜間11人、職員・人数・明細行は原本確認済 | 二つの行がそれぞれ新校舎/旧校舎を利用したと断定できる施設住所・建物ID |
| 江戸川区[避難所開設・運営マニュアル](https://www.city.edogawa.tokyo.jp/documents/557/hinanjo.pdf) | **2020年11月・2022年3月の改訂を含む後年版。現行URL原本取得は未成功** | 公式検索索引の後年設備表に小松川第二中学校 No.2、夜間 No.3が別行で登場 | この表の各設備・番号が2019年当時も同一で、台風当日にも使われたこと |
| [小松川第二中学校の後年公式沿革](https://edogawa.schoolweb.ne.jp/1320032/page/frm4cd26abc60641) | 後年編集・現行ページの直接アクセス不安定 | 旧平井校舎に平井3丁目20番1号という過去所在地表記。2018年通常課程は移転 | 台風当日の夜間11人が旧平井校舎で避難したこと |

## 証拠レベルの区別

- **SCHOOL_CAMPUS_LOCATION**: 学校として授業を行った場所。2019表示の公式記録に2地区の別運営あり。
- **OPERATIONAL_REPORT_GROUP**: 事後の学校避難所報告にある番号（中学校2）。全65運用グループと66明細行の区別を保持。
- **SHELTER_FACILITY_INVENTORY**: 後年改訂の設備表には通常と夜間が別番号（2/3）。**2019年版の原本・版の確証がない**。
- **ACTUAL_EVENT_SHELTER_BUILDING**: 2019年10月12日に通常205人/夜間11人を収容した個別建物・住所。**未検証・null**。
- **PREDICTIVE_HISTORICAL_INPUT**: 2019当時公表済みと独立に認められた予報・施設情報。上述の事後資料を遡って混入しない。

この違いは出典行の見た目だけでは分からない。常に原本SHA・初回公表履歴・報告作成日と観測日・source roleを分離して管理する。2019年3月表示のHTMLそのものが2019に同一bytesで提供された証明もない。

## 独立監査の証跡（2026-10-27まで短期保管）

- 校舎資料: A/Cジョブ [#38350260260](https://github.com/1kz-ma1/HINANEX/actions/runs/38350260260)、SHA `542d615df1df07139c37eab45d65e0ea3e4ac87783e868471f79746702a673df`、C report artifact `11790661185`。
- 2018広報: [#38349472925](https://github.com/1kz-ma1/HINANEX/actions/runs/38349472925)、SHA `c44db027ac7d75444a5684e0a1c37973c6c6dc50fbe9974374c566713c219e33`、C report `11790695231`。
- 2020事後報告: [#38344307696](https://github.com/1kz-ma1/HINANEX/actions/runs/38344307696)、SHA `89fc7de1810685aaf48a5c6fd6f4c79d6888e1ffb3d6314756fa5665d652b380`、C report `11788715466`。
- 新しい横断検査では**三つの別実装Cレポートを再読込**して、3つの意味が混線していないことを確認する。C人間承認や歴史的な予測成績とは別。

## 次の受入条件

実際の校舎利用を確定するには2019-10-12の**避難所開設記録・建物別運用日誌・入所施設を識別する当日台帳**等が必要。未取得なら`UNKNOWN`のまま。

2017年制定/修正版の開設マニュアルが見つかれば「災害前の候補施設リスト」として利用可否を独立検証できるが、それだけでは**当日実際に205人と11人が避難した場所**は分からない。2022年設備表を2019年へ遡及使用しない。

関連: [Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142)、[Issue #134](https://github.com/1kz-ma1/HINANEX/issues/134)。スコープはAのEvidence記録のみ。DのRegionExportや災害安全判定の変更なし。
