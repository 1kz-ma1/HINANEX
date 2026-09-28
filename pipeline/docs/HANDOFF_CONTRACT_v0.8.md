# HINANEX B/C 引き渡し契約 v0.8

## 目的

D担当が自治体ごとの異なる元データを吸収し、B（UI）とC（検証）が同じ出力だけを見れば作業できる状態に固定する。

Bは自治体固有CSV/Excelの列名や取得方法を扱わない。Cは出典から最終Recommendationまで判定根拠を追跡する。

## 1地域1JSON

```text
data/output/
├─ edogawa.json
├─ niigata.json
└─ nagoya.json
```

トップレベルSchemaは固定する。

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

## B担当が主に使う場所

- `region`: 地域選択・タイトル
- `assessments`: Data Quality / Application Readiness
- `capabilities`: FULL / DEGRADED / BLOCKED / UNKNOWN
- `gaps`: 何が不足・未確認か
- `recommendations`: 改善案・追加調査案
- `datasets[].records`: 地図や施設一覧などの実データ

Bは `score = null` を0点として表示しない。

- `0`: 評価した結果、その軸では利用できない
- `null`: 未評価 / 現時点で判断できない

## C担当が追う経路

```text
datasets[].evidence
    ↓ source / publisher / fetched_at
Normalized record
    ↓ requirement_code
assessments
    ↓ findings / MetricScore.reason
capabilities
    ↓ dependency_results / reasons
gaps
    ↓ kind / severity / reason
recommendations
    ↓ actions / rationale
```

`requirement_code` と `capability_code` を結合キーとして使う。

## Gapの解釈

- `CONFIRMED_IMPROVEMENT`: 現在の取得データで不足を確認できた改善候補
- `INVESTIGATION`: 取得可否・存在・評価自体が未確認。自治体側の未公開や不足とは断定しない

HINANEXは自治体ランキングを作らない。Capability単位で「現在の取得経路・現在の判定ルールでは何ができるか」を示す。

## v0.8時点の対象範囲

現在は3地域とも `shelter_location -> Shelter Discovery` の縦パイプラインが対象。

今後DataRequirementやCapabilityが増えても、トップレベルSchemaは維持し、各配列に追加する。
