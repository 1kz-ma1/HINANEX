# A Evidence — Niigata ODS flood marker crosswalk (2026-10-09)

- Role: A / Data Research / Evidence
- Issue: [#48 Clarify Niigata ODS flood marker semantics before Scenario release](https://github.com/1kz-ma1/HINANEX/issues/48)
- Scope: 新潟市公式ODS CSV `災害種別_洪水` の raw marker と、新潟市公式資料にある洪水時の表記説明との対応確認
- Fetched / verified: **2026-10-09**
- Safety boundary: Aは `CANDIDATE` / `EXCLUDED` を決定しない。ODS列との対応が直接確認できない値はDへ `UNKNOWN` 維持をhandoffする。

## 結論

新潟市公式資料には、洪水時の `○`、`×`、`－`、階層表記を説明する「災害種別毎の指定有無」凡例と、河川別の `全階可`、`○階以上`、`－` 凡例が存在する。

一方、確認した公式資料には、**現在配布中の自治体標準ODS CSVの `災害種別_洪水` 列が、これらの凡例をどの版・どの集約規則で採用しているかを明記したcolumn-specific dictionaryがない**。特に、河川別の複数状態がODSの単一セルへどう集約されるかは確認できない。

したがって、各markerは「新潟市の関連する公式洪水資料での意味」は部分的に確認できるが、「現行ODS列の値からHINANEX Scenario statusを確定できる」という意味では未確認である。Dは全markerを `UNKNOWN` のまま保持する。

## Source register

| ID | Publisher | Source title | URL | Publication / update | Fetched | Relevant part |
| --- | --- | --- | --- | --- | --- | --- |
| NIIGATA-ODS-CATALOG | 新潟市 | オープンデータ「指定緊急避難場所一覧」 | https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/ | catalog updated **2026-09-25** | 2026-10-09 | CSV配布元、防災課、更新日 |
| NIIGATA-ODS-CSV | 新潟市 | 自治体標準オープンデータセット「指定緊急避難場所一覧」CSV | https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/index.files/151009_evacuation_space.csv | catalog updated **2026-09-25** | 2026-10-09 | `災害種別_洪水` 列とraw marker |
| NIIGATA-DESIGNATION-LEGEND | 新潟市 | 表2-1-17-1 指定避難所・指定緊急避難場所一覧（江南区） | https://www.city.niigata.lg.jp/kurashi/bosai/hinanjo/ku_hinanarea/kounanku.files/r4syubetu_konan.pdf | PDF内に発行・更新日の明記を確認できず | 2026-10-09 | p.1「2. 災害種別毎の指定有無」「(2) 洪水時」 |
| NIIGATA-R8-PLAN | 新潟市防災会議 / 新潟市 | 新潟市地域防災計画 資料編・表2-1-17-1 指定避難所・指定緊急避難場所一覧 | https://www.city.niigata.lg.jp/shisei/seisaku/seisaku/keikaku/kikikanri/chiikibosai/index.html | **2026-03修正** | 2026-10-09 | 洪水の「指定有無」欄に同種のmarkerを掲載。ODSとの対応説明はない |
| NIIGATA-R8-FLOOD-LEGEND | 新潟市 | 新潟市総合ハザードマップ 北区・早通中学校区 | https://www.city.niigata.lg.jp/kurashi/bosai/hinanjo/kouzui_hinanchizu/sougou_map/bosai_01souogu.files/07hayadoriR8.pdf | **2026-03修正版** | 2026-10-09 | 河川別洪水表の `全階可`、`○階以上`、`－` と注意書き |
| DIGITAL-AGENCY-ODS | デジタル庁 | 自治体標準オープンデータセット（正式版） | https://www.digital.go.jp/resources/open_data/municipal-standard-data-set-test | page updated **2026-08-10**; definition **2026-08-01** | 2026-10-09 | 定義書Aの `災害種別_洪水` と controlled vocabulary |

## 現行ODS raw確認

2026-10-09に `NIIGATA-ODS-CSV` を直接取得し、UTF-8 CSVの `災害種別_洪水` 列を文字列のまま集計した。結果は566行で、`○=16`、`×=239`、`2階以上=173`、`3階以上=9`、`全階可=74`、`－=55`。これは取得日の監査snapshotであり、恒久的な件数・fixture・判定条件ではない。

列には公式値が存在するが、CSV本体にはmarker dictionaryや集約規則は付属していない。

## 公式説明の確認

### 新潟市「災害種別毎の指定有無」凡例

`NIIGATA-DESIGNATION-LEGEND` は、指定緊急避難場所の洪水欄を次のように説明する。

- `○`: 避難場所周辺のすべての河川について洪水時に使用できる場所。
- `階層`: 指定有。表に列挙されたすべての河川について、想定浸水深より高い階層に避難スペースがあり、周辺での洪水時に使用できる施設・場所。
- `×`: 指定無。列挙された一部河川で避難スペース全階が浸水するおそれがあり、当該河川洪水時に使用できない施設・場所。河川ごとの使用可否は別表参照。
- `－`: 指定無。列挙されたすべての河川について浸水想定区域から離れ、洪水時に使用を予定しない施設・場所。

これは「洪水時に安全である」「避難情報発令時に必ず開設する」「現在開設中である」と同義ではない。また、このPDF自体は現行ODS CSVとの同一仕様・生成元・集約規則を宣言していない。

### 新潟市・河川別洪水凡例

`NIIGATA-R8-FLOOD-LEGEND` は、河川別の表について次を説明する。

- `全階可`: 浸水範囲外で、1階からすべての階へ避難可能。
- `○階以上`: ○階の下まで浸水する避難所であり、○階以上へ避難可能。
- `－`: **当該河川洪水時**に開設しない。
- 階数表記は、想定浸水深と指定避難所の建物階数の高さを比較したもの。
- 避難情報が発令された時に必ず開設することを示すものではない。

同PDFの `○` / `×` / `－` の別凡例は土砂災害用であり、洪水ODS列へ転用しない。

### デジタル庁・全国標準定義

2026-08-01版の定義書Aでは `災害種別_洪水` はcontrolled vocabularyで、特記事項は `1` を「対応済み」、空欄を「未対応」とする。新潟市CSVにある6種類の独自値は、この全国標準定義だけでは説明できない。全国標準の `1` / 空欄を、新潟市の `○` / `×` / `－` / 階層へ推測変換しない。

## Crosswalk

ここでの「確認状態」は、**新潟市公式の関連資料に説明があるか**と、**現行ODS列への直接対応が確認できたか**を合わせた状態である。全行とも後者が未確認のため `PARTIALLY CONFIRMED` であり、HINANEX status候補はfail-closedの `UNKNOWN` とする。

| Raw marker | 公式説明（関連する市資料） | Source | 確認状態 | ODS列への直接対応 | HINANEX status候補 |
| --- | --- | --- | --- | --- | --- |
| `○` | 周辺のすべての列挙河川について洪水時に使用できる場所 | NIIGATA-DESIGNATION-LEGEND | PARTIALLY CONFIRMED | **UNCONFIRMED** | `UNKNOWN` |
| `×` | 指定無。一部河川で全階浸水のおそれがあり、当該河川洪水時に使用できない | NIIGATA-DESIGNATION-LEGEND | PARTIALLY CONFIRMED | **UNCONFIRMED** | `UNKNOWN` |
| `－` | 単一の指定有無表では、全列挙河川の浸水想定区域外で洪水時に使用予定なし。河川別表では当該河川洪水時に開設しない | NIIGATA-DESIGNATION-LEGEND / NIIGATA-R8-FLOOD-LEGEND | PARTIALLY CONFIRMED | **UNCONFIRMED**。表の粒度により説明が異なる | `UNKNOWN` |
| `2階以上` | `階層`の一種。想定浸水深より高い階層の避難スペースという条件。河川別表では2階以上へ避難可能 | NIIGATA-DESIGNATION-LEGEND / NIIGATA-R8-FLOOD-LEGEND | PARTIALLY CONFIRMED | **UNCONFIRMED** | `UNKNOWN`; rawは `usable_floor_raw` に保持 |
| `3階以上` | `階層`の一種。想定浸水深より高い階層の避難スペースという条件。河川別表では3階以上へ避難可能 | NIIGATA-DESIGNATION-LEGEND / NIIGATA-R8-FLOOD-LEGEND | PARTIALLY CONFIRMED | **UNCONFIRMED** | `UNKNOWN`; rawは `usable_floor_raw` に保持 |
| `全階可` | 河川別表では浸水範囲外で1階から全階へ避難可能 | NIIGATA-R8-FLOOD-LEGEND | PARTIALLY CONFIRMED | **UNCONFIRMED** | `UNKNOWN`; rawは `usable_floor_raw` に保持 |

## 解釈してはいけない境界

- 指定避難所と指定緊急避難場所を同一視しない。
- 指定有を安全保証、開設保証、現在開設中へ変換しない。
- `×` を施設一般の危険・利用不可へ拡張しない。公式説明は河川条件を含む。
- `－` を一律に対象外・危険・利用不可へ変換しない。単一指定表と河川別表で粒度が異なる。
- 階数値を無条件の `CANDIDATE` へ変換しない。河川条件、指定、利用階、開設は別概念である。
- ODS単一セルから、どの河川条件が採用・集約されたかを推測しない。

## D / C / B / E handoff

- **D**: 現行の全Niigata `FacilityScenarioStatus.UNKNOWN` を維持する。`official_status_raw` と、階数値の `usable_floor_raw` を保持する。新しいenumやmarker mappingは追加しない。
- **C**: raw row、ID、Source URL、trace、階数rawと、全markerが `UNKNOWN` であることを独立確認する。公式凡例が存在することとODS mapping acceptanceを分離する。
- **B**: D Scenario Resultのみを表示し、raw markerを再評価しない。`discovery_status=AVAILABLE` はraw取得済みであり、判定可能を意味しない。
- **E**: Dのfacility statusと公式rawのみを表示し、marker、座標、洪水ラスタから独自判定しない。

## Issue #48 disposition

**STILL OPEN.** 新潟市公式の関連洪水凡例は確認できたが、現行ODS `災害種別_洪水` 列と6 markerの版・集約・意味を直接結ぶcolumn-specific dictionaryは確認できない。Issueをcloseするには、新潟市防災課または公式ODS metadataでこの対応が直接確認できる必要がある。
