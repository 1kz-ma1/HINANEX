# A Evidence Reverification — Flood Shelter Selection (2026-10-08)

- Role: A / Data Research / Evidence
- Scope: `flood_shelter_selection` 公式Source再確認とD/Cへの事実handoffのみ
- Existing A baseline: [A PR #37](https://github.com/1kz-ma1/HINANEX/pull/37)
- D provider: [D PR #41](https://github.com/1kz-ma1/HINANEX/pull/41) （`role/d-pipeline`統合済、`main`への統合は別判断）
- C validation: [C PR #42](https://github.com/1kz-ma1/HINANEX/pull/42) （raw照合は3地域PASS、意味論は別ゲート）
- **AはCandidate / Excluded / UNKNOWNやCapability・Gapの最終判定を行わない。**

## A-1 新潟市：現行データと条件付き階数の意味

### A-1a 公開データ（現行の2026年9月25日付カタログ）

- Official catalog: https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/
- Publisher: 新潟市
- Dataset: 自治体標準オープンデータセット「指定緊急避難場所一覧」
- Source format: CSV（市のページに171KBと記載）
- Dataset updated_at: **2026-09-25**（市のカタログに明記。初回公開日ではない）
- Catalog verification: **2026-10-08**
- Same-source join: `DIRECT_SAME_SOURCE` （現行D Adapterと同じCSV行を参照）
- Hazard source column: `災害種別_洪水`
- License: 既存A handoffの新潟市一般条件 `CC BY 2.1 JP` を変更しない。個別Source優先条項の再確認は必要時実施
- URLの更新・配布CSVのファイル内容はDワークフローが取得したraw archiveで管理し、Aは新しい施設属性を創作しない

### A-1b C独立raw照合で確認した現行CSVの値分布

2026-10-08にユーザーがC検証スクリプト `validation/validation/verify_flood_scenario_acceptance.py` を実行し、Dが保存した公式CSVの566行とRegionExportの行・施設名・raw値・Source URLの照合が **PASS**。以下は**ユーザー実行ログに由来するraw集計**であり、Aが独立に配布CSVを再ダウンロードして得たものではない。

| `災害種別_洪水` raw値 | CSV行数 |
| --- | ---: |
| `○` | 16 |
| `×` | 239 |
| `2階以上` | 173 |
| `3階以上` | 9 |
| `全階可` | 74 |
| `－` | 55 |
| **Total** | **566** |

C確認結果: `C raw trace acceptance: checks PASSED (official semantics remain separate review gate)`。

ここで確認できたのは**元値と現在の出力の一致**であり、`○`を無条件候補、`×`を洪水時利用不可と認定する根拠の確定ではない。

### A-1c 新潟市の2026年3月修正版・洪水ハザードマップに載る公式「表の見方」

- Official PDF source (city-controlled): https://www.city.niigata.lg.jp/kurashi/bosai/hinanjo/kouzui_hinanchizu/sougou_map/bosai_01souogu.files/07hayadoriR8.pdf
- Source: 新潟市総合ハザードマップ、北区の洪水・土砂災害「指定避難所・指定緊急避難場所一覧表」の表の見方、表紙に**令和8年3月修正版**と記載（正確な日付は未確認）
- Source type: PDF / official municipality; initial publication date not established
- Verification date: 2026-10-08

同PDFの**洪水**の凡例が示す意味:

| 表記（2026年版公式PDF） | 公式の説明（要旨） | Evidence上の区分 |
| --- | --- | --- |
| `全階可` | 浸水範囲外で、1階から全階へ避難可能 | 全階利用という条件付き公式事実 |
| `○階以上`（例 `2階以上` / `3階以上`） | ○階の下まで浸水する避難所であり、○階以上に避難可能 | 避難可能階数の下限という公式事実 |
| `－`（横線） | **当該河川洪水時**において開設しない | 河川別・場面限定の非開設（一般的な「対象外」とは異なる） |
| `利用不可` | 全階浸水または家屋倒壊等氾濫想定区域内などで利用不可 | 限定された公式利用不可理由 |
| `利用可` | 一時・広域避難場所が浸水範囲外で利用可 | 場所区分に依存する公式事実 |

同一PDFの**土砂災害**欄には `○`（土砂災害時に開設する避難所）、`×`（土砂災害警戒区域等にあり避難に適さない避難所）、`－`（警戒区域等の外、土砂災害時に開設しない避難所）が使われている。この説明を**洪水CSV列の`○`・`×`に流用してはならない**。

市はさらに「表の階数表記は、想定浸水深と建物の高さを比較したもの」「避難情報発令時に必ず開設する意味ではない」と明記。

**重要な適用制限:** このPDFは**河川ごと**の洪水凡例と避難施設一覧である。一方、今回のD/Cが扱うCSVは自治体標準ODSの **`災害種別_洪水`** 列である。両Sourceの値の対応表・利用目的・更新タイミングは公式に一対一と明示されていない。従って、このPDFは「階数表記は防災上有意味な公式事実である」の根拠にはなるが、CSVの全566行へPDFの判定をそのまま適用する根拠にはならない。

### A-1d Dへの正式Fact handoff（意味の保存のみ）

- `2階以上` 173件、`3階以上` 9件、`全階可` 74件、計**256件**には、階数に関するraw事実が明示されている。`UNKNOWN` というScenario最終ステータスをAが一方的に変更しないが、`UNKNOWN`が「出典に階数情報なし」を意味すると誤表現してはいけない。
- Dが`floor_restriction_raw`等の**Source固有の利用階条件**を明確に保持・表示できる設計を検討することを推奨する。AはCandidate認定も安全判定も行わない。
- `×` 239件、`○` 16件、`－` 55件の洪水CSV列での公的な意味を、最新CSV固有の仕様書・凡例と照合するまではAにとって **UNCONFIRMED_MAPPING**。`－`を無条件で「候補外」や「危険」へ変換しない。
- Cのraw-row監査がPASSしたことと、公式凡例の意味論がPASSしたことは別ゲートとして管理する。

## A-2 名古屋市：ページ・一覧の鮮度

- Official page: https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html
- Publisher: 名古屋市 防災危機管理局
- Page title: 指定緊急避難場所・指定避難所の指定
- **updated_at (official page): 2026-10-07**
- **source_reference_date (official list): 2026-09-01**（ページに「令和8年9月1日時点」と明記）
- Verification: 2026-10-08
- published_at: `null`（初回公開日を特定できない）
- Format: 16区の屋内施設ExcelおよびPDF、別途屋外施設Excel/PDF
- License: CC BY 4.0（ページのオープンデータ欄に明記）
- Existing D current scope: **16区屋内Excelのみ**。屋外データを勝手に追加しない
- Raw column: `洪水・内水` は結合列であり、洪水と内水を別々に判定しない
- Current C trace audit: ユーザー実行で16ファイル・1,602施設のraw行がPASS。ただしこれは**以前のA手渡し時点とのファイル差分を検証した証拠ではない**。更新日・基準日の差だけから増減や変更を断定しない

2026-10-06のA handoffに記載されていた `updated_at=2026-07-27` と `source_reference_date=2026-07-01` は公式現行ページと異なるため、2026-10-08の再検証値に改訂する。

## A-3 江戸川区：既存の制約継続

- Existing official flood/water-disaster page:
  https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html
- 施設単位の共通IDはAに未確認（`PARTIAL` joinability）。既存152位置施設へ公式HTMLの水害待避施設を曖昧名称で自動対応させない
- `水害` を自動的に「洪水単独の指定」と読み替えない
- Cは152件の`UNVERIFIED/UNKNOWN`整合を確認。ただし水害時待避施設HTMLの個別行との対応は未実施

## A-4 Outstanding / review gates

1. **C-FLOOD-01** (A→D): 今回の2026年版PDFでは`洪水`の階数表記が確認できたが、**CSV`災害種別_洪水`の○/×/－/階数表記の公式定義への完全な対応は未確認**。DはCSV固有凡例・表記の採用規則を明文化するまで `EXCLUDED/CANDIDATE`の意味を断定しないこと。
2. **D contract decision:** 256件の階数条件をraw factsとして保持し、条件付きで提示するデータモデルが必要かD/C/Bで協議。フロア条件を外して「安全」と表示することは不可。
3. **C-FLOOD-02:** 江戸川は安全なjoin不可。地名や住所の曖昧照合を自動確定しない。
4. **C-FLOOD-03:** 名古屋ページ・一覧基準日はこのA handoffで更新済み。ファイル内容変更有無の時点間比較は **NOT_VERIFIED**。
5. **A/C independence:** raw-value histogramはCのユーザーローカル検証ログに基づく。Aが本体CSVを再取得したと偽らない。
6. **Real-time:** 公式静的資料は個別施設の現時点の開設・道路安全性・洪水時安全性を保証しない。

## Source register

| ID | Authority | Title | Format | Date evidence | Reference |
| --- | --- | --- | --- | --- | --- |
| A-NIIGATA-ODS | 新潟市 | 新潟市オープンデータ「指定緊急避難場所一覧」 | CSV catalog | updated 2026-09-25 | https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/ |
| A-NIIGATA-FLOOD-LEGEND-R8 | 新潟市 | 新潟市総合ハザードマップ 洪水・土砂災害（北区・令和8年3月修正版） | PDF | revision 2026-03; exact day unknown | https://www.city.niigata.lg.jp/kurashi/bosai/hinanjo/kouzui_hinanchizu/sougou_map/bosai_01souogu.files/07hayadoriR8.pdf |
| A-NAGOYA-DESIGNATIONS | 名古屋市 | 指定緊急避難場所・指定避難所の指定 | HTML / 16 indoor XLS/PDF | page updated 2026-10-07; list as of 2026-09-01 | https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html |
| A-EDOGAWA-WATER | 江戸川区 | 水害ハザードマップ第2版 待避施設・自主避難施設 | HTML | existing A handoff (2026-10-06) | https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html |
