# HINANEX Architecture — v1.0-D-MVP

## 1. Dパイプラインの責務

Dは自治体固有の公開形式をB/C/Eへ漏らさず、同じ共通Schemaと評価フローへ変換します。

```text
Official Source
  -> SourceAdapter
  -> Raw evidence
  -> NormalizedDataset
  -> DatasetAssessment
  -> CapabilityAssessment
  -> GapAnalysis
  -> RegionExport
```

## 2. レイヤ

### Acquisition / Adapter

`src/hinanex/adapters/`

自治体固有のCSV / Excel / 公開ページ差を吸収します。Adapterは、取得した事実を勝手に補完せず、確認できない値は`None`として保持します。

### Common Models

`src/hinanex/models/`

- `NormalizedDataset`
- `ShelterRecord`
- `DatasetAssessment`
- `CapabilityAssessment`
- `GapItem` / `Recommendation`
- `RegionExport`

B/C/Eは自治体固有Adapterではなく、原則これらの出力だけを利用します。

### Evaluation

`src/hinanex/evaluation/`

現在は `shelter_location` と `Shelter Discovery` の縦スライスを実装しています。

### Integration Contract

`data/output/{region}.json` と `contracts/region_export.schema.json` がB/Cとの境界です。

## 3. IDと結合キー

- 地域: `region.code`
- DataRequirement: `requirement_code`
- Capability: `capability_code`

CはEvidenceからRecommendationまでこのキーで追跡します。

## 4. Null semantics

HINANEXでは欠損を0点と同一視しません。

- `score=0`: 評価済みで条件を満たさない
- `score=null`: 未評価 / 評価不能
- `supported_disasters=null`: 元データから安全に判断不能
- `latitude/longitude=null`: 元データに機械可読座標がない

## 5. 現在の検証地域

- 江戸川区: CSV / 座標あり
- 新潟市: 標準ODS系CSV
- 名古屋市: 16区Excel統合 / 座標なし

異なるデータ公開形態を同じCapability判定まで流せることがD-MVPの検証目的です。

## 6. 今後の拡張境界

MVP後の候補:

- `shelter_disaster_compatibility`
- `shelter_accessibility`
- `shelter_capacity`
- flood hazard / inundation depth
- Population Exposure Analysis

これらは現在のSchemaや評価ルールを壊さず、DataRequirementとCapabilityを追加して拡張します。
