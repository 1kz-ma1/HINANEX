# A→D 3地域 shelter_location Validation

- review date: 2026-09-29
- reviewer role: C / Validation
- repository: `1kz-ma1/HINANEX`
- validation base: `role/d-pipeline` commit `a5a8ab0bc535aff611a8fb6eb6c7ec74d018f6e7`
- formal DataRequirement: `shelter_location`
- Capability: `shelter_discovery`
- overall judgment: **valid with review items**
- classifications: `valid` / `needs_review` / `misclassified`

## 2026-10-06 C targeted follow-up（D PR #23確認後）

C PR #17でDへ返却した `Evidence.published_at` の1点だけを再確認した。
3地域の全Validationを最初からやり直すのではなく、返却事項に対するD修正と
回帰テストを対象にした差分Validationである。

- D修正: PR #23 `fix(d): keep update dates out of Evidence.published_at`
- 確認対象: `role/d-pipeline` commit `8595f39f372e3b5b50857fd0f453130919d3ace2`
- CI: PR #23 GitHub Actions `test` run #52 = **success**
- Contract変更: none
- Schema変更: none
- Cは `pipeline/**` を変更していない

### Return itemの解消確認

| 対象 | PR #17時点の問題 | PR #23後の確認 | C判定 |
| --- | --- | --- | --- |
| 新潟市 | 一覧に紐づく日付を `Evidence.published_at` へ設定していた | `published_at=None`。確認した日付はnotesへ「一覧に紐づく日付」として保持し、公開日・初回公開日とは確認できないため `published_at` に使用しない旨を明記 | **resolved** |
| 名古屋市 | 公式ページの「更新日」を `Evidence.published_at` へ設定していた | `published_at=None`。ページ更新日はnotesへ意味付きで保持し、初回公開日とは確認できないため `published_at` に使用しない旨を明記 | **resolved** |

新潟・名古屋とも、既存Contract:

```text
Evidence.published_at
= 公式Sourceで公開日として確認できる場合のみ設定
```

へ実装が揃ったことを確認した。更新日等は捨てずにnotesへ残るため、
Traceabilityも維持されている。

### Regression evidence

PR #23では以下の回帰テストが追加・更新されている。

- Niigata: 日付を取得できても `published_at is None` であること
- Niigata: 取得した日付がnotesへ残ること
- Nagoya: ページ更新日を取得できても `published_at is None` であること
- Nagoya: 更新日がnotesへ残ること
- Scope Guard / Python compile / unit & regression / JSON Schema sync /
  PowerShell parse を含むCI run #52がsuccess

### C conclusion

**PR #17で追加した `published_at` のreturn itemは解消済み。**

この修正はEvidence metadataの意味論のみで、
record count、DatasetAssessment、Capability、Gap、Recommendationの
判定ロジックを変更していない。したがって、この1点の確認のために
江戸川152件・新潟566件・名古屋1602件の全raw再取得を再実施する必要はない。

今回の差分Validationで新しい `misclassified` は確認していない。

引き続き別論点として残るもの:

- 新潟566件の独立raw hash / 全件再照合
- 名古屋1602件の独立raw再カウント
- 実地位置精度
- 名古屋屋外施設をformal Datasetへ含めるかのProduct/Contract判断
- 災害別安全性・capacity・accessibility等

これらはPR #23の受入を止める理由ではなく、今回の
`published_at` return itemとは分離して扱う。

---

## 2026-10-06 C follow-up（最新main同期後）

この節は、以下の2026-09-29時点の検証記録に対する**追補**である。旧節の
`needs_review` と「現在」の記述は当時の状態を示し、現在の修正状況は本節を優先する。

- 確認基準: `main` commit `79bae2713123a45ca54fc9018cbe2046600bc61d`
  （A日付修正 PR #19、DのC指摘対応 PR #20、D main統合 PR #22を含む）。
- PR #17のbase `role/c-validation` をこのmainへfast-forwardし、
  feature branchも最新baseへ追従させた。
- 対象は引き続き `shelter_location -> shelter_discovery`。CはA/Dの
  production code、共有Contract、Schemaを変更しない。

### 前回の返却事項の再確認

| C指摘 | 2026-10-06の確認結果 | 判定 |
| --- | --- | --- |
| 江戸川の更新日を初回公開日に見せない | `EdogawaShelterAdapter.normalize()` は `Evidence.published_at=None` とし、公式ページの2025-12-11が更新日である旨をnotesに記録。 | 対応確認 |
| 名古屋A handoffの更新日 | 現在の公式ページはページ更新日2026-09-15、一覧表は2026-09-01時点。Aの同一Sourceの関連Evidence 3件はすべて `updated_at=2026-09-15`、notesに一覧基準日とページ更新日を区別して記録。旧節の2026-07-27 / 2026-07-01は9月29日の初回C調査で見た旧表示であり、現在値として扱わない。 | 対応確認 |
| 名古屋Dの1602件の範囲 | `NagoyaShelterAdapter.DATASET_SCOPE_NOTE` と各Evidence.notes、`pipeline/docs/HANDOFF_E.md` は16区別屋内施設Excelのみを対象とし、屋外施設を含まないことを明記。公式ページにも屋外Excelが別に掲載される。 | 表現上の対応確認 |
| FULLとGap 0の意味 | `capability.py` のREADY理由とD handoffは、名称・緯度経度による位置ベース探索にFULLを限定。災害別安全性などを保証しない。Gap 0も現在のcapability条件内の意味。 | 対応確認 |
| 名古屋Recommendation | `gap.py` は現在取得しているSourceで確認した不足と、別の公式Source/公式補完方法の調査に限定。自治体が座標を一切公開していないとは断定しない。 | 対応確認 |
| 新潟の施設種別 | 現行Adapterの`designated_emergency_evacuation_site`は維持。566件すべてを「指定避難所」として扱わない。 | 対応確認 |

公式ページ: https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html
（2026-10-06 C再確認）。Aの修正はPR #19、Dの修正はPR #20、
main統合はPR #22で追跡可能。

### 判定値と未解決項目

D PR #20の実データ回帰記録では、修正後も次の結果を報告している。
Cは今回、最新mainの変更箇所・回帰テストを照合したが、
**2026-10-06に三地域のrawファイルを独立再取得して件数を再計算していない**。
以下の件数はDの当該実行記録に基づく。

| 地域 | Dの実データ回帰記録 | Cの評価 |
| --- | --- | --- |
| 江戸川区 | 152件、4/4/4/4、FULL、Gap 0、Recommendation 0 | 以前のCによる同一CSV全件照合と整合。Evidence日付の表現は修正済み。 |
| 新潟市 | 566件、4/4/4/4、FULL、Gap 0、Recommendation 0 | 現行の位置ベース条件とは整合。566件の独立raw再カウントは未実施。 |
| 名古屋市 | 屋内16ファイル1602件、Completeness 0 / Validity null / Machine Readability 4 / Geospatial Usability 0、BLOCKED、Gap 1、Recommendation 1 | 0とnullの区別およびBLOCKEDは現行Contractと整合。1602件の独立raw再カウントは未実施。 |

**新規 needs_review（Dへの返却事項）:** 江戸川は`published_at=None`に修正されたが、
新潟Adapterは一覧に紐づく日付を抽出して`Evidence.published_at`へ代入し、
名古屋Adapterは公式ページの`更新日`を抽出して同フィールドへ代入している。
少なくとも後者は初回公開日と確認できない。前者もその日付が初回公開日か
確認できていない。Dは`published_at`の契約意味を確認し、更新日なら
初回公開日として記録しない扱いを検討すること。Cは値を推測補完しない。
本指摘は現行の4/4/4/4・BLOCKEDなどの判定変更を要求しない。

引き続き未確認: 新潟CSVの独立hash/566行照合、名古屋16 Excelの独立
hash/1602行照合、実地位置精度、屋外施設のformal datasetへの採否、
災害別安全性。PR #8は江戸川の過去の独立照合として参照し、
PR #17がC branchに受け入れられた後の扱いを人間が決める。

### Test evidence

- Passed: A handoff JSONを再取得・parseし、名古屋同一Sourceの3件の
  `updated_at` / notesを照合。DのEdogawa/Nagoya Adapter、Capability、
  Gap、E handoffと公式名古屋ページを再確認。
- Failed: 上記read-onlyのC照合ではなし。
- Not run: 2026-10-06のC環境からの三地域live workflow、
  Niigata/Nagoyaの独立raw hash・行数照合。
- Reason: GitHub上のソースとA/Dの回帰記録を確認する追補であり、現在の
  C実行環境には最新mainの実データraw一式を配置していない。CI結果は
  この追補をpushした後にPR本文へ別途記載する。

---

## 1. Scope and validation principle

This review validates the trace:

```text
A Evidence
  -> D Adapter / NormalizedDataset
  -> DatasetAssessment
  -> CapabilityAssessment
  -> Gap
  -> Recommendation
  -> RegionExport
```

The review is intentionally limited to the currently formal D-MVP vertical slice:

```text
shelter_location -> shelter_discovery
```

Flood hazard, inundation depth, shelter accessibility, shelter capacity, and
shelter disaster compatibility are not promoted to formal DataRequirements by
this validation.

`FULL` in this review means that the current `shelter_location` dependency
has sufficient name + machine-usable location data for the current
position-based Shelter Discovery rule. It does **not** mean that HINANEX has
validated disaster suitability, safety, capacity, accessibility, legal
designation completeness, or route safety.

Likewise, `Gap = 0` means that no gap is produced by the current
`shelter_location -> shelter_discovery` rule. It does not mean that the
municipality has no other disaster-data gaps.

## 2. Repository / dependency state used for validation

At review start:

- latest `main`: `fb36b14a4afdd2f2551723cb242acd72580eea54`
  - includes A handoff through the A role integration.
- A handoff:
  - `data-research/handoff/HINANEX_A_final_handoff.json`
  - PR #11 merged, then A role branch merged to main by PR #15.
- D A-D Integration Check:
  - PR #16 merged to `role/d-pipeline`
  - `role/d-pipeline`: `a5a8ab0bc535aff611a8fb6eb6c7ec74d018f6e7`
- previous C branch was stale:
  - `role/c-validation` was 45 commits behind main and 51 commits behind the
    D validation base.
  - It was fast-forwarded to the D integration commit before this review
    branch was created.
- previous PR #8 is a one-region Edogawa initial review based on an older
  baseline. It is useful historical evidence but is superseded in scope by
  this three-region review.

No `pipeline/**` files are modified by this review.

## 3. Common A→D traceability

| Check | Judgment | Reason / evidence | Expected correction |
| --- | --- | --- | --- |
| Region identity | valid | A and D use Edogawa `13123`, Niigata `15100`, Nagoya `23100`. | none |
| Formal requirement scope | valid | Both A handoff and D integration keep the current formal requirement at `shelter_location`. | none |
| Source-page seam | valid | D's three adapters use the same official municipal source pages recorded by A for the formal shelter_location evidence. | none |
| A discovery_status vs D assessment semantics | valid | A discovery state is research evidence metadata; D independently acquires and evaluates the source. D does not copy A status into DatasetAssessment. | none |
| RegionExport trace | valid | D integration checks Dataset -> Assessment -> `shelter_discovery` dependency for each region. | none |
| Meaning of FULL | needs_review | Technically correct under current contract, but downstream consumers could overread FULL as “safe shelter selection available.” | D/E/B documentation and presentation must keep FULL scoped to position-based shelter discovery. |
| Meaning of Gap 0 | needs_review | Correct for current capability only; it is not evidence that other shelter/hazard data gaps do not exist. | Preserve capability-scoped wording in downstream use. |

No common item was classified `misclassified`.

---

# 4. 東京都江戸川区 / 13123

## 4.1 Source → A Evidence → D Adapter

**region**

`東京都江戸川区 / 13123`

**source**

- official page:
  `https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html`
- D source CSV:
  `https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv`

**A Evidence**

A records the dataset as:

- `江戸川区 地図データ 避難所・避難所補完施設`
- `requirement_code = shelter_location`
- discovery status `PARTIAL`
- shelter and supplementary-shelter rows are mixed.
- legal/statutory classification requires separate interpretation.

**D result**

- records: 152
- Completeness: 4
- Validity: 4
- Machine Readability: 4
- Geospatial Usability: 4
- Shelter Discovery: `FULL`
- Gap: 0
- Recommendation: 0

### Judgment: source selection — valid

D downloads the same dated official CSV identified by A.

### Judgment: 152 records / normalized names and coordinates — valid

PR #8's earlier independent C check used the same official CSV and established:

- raw source rows: 152
- normalized records: 152
- name / latitude / longitude matched source row-by-row for all 152 records
- missing name/coordinates: 0
- duplicate normalized IDs: 0

The current D adapter only strips surrounding name text and converts the
official latitude/longitude columns to numeric values. It does not geocode or
invent coordinates.

### Judgment: supported disaster handling — valid

The CSV's `災害種別記号` is not assigned a disaster meaning by D. D keeps
`supported_disasters = null` rather than guessing from an icon URL.

### Judgment: 4 / 4 / 4 / 4 assessment — valid

For the current `shelter_location` contract, all 152 rows contain name,
latitude and longitude, and the coordinate values pass the evaluator's basic
numeric/range check.

Validity = 4 means basic structural/range validity for evaluable records. It
does **not** establish real-world facility existence or geographic positional
accuracy.

### Judgment: Shelter Discovery FULL — valid

This is valid only under the current definition:

```text
shelter_location:
  name + latitude + longitude

shelter_discovery:
  position-based shelter presentation
```

It must not be interpreted as disaster-specific safe shelter selection.

### Judgment: Gap 0 / Recommendation 0 — valid

The current critical dependency is READY, so no gap is generated for this
capability. This does not erase A's separate concern that statutory facility
classification is not fully established from the mixed CSV.

### Needs review: Evidence date semantics

D records `published_at = 2025-12-11`, while the municipal page presents that
date as an update date. C cannot establish that it is the initial publication
date.

**Expected correction / D request**

Clarify the semantic contract for `published_at` versus an official “updated”
date. Do not claim first-publication chronology unless the source states it.

---

# 5. 新潟県新潟市 / 15100

## 5.1 Source → A Evidence → D Adapter

**region**

`新潟県新潟市 / 15100`

**source**

- official open-data page:
  `https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/`
- current target on the official page:
  `指定緊急避難場所一覧` CSV

**A Evidence**

A records:

- dataset: `指定緊急避難場所一覧`
- `requirement_code = shelter_location`
- discovery status: `AVAILABLE`
- format: CSV
- responsible section: 防災課
- update date: 2026-09-25

**D result**

- records: 566
- Completeness: 4
- Validity: 4
- Machine Readability: 4
- Geospatial Usability: 4
- Shelter Discovery: `FULL`
- Gap: 0
- Recommendation: 0

### Judgment: current CSV selection — valid

The D adapter does not hard-code an old asset URL. It discovers the current
official page link whose visible label identifies `指定緊急避難場所一覧`.
This matches A's formal shelter_location source selection.

The current official page was independently confirmed to identify the target
CSV, 防災課, and update date 2026-09-25.

### Judgment: 566 record exact source count — needs_review

The D real-data workflow reports 566 normalized records and the user-reported
acceptance run succeeded. C could not independently re-download and recount the
current CSV bytes with the available validation runtime.

Therefore:

- C does **not** classify 566 as wrong.
- C also does **not** independently certify the exact count from raw bytes in
  this review.

**Expected correction**

No D code correction is requested from this finding. For release evidence, a
future C run should preserve a raw-file hash and independently compare current
source-row count to normalized record count, as was done for Edogawa.

### Judgment: name / coordinates normalization — valid in implemented logic

D:

- takes the name from explicit standard-ODS aliases,
- reads explicit latitude/longitude columns,
- preserves missing coordinates as null,
- does not geocode,
- uses an official source ID when available only as part of deterministic ID
  generation.

Given the reported 4/4 location assessment, D found complete coordinates in
the current run. C found no logic that could silently invent them.

### Judgment: disaster columns — valid

D maps only explicitly named standard columns such as flood, landslide,
earthquake and tsunami using a restricted marker set.

These attributes are not used to upgrade `shelter_discovery`, so the current
FULL judgment does not claim hazard compatibility.

### Judgment: Shelter Discovery FULL / Gap 0 — valid

The judgment is valid for current location discovery only.

### Needs review: facility semantics

The current source is specifically a `指定緊急避難場所一覧`. D preserves
`facility_type = designated_emergency_evacuation_site`.

Downstream consumers must not relabel all 566 rows as statutory
`指定避難所`.

---

# 6. 愛知県名古屋市 / 23100

This is the highest-priority validation case.

## 6.1 Source → A Evidence → D Adapter

**region**

`愛知県名古屋市 / 23100`

**source**

`https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html`

**A Evidence**

A records the official page as publishing ward-separated indoor Excel data and
also records outdoor-facility Excel availability.

**D source scope**

D intentionally discovers **only the 16 ward-specific indoor Excel files**.

D real-data result:

- records: 1602
- source files: 16
- Completeness: 0
- Validity: null
- Machine Readability: 4
- Geospatial Usability: 0
- Shelter Discovery: `BLOCKED`
- Gap: 1
- Recommendation: 1

### Judgment: official Excel has no machine-readable latitude/longitude — valid

C independently inspected the current official source structure and a current
official ward PDF representation.

The official ward table contains:

- school district
- number
- facility name
- address
- emergency-evacuation disaster columns
- designated-shelter column

No latitude or longitude field is present in the inspected current ward table.

This agrees with D's adapter behavior:

```text
latitude = null
longitude = null
```

D does not geocode or infer coordinates.

C found no evidence that D overlooked a coordinate column.

### Judgment: 1602 records — needs_review

The D real-data workflow reports 1602 rows extracted from 16 indoor Excel
files. C confirmed that the official page publishes 16 ward-specific indoor
files, but could not independently download and re-count every workbook in the
available validation runtime.

More importantly, the official page also publishes outdoor-facility Excel
files. D's 1602 rows therefore describe the adapter's **indoor source scope**;
they must not be presented as “all shelter/emergency-location rows published
on the official page” without qualification.

### Judgment: Completeness = 0 — valid

Under the current formal `shelter_location` requirement, required fields are:

- name
- latitude
- longitude

All current normalized indoor rows lack coordinates. Therefore 0% meet the
current required-field set and score 0.

This score does **not** mean the source rows contain no useful facility data;
the rows still contain names, addresses and designation/hazard columns.

### Judgment: Validity = null — valid

The evaluator only applies coordinate/name structural validity to rows complete
enough to validate the formal location requirement.

With no name+latitude+longitude sample, the system cannot evaluate that
validity dimension. `null`, rather than 0, correctly preserves “unassessed.”

### Judgment: Machine Readability = 4 — valid

The data is official Excel and D can automatically download and parse the
selected files. Lack of coordinates is not the same as lack of machine
readability.

### Judgment: Geospatial Usability = 0 — valid

For the current point-location requirement, none of the normalized records has
usable latitude/longitude. This is a confirmed zero, not an unknown.

### Judgment: Shelter Discovery = BLOCKED — valid

The current capability is explicitly position-based and treats
`shelter_location` as CRITICAL.

Confirmed zero scores in Completeness / Geospatial Usability are hard blockers,
even though Validity is correctly null.

This does **not** mean the official shelter data is generally unusable.
It means the current point-based Shelter Discovery capability cannot place
these indoor records using the current official source alone.

### Judgment: Gap = 1 — valid

The gap is appropriately `CONFIRMED_IMPROVEMENT`, because:

- the source is acquired,
- records are parsed,
- the location shortfall is observable,
- this is not a NOT_FOUND/UNKNOWN inference.

### Judgment: Recommendation = 1 — valid with wording caution

The recommendation is appropriately an `IMPROVE_DATA` recommendation and
asks the pipeline user to identify missing location information / consider
alternative official data integration.

It does not state that Nagoya publishes no coordinate data anywhere, and does
not instruct D to silently geocode.

Downstream wording must preserve this distinction.

### Needs review: D normalized source scope

The official page exposes more than the 16 indoor files, while D normalizes the
16 indoor files only.

This is not automatically a D defect because the adapter scope is explicit and
the coverage metric is unassessed. However, RegionExport consumers could
mistakenly assume the normalized dataset represents all facilities from the
page.

**Expected D correction / request**

D should make the current indoor-only source scope explicit in Evidence,
findings, or downstream documentation. D should separately decide whether the
formal shelter_location dataset is intended to include outdoor facility files.
C does not make that product/contract decision.

### Needs review: A update-date metadata

At C review time, the current official Nagoya page states:

- page update date: 2026-07-27
- facility list: as of 2026-07-01

The A handoff currently contains `updated_at = 2026-09-01` for Nagoya shelter
evidence.

C cannot reconcile the A date with the current official page.

**Expected A correction / request**

A should re-check and correct or explain the Nagoya shelter source date. Until
then, D should not use A's 2026-09-01 value as an independently confirmed
source update date.

---

# 7. Classification summary

| Region / item | Classification |
| --- | --- |
| Edogawa source selection | valid |
| Edogawa 152 rows / names / coordinates | valid |
| Edogawa 4/4/4/4 | valid |
| Edogawa FULL / Gap 0 | valid within current capability |
| Edogawa published_at semantics | needs_review |
| Niigata current official CSV selection | valid |
| Niigata exact 566 raw-row recount | needs_review |
| Niigata normalization logic | valid |
| Niigata disaster-marker handling | valid |
| Niigata FULL / Gap 0 | valid within current capability |
| Niigata statutory facility-type interpretation | needs_review downstream |
| Nagoya no coordinate columns in current indoor source | valid |
| Nagoya exact 1602 raw-row recount | needs_review |
| Nagoya Completeness 0 | valid |
| Nagoya Validity null | valid |
| Nagoya Machine Readability 4 | valid |
| Nagoya Geospatial Usability 0 | valid |
| Nagoya BLOCKED | valid |
| Nagoya Gap 1 | valid |
| Nagoya Recommendation 1 | valid with wording caution |
| Nagoya indoor-only D source scope | needs_review |
| Nagoya A handoff update date | needs_review |

**misclassified: 0 confirmed items in this review.**

---

# 8. D follow-up requests

C does not change `pipeline/**`. The following are hand-back requests to D:

1. **Clarify Edogawa Evidence date semantics**
   - actual: D stores page update date as `published_at`.
   - reason: source identifies it as update date; first publication is not
     established.
   - expected: clarify field semantics or store the date without implying
     initial publication.

2. **Document Nagoya indoor-only normalization scope**
   - actual: D downloads 16 indoor ward files only.
   - evidence: official source page also exposes outdoor facility files.
   - expected: make the normalized scope explicit; decide separately whether
     outdoor facilities belong to the formal shelter_location dataset.

3. **Keep capability wording narrow**
   - actual: Edogawa/Niigata are FULL; Nagoya BLOCKED.
   - expected: preserve that this is position-based Shelter Discovery, not a
     judgment of safe evacuation suitability.

No D correction is requested to change Nagoya
`Completeness=0 / Validity=null / Geospatial=0 / BLOCKED`; those results are
human-valid under the current formal contract.

---

# 9. Human / future validation still required

- Independently re-download and hash the current Niigata CSV, then compare all
  raw rows to the 566 normalized records.
- Independently download all 16 current Nagoya indoor Excel workbooks and
  reproduce the 1602 record count from raw files.
- Resolve the A handoff Nagoya date discrepancy.
- Decide at A/D product-contract level whether Nagoya outdoor files should be
  part of the formal shelter_location dataset.
- Real-world positional accuracy is not established by the current
  numeric/range validity score.
- No disaster-specific safety, capacity or accessibility conclusion is made in
  this review.

---

# 10. PR #8 disposition

PR #8 contains useful historical evidence for Edogawa and was used as a prior
independent row-level comparison reference.

However, it:

- covers only Edogawa,
- uses an older repository baseline,
- predates the merged A handoff and D A-D Integration Check,
- overlaps substantially with this new three-region validation.

**C recommendation:** treat PR #8 as a **superseded / close candidate** after
this three-region validation is accepted into the C role branch. Do not merge
both as independent current validation reports without clearly marking #8 as
historical.

C does not close or merge #8 in this change.

---

# 11. Handoff to E

## Edogawa

**Yes, with scope limitation.**

The current D output can be consumed for point-based shelter discovery.
`FULL` must not be translated into disaster-specific shelter safety.

## Niigata

**Yes, with scope limitation and one remaining row-count audit.**

The adapter uses explicit official coordinates and does not invent them.
Downstream must preserve the facility type as designated emergency evacuation
sites rather than silently relabeling all rows as designated shelters.

## Nagoya

**No for point placement from the current D shelter_location output.**

The current source has address-based facility information but no
machine-readable coordinates in the selected indoor source. C agrees with D's
`BLOCKED` classification for point-based Shelter Discovery.

E must not invent or geocode coordinates as if they were official source facts.

## Overall C decision

The D evaluation semantics are suitable to hand to E **only when E consumes the
status and scope explicitly**:

- Edogawa / Niigata: usable for current point-based shelter discovery.
- Nagoya: preserve BLOCKED; do not generate shelter points from null
  coordinates.
- `FULL` is not a safety certification.
- `Gap 0` is not a statement that no other disaster-data gaps exist.
