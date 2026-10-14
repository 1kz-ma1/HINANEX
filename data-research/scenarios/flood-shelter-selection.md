# Flood Shelter Selection — A Evidence / Scenario Requirement

- Role: A / Data Research / Evidence
- Original review date: 2026-10-06
- Latest A evidence re-verification: **2026-10-08** — details: [2026-10-08-flood-source-reverification.md](2026-10-08-flood-source-reverification.md)
- Scenario ID: `flood_shelter_selection`
- Scenario Name: Flood Shelter Selection / 洪水時の避難候補探索
- Status: A's original proposal is retained; D adopted `shelter_hazard_applicability` as a **Scenario-local** requirement in PR #41 (merged to `role/d-pipeline`, not yet `main`). Shared/legacy Contract adoption is a separate decision.
- Existing formal requirement: `shelter_location`
- Current RegionExport schema: 0.9

## 1. Purpose

現在HINANEXが取得できる公式情報から、洪水という条件を考慮して避難候補を絞り込むための情報が揃っているかを、Dが後から機械評価できる状態にする。

このScenarioは「安全な避難所を決定する」ものではない。

Aが渡すのは次の事実だけとする。

- 公式Source上で施設が何として掲載されているか
- 洪水または水害に関してどの公式項目があるか
- 公式項目の生値・意味
- 現行 `shelter_location` recordとどう追跡できるか
- 何が未確認・結合不能・意味未確定か

最終的な `CANDIDATE / EXCLUDED / UNKNOWN` 等のScenario判定はDの責務。

## 2. In Scope

- hazard: flood
- 既存 `shelter_location` の施設位置
- 施設単位の公式な災害別指定・利用可否・利用階情報
- Source間 / record間のjoinability
- raw value / null / unknown の保持
- 将来multi-hazardへ拡張可能なEvidence設計

## 3. Out of Scope

- 「この施設は安全」というA独自判定
- 洪水浸水深ポリゴンと施設点の独自交差による安全判定
- 住所からのgeocoding
- リアルタイム開設状況
- 道路・避難ルート安全性
- 収容人数、アクセシビリティ
- 洪水Evidenceから他災害の安全性を推測すること
- Capability / Gap / Recommendationの算出

## 4. Required facts

最低限、Scenario評価には次の2系統の事実が必要。

1. **既存 `shelter_location`**
   - facility name
   - machine-usable location
2. **施設単位の災害別公式情報**
   - facility reference
   - hazard / hazard scope
   - official status raw value
   - official meaning / source semantics
   - join key / join method

Aは2をtrue/falseへ単純化しない。

## 5. Proposed Requirement

### Proposed code

`shelter_hazard_applicability`

これは **提案名**。現行D-MVPの正式DataRequirement codeではない。

### Meaning

> 避難施設について、特定の災害に対する指定・利用可否・利用条件として公式Sourceが示している事実を、そのSource固有の意味を失わず保持する。

### Proposed fields

Required candidate fields:

- `facility_reference`
- `hazard_code_raw` または source-defined hazard scope
- `source_semantics`
- `official_status_raw`
- `source_url`

Optional candidate fields:

- `official_facility_id`
- `facility_name`
- `address`
- `usable_floor_raw`
- `notes`

### Why not a simple flood boolean

3地域の公式Sourceは同じ意味ではない。

- 新潟市: 「指定緊急避難場所一覧」の `災害種別_洪水`
- 名古屋市: 「指定緊急避難場所」の `洪水・内水` 列。○ / × / － / 階数表現
- 江戸川区: 水害ハザードマップの「待避施設」と「使用可能階数」

よって、A側で `flood_supported=true/false` へ統合すると公式意味を失う。

## 6. Region evidence

### 6.1 東京都江戸川区 / 13123

**Source**

- 江戸川区水害ハザードマップ第2版
- 「地域防災拠点に避難、待避施設（小中学校等）・自主避難施設へ避難」
- https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html

**Official meaning**

公式ページでは「待避施設」を、避難する時間がない・避難が困難など、やむを得ない場合に緊急避難する施設と説明している。
小中学校・高等学校等の施設ごとに「使用可能階数」を掲載する。
一部施設には「大規模水害では使用不可」という明示もある。

これは新潟・名古屋の「災害種別ごとの指定緊急避難場所」列と同じ意味とは断定しない。

**Available fields**

- 番号
- 名称
- 住所
- 電話番号
- 使用可能階数

**Hazard scope**

Sourceは「水害」文脈。A側で洪水だけの公式指定へ読み替えない。

**Joinability**

`PARTIAL`

現行D Edogawa `shelter_location` は同区の避難所CSVを使用するが、共通IDは確認できない。
候補joinは正規化施設名。
Source側には住所があるため追加検証には使えるが、現行D normalized shelter_location recordでは住所を保持していないため、現状は安全な完全自動joinキーではない。

名称差、旧校名、複合校名等は曖昧判定として残す。

**Machine readability**

HTML tableとして抽出可能。ただし自治体標準ODSのような共通構造ではない。

**Evidence status**

`PARTIAL`

理由:
- 水害時の公式施設利用情報は存在する。
- 現行 shelter_location recordとの共通IDがない。
- 「水害」を「洪水のみ」とA側で同義化できない。

**Publisher**

江戸川区

**updated_at**

ページ更新日: 2025-12-19

**published_at**

`null`

水害ハザードマップ第2版が2025年7月公表であることは公式ページ上で確認できるが、日単位の初回公開日はA側で補完しない。

**license**

`null`

この水害ハザードマップページについて、今回の確認範囲で個別オープンデータライセンスを確定していない。

---

### 6.2 新潟県新潟市 / 15100

**Source**

- 新潟市オープンデータ
- 自治体標準オープンデータセット「指定緊急避難場所一覧」
- https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/

補助的な標準定義:
- デジタル庁 自治体標準オープンデータセット
- https://www.digital.go.jp/resources/open_data/municipal-standard-data-set-test

**Official meaning**

新潟市は「指定緊急避難場所一覧」を自治体標準ODSとして公開。
自治体標準ODSの指定緊急避難場所定義には、施設が対応する災害を示す `災害種別_洪水` が定義されている。

**Available / expected standard fields relevant to this Scenario**

- ID
- 名称
- 緯度
- 経度
- `災害種別_洪水`
- その他の災害種別列

現行D Adapterも同Sourceを取得し、明示された災害種別列だけを扱っている。

**Joinability**

`DIRECT_SAME_SOURCE`

現在の `shelter_location` と災害種別情報は同じ公式CSV行から取得可能。
公式IDが存在する行ではIDを第一候補。
同一Adapter取得時は同一raw rowからlocationとhazard evidenceを生成できるため、名称fuzzy joinを主方式にする必要はない。

**Machine readability**

CSV / machine-readable.

**Evidence status**

`AVAILABLE`

2026-10-08にC側の独立監査をユーザーが実行し、公式raw CSVの566行の値とD RegionExportの一致を確認した（A独立ダウンロードではない）。生値は `○`16、`×`239、`2階以上`173、`3階以上`9、`全階可`74、`－`55。**これはraw行の一致であり、災害別の公式記号意味の認定とは異なる。**
2026年3月修正版・新潟市の洪水ハザードマップは全階可／○階以上／当該河川洪水時の `－` 非開設の意味を明示するが、**河川別ハザードマップの凡例とODS CSV `災害種別_洪水` の対応は未確認**。詳細は2026-10-08 Evidence追補を参照。

**Publisher**

新潟市

**updated_at**

2026-09-25

**published_at**

`null`

**license**

CC BY 2.1 JP（個別定めがない場合の新潟市オープンデータ一般条件）

---

### 6.3 愛知県名古屋市 / 23100

**Source**

- 指定緊急避難場所・指定避難所の指定
- https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html

**Official meaning**

指定緊急避難場所は「命を守るため、災害の危険からまず逃げるための場所」であり、災害の種類ごとに異なる。
屋内施設一覧では施設行に、指定緊急避難場所としての

- 洪水・内水
- 高潮
- 土砂
- 津波

と、別列の「指定避難所」を掲載する。

現在の公式PDFで記号の意味は:

- `○`: 避難可能
- `×`: 避難不可
- `－`: 災害の危険性がない
- 数字 / 丸数字: 避難可能階数（例: ② = 2階以上避難可）

**Important hazard semantic**

Source列は「洪水・内水」の結合列。
A側でこれを `flood` と `inland_flood` の2つの独立判定に分解しない。
raw hazard scopeを `flood_inland_combined` として保持するのが安全。

**Available fields**

- 学区
- 番号
- 施設名称
- 所在地
- 指定緊急避難場所 洪水・内水
- 高潮
- 土砂
- 津波
- 指定避難所

**Joinability**

`DIRECT_SAME_SOURCE` for current indoor scope.

現行D `shelter_location` は公式ページの16区別屋内Excelを直接正規化している。
新Requirementも同一raw rowから抽出すれば、`ward + source number + facility name + address` を追跡可能であり、別Sourceのfuzzy joinは不要。

ただし現行D Datasetは屋内16ファイルのみ。
公式ページ上の屋外施設Excelは現行 `shelter_location` Datasetへ含まれていないため、Scenario対象範囲を勝手に「名古屋市の全避難施設」へ拡張しない。

**Machine readability**

Excel / machine-readable.

**Evidence status**

`AVAILABLE` for the official hazard column itself.
Current Scenario joinability is strong for the 16 indoor files already used by D.

**Publisher**

名古屋市

**updated_at**

2026-10-07（2026-10-08に公式ページ再確認）

**list reference date**

2026-09-01時点（名古屋市公式の『令和8年9月1日時点』）

**published_at**

`null`

**license**

CC BY 4.0

## 7. Proposed normalization handoff to D

A does not require D to adopt this exact shared Schema. The following is an implementation handoff proposal.

```json
{
  "region_code": "23100",
  "facility_reference": {
    "official_facility_id": null,
    "facility_name": "千種小学校",
    "address": "千種3-2-5"
  },
  "hazard_code_raw": "flood_inland_combined",
  "source_semantics": "designated_emergency_evacuation_site_hazard_column",
  "official_status_raw": "○",
  "usable_floor_raw": null,
  "source_url": "https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html"
}
```

### Required preservation rules

- `official_status_raw` を必ず保持する。
- `○ / × / － / 階数`をA側で安全/危険booleanへ変換しない。
- 江戸川の「使用可能階数」を名古屋の「洪水・内水」指定と同義にしない。
- 名古屋の「洪水・内水」を洪水と内水の独立2値へ分割しない。
- 新潟の `災害種別_洪水` 以外の列から洪水可否を補完しない。
- join不能は `UNKNOWN` 相当の未確定事実としてDへ渡し、施設を推測対応させない。

## 8. Region differences for D

| Region | Flood-related official fact | Join to current shelter_location | Key limitation |
| --- | --- | --- | --- |
| Edogawa | 水害時の待避施設 / 使用可能階数 | PARTIAL | 共通IDなし。水害文脈を洪水指定へ同義化できない |
| Niigata | `災害種別_洪水` in standard ODS | DIRECT_SAME_SOURCE | raw marker semanticsを保持 |
| Nagoya | `洪水・内水` designated-emergency-site column | DIRECT_SAME_SOURCE for 16 indoor files | floodとinland floodの結合列。屋外施設は現行D scope外 |

## 9. Unknown / unresolved before D finalizes evaluation rules

1. **Requirement code has been adopted for the D Scenario-local model**
   - `shelter_hazard_applicability` originated as A proposal; D PR #41 adopted it in `role/d-pipeline`.
   - This is not proof that the legacy `DatasetAssessment → Capability → Gap` or `main` has adopted the same formal code; shared consumer integration must be decided separately.

2. **Edogawa semantic mapping**
   - 「水害時の待避施設 / 使用可能階数」を、Flood Shelter Selectionの必須Requirementとしてどのように評価するかはD/C側のルール決定が必要。
   - Aは「洪水対応指定」とは断定しない。

3. **Edogawa join**
   - 共通IDなし。
   - 名称joinの曖昧レコードを自動確定しない。
   - addressをD normalized recordへ追加する変更が必要ならD担当領域で行う。

4. **Nagoya combined hazard column**
   - `洪水・内水`をFlood Scenarioでどのように扱うかはDの明示ルールが必要。
   - Aは洪水単独の値へ分解しない。

5. **Nagoya outdoor facilities**
   - 公式ページには屋外施設もあるが現行D shelter_location scope外。
   - Scenarioの正式対象に含めるかはD/Product判断。

6. **Real-time state**
   - 3地域とも静的公式Evidenceからリアルタイム開設を推測しない。

## 10. Future extension

将来はConceptとして次のように拡張可能。

```text
Scenario
├─ scenario_id
├─ hazards[]
├─ requirements[]
└─ required_evidence[]
```

`shelter_hazard_applicability` を採用する場合も、hazard-specific raw factsを保持することで flood / landslide / tsunami / storm_surge 等へ拡張しやすい。

ただしAは今回、新しいshared Schema・RegionExport構造・Capabilityを実装しない。

## 11. 2026-10-08 A Evidence follow-up

今回の公式情報再確認の詳細は [2026-10-08-flood-source-reverification.md](2026-10-08-flood-source-reverification.md) を参照。

- 新潟：現行ODSカタログ更新日は2026-09-25。C監査により raw値6種類・計566行の対応を確認（Cユーザーローカル実行結果）。公式洪水ハザードマップの「利用階・開設」の凡例とODS列の正式対応が未確認であることを明記。
- 名古屋：公式HTML更新日2026-10-07、一覧基準日2026-09-01。16区屋内が現行D scope、屋外は別データ。旧版と最新Excelの差分は推測しない。
- 江戸川：既存 PARTIAL join、施設単位Source行未照合という制約は変更せず。
- Aが算定するのはEvidenceであり、CANDIDATE/EXCLUDED/UNKNOWN、Capability、Gapの判定規則はD/C側の責務。

## 12. 2026-10-10 判定可能な施設を増やすための根拠ゲート

[2026-10-10公式根拠・施設照合ゲート](2026-10-10-flood-classification-unblock-plan.md) を参照。江戸川は水害時待避施設HTMLとD位置CSVの共通ID・住所未照合、新潟は同一行traceがあるがODS `災害種別_洪水` 列のraw記号を公式に解釈できない。現時点でA/D/Cの正式に承認済みの施設単位分類増加はゼロ。AのEvidence収集と、D評価・C独立受入を混同しない。
