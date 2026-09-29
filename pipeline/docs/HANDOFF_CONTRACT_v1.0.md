# HINANEX B/C引き渡し契約 — D-MVP v1.0

プロジェクトリリースは`v1.0-D-MVP`ですが、RegionExport JSON Schemaは互換性維持のため`0.9`のままです。

## Output

```text
data/output/
├─ edogawa.json
├─ niigata.json
├─ nagoya.json
└─ manifest.json
```

RegionExportの固定トップレベル:

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

## Contract semantics

- `meta.schema_version = "0.9"`
- `score=0`: 評価済みで利用条件を満たさない
- `score=null`: 未評価 / 評価不能
- `CONFIRMED_IMPROVEMENT`: 現在のEvidenceから不足を確認できる
- `INVESTIGATION`: 追加調査が必要
- `NOT_FOUND`: HINANEXの現在の取得経路で見つからない
- `Evidence.published_at`: 公式Sourceで公開日として確認できる場合のみ設定する。更新日しか確認できない場合は初回公開日を推測せず `null` とし、確認できた更新日の意味を `notes` に残す。
- `Shelter Discovery = FULL`: 現在の `shelter_location` dependency（施設名称・緯度経度）が位置ベース探索の条件を満たす状態。災害別安全性、収容人数、アクセシビリティ、避難経路安全性、リアルタイム利用可否を保証しない。

## Dataset scope

- 名古屋市の現行 `shelter_location` Datasetは、公式ページにある16区別の**屋内施設Excelのみ**をD Adapterが取得・正規化している。
- 同じ公式ページ上の屋外施設データは現行Datasetへ含めていない。
- したがって、名古屋のrecord件数を「公式ページ上の全避難関連施設数」と解釈しない。

## Traceability

```text
datasets[].evidence
  -> requirement_code
  -> assessments[].reason / findings
  -> capabilities[].dependency_results / reasons
  -> gaps[].reason
  -> recommendations[].rationale / actions
```

## Validation

```powershell
python validate_region_contracts.py
```

JSON Schema:

```text
contracts/region_export.schema.json
```

B/CがSchema変更を必要とする場合は、DのPRで影響範囲とmigrationを明記してから`schema_version`を更新します。
