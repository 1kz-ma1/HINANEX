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
