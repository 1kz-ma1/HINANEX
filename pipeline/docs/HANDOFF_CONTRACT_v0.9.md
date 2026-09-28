# HINANEX B/C 引き渡し契約 v0.9

## 目的

D担当が自治体固有のCSV/Excel/公開方法の差を吸収し、B（UI）とC（検証）が自治体固有処理を意識せず作業できるようにする。

## 1地域1JSON

```text
data/output/
├─ edogawa.json
├─ niigata.json
└─ nagoya.json
```

トップレベルは固定:

```json
{
  "region": {},
  "datasets": [],
  "assessments": [],
  "capabilities": [],
  "gaps": [],
  "recommendations": [],
  "meta": {}
}
```

`meta.schema_version` は `0.9`。

## B担当が使う主な場所

- `region`: 地域名・地域コード
- `datasets[].records`: 施設一覧・地図表示用の正規化データ
- `assessments`: Data Quality / Application Readiness
- `capabilities`: FULL / DEGRADED / BLOCKED / UNKNOWN
- `gaps`: 確認済み不足・追加調査対象
- `recommendations`: 改善案 / 調査案

### scoreの意味

- `0`: 評価済みで利用できない / 条件を満たさない
- `null`: 未評価または評価不能

UI上で`null`を0点として描画しない。

## v0.9のValidityルール

欠損と不正値を分離する。

例: 名古屋市の元Excelに機械可読な緯度経度が存在しない場合:

```text
Completeness = 0
Validity = null
Geospatial Usability = 0
```

これは「座標値が不正」ではなく「座標値が存在せず、妥当性を評価できない」ため。

Capability側では確定的な0点ブロッカーを未評価軸より優先するため、Shelter DiscoveryはBLOCKEDとして判定できる。

## C担当が追う経路

```text
datasets[].evidence
  -> dataset.requirement_code
  -> assessments[].MetricScore.reason / findings
  -> capabilities[].dependency_results / reasons
  -> gaps[].kind / severity / reason
  -> recommendations[].actions / rationale
```

結合キー:

- `requirement_code`
- `capability_code`

さらに `data/output/manifest.json` には地域ごとのSource・レコード件数・Capability状態を集約している。

## Gapの解釈

- `CONFIRMED_IMPROVEMENT`: 現在取得できているデータから具体的な不足を確認できた
- `INVESTIGATION`: データの存在・取得可否・評価状態が十分に確定していない

`NOT_FOUND` を自治体の未公開と断定しない。

## 契約検証

```powershell
python validate_region_contracts.py
```

以下を自動確認する。

- schema_version
- 地域識別情報
- meta件数と配列長
- Evidence件数
- Dataset -> Assessmentの対応
- Capability dependency -> Assessmentの対応
- Gap / Recommendationの参照整合性

JSON Schemaは以下。

```text
contracts/region_export.schema.json
```
