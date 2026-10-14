# A Evidence — 2019年10月12日以前の学校名簿候補（2026-10-13）

**Status: DISCOVERY ONLY / ALL UNAPPROVED / historical-as-of INPUT = 0.**

- 親: [Historical Replay #142](https://github.com/1kz-ma1/HINANEX/issues/142)
- 事後学校避難所の原本→抽出→C独立監査: [#156](https://github.com/1kz-ma1/HINANEX/pull/156)、[#159](https://github.com/1kz-ma1/HINANEX/pull/159)、[#160](https://github.com/1kz-ma1/HINANEX/pull/160)（**65 operational groups / 66 detail rows = 26,761 people、事後TRUTH**）
- 2019時点固定のC gate: [#148](https://github.com/1kz-ma1/HINANEX/pull/148)。
- machine-readable candidate ledger: [`2019-typhoon19-edogawa-school-roster-candidate-ledger.json`](2019-typhoon19-edogawa-school-roster-candidate-ledger.json)。

## Official sources and their important differences

| Source | 出版/カタログの根拠 | 日時精度 | 2019-10-12 09:00時点の INPUT |
| --- | --- | --- | --- |
| **東京都 平成29年度中学校一覧（所在地等）** | [東京都オープンデータ APIカタログ](https://spec.api.metro.tokyo.lg.jp/spec/t000021d1700000002-c0aa9217b65291115b9a588fc71b0c81-0?lang=en) : Created/Updated=2018-03-30、CC BY、元 CSV URL掲載 | **カタログ日**。現在元CSVのbyte同一性・当時公表履歴は未確認 | **候補**。2017→2019の閉校/移転/夜間学級/改称/住所変更を人手承認しない限り使わない |
| **東京都 平成30年度公立学校一覧** | [東京都立図書館2021年資料目録](https://www.library.metro.tokyo.lg.jp/search/research_guide/tokyo/monthly/202103/index.html) に2018年10月刊行と記載 | **月のみ**。原本・初回公開時刻未取得 | **候補**。2018年10月はイベント以前だが、当時版・正確な一覧が未確認 |
| **東京都 令和元年度公立学校一覧** | 同じ都立図書館の後年目録に**2019年10月刊行** | **月のみ**（10/01–10/31の幅） | **BLOCKED**。10/12より前なのか後なのか不明。10月1日と推定して入力に入れない |
| **江戸川区 学校適正配置の考え方 令和元年11月** | [江戸川区PDF](https://www.city.edogawa.tokyo.jp/documents/8888/r1gakkoutekiseihaitinokanngaekata.pdf) の発行年月 | 2019年11月、災害後 | **POST_EVENT_REFERENCE ONLY**。当時の学校構成を示していても10/12のINPUTにはならない |

**Important:** 「2019年度の学校調査の調査基準日=2019-05-01」と「実際のレポート公開日時」は異なる。令和元年度学校基本統計は調査自体が過去でも、報告書に後から集計・訂正が加わり得る。5月1日の値が2019年5月1日に公表済みと推測しない。東京都立図書館による2021年の事後目録も、現に2019年10月11日まで配信されたデジタル版の暗号学的証拠ではない。

## 2017 API catalog vs original source

カタログが提供する元 URL は **HTTP**:
`http://www.kyoiku.metro.tokyo.jp/administration/statistics_and_research/list_of_public_school/files/school_lists2017_csv/houkokushokouritsu02_03.csv`

現行のWeb環境ではHTTPS版への直接アクセスを確認できなかった。**HTTPであることから、アーカイブ取得で無断HTTPSへの置換やredirectを追従しない**。後続のA独立取得PRは公式データ提供サイトの確実なリンク・応答・SHAを新しく検証し、取得経路が失敗したら`ACCESS_PATH_UNVERIFIED`とする。カタログのCC BY表示は元CSVを現在取得・再配布できることの保証ではない。

## T0→T1 historical identity prerequisites

1. A: 2018年版の**元冊子 / official CSV / 施設名・住所・開校閉校の出典**を取得。2019年の災害前に配布された版の履歴を別証拠で同定。
2. C: 元データの版・発行時刻・学校名/所在地/夜間学級/旧校舎の独立監査。時点とsource revisionの真正性が立証できない場合 `asof=BLOCKED`。
3. **「学校」「夜間学級」「校舎」「避難所運用単位」を別概念として扱う**。#156の事後65 source groups/66 attendance rowsは、2017–19名簿との名前自動joinを許さない。旧平井二小学校、旧清新第二小学校、葛西小・中学校、夜間小松川第二中学校は人間が一対一・一対多関係をレビューする。
4. 学校一覧が示す「学校が存在/住所」は「当日の避難所開設」「洪水時安全性」「同名の物理施設」の証拠ではない。容量・地理座標を創作しない。
5. 人手承認された`as_of`版と`identity`が揃ったものだけ、DがT1比較対象へ接続できる。現時点の**正式なINPUT認可0件 / identity承認0件 / 予測MATCH/MISMATCH 0件**を維持。

## 10/22中間発表での使い方

- 2019年10月発行の名簿は**「その月だから過去に存在したはず」では使わない**という判定保留を説明可能。
- 2018年の名簿は災害より前でも**「古い住所・学校変更」がありうるので施設単位の確定joinは行わない**ことを示す。
- 2019年11月の計画図は学校名が描かれていても**事後参考に隔離**。
- このgateが`BLOCKED`となることは信頼性チェックの成果。施設の実被害予測や開設数一致の「成功」と呼ばない。

**A ownership:** `data-research/**` only。実データの原本解釈で不確実な点はnull/UNKNOWNのまま残し、C/D/Shared Contractを書き換えない。
