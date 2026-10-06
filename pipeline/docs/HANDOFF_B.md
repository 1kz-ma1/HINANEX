# B担当への引き渡し — UI

Bは自治体固有のCSV/Excelを直接読みません。Dが生成する1地域1JSONを利用します。

```text
data/output/edogawa.json
data/output/niigata.json
data/output/nagoya.json
```

## 固定トップレベル

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

## UIで重要な扱い

- `score=null` を0点として表示しない。
- `UNKNOWN` を「悪い」と表現しない。
- `BLOCKED` はCapabilityが現在のデータでは成立しない状態であり、自治体評価ではない。
- `FULL` は現在の `shelter_location` が位置ベースのShelter Discovery条件を満たす意味に限定する。安全な避難所選定や災害適合性まで保証する表示にしない。
- `INVESTIGATION` は追加調査対象であり、改善不足の断定ではない。
- 緯度経度は`null`になり得る。地図上に無理に配置しない。

## 推奨表示単位

地域選択後に以下を同一画面で辿れるとよいです。

1. Capability状態
2. Data Quality / Application Readiness
3. Gap
4. Recommendation
5. Evidence / reason

### 名古屋市の現行Dataset scope

名古屋市の `shelter_location` は、D Adapterが取得する16区別の屋内施設Excelのみを対象にしています。同じ公式ページ上の屋外施設データは含まれないため、record件数を「名古屋市の全避難関連施設数」と表示しないでください。

JSON Schemaは `contracts/region_export.schema.json` を参照してください。
