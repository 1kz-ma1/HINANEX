# Pipeline AI Rules

このディレクトリでは root `/AGENTS.md` に加えて本ルールを適用します。

## Ownership

`pipeline/` は D 担当の領域です。

責務:

- Discovery / acquisition
- raw archive
- municipal Adapter
- common schema normalization
- DatasetAssessment
- CapabilityAssessment
- Gap / Recommendation
- RegionExport
- B/C/E 向け共有 Contract

## Stability

現在の D-MVP は統合基盤として扱います。
依頼に必要のない全面リファクタリングは禁止です。

既存の以下の意味を保持してください。

- `score=0` = 評価済み・要件未達
- `score=null` = 未評価 / 不明
- `NOT_FOUND` = 現在の取得経路で見つからない
- `CONFIRMED_IMPROVEMENT` と `INVESTIGATION` の区別
- Criticality は `CapabilityDependency` 側に存在する

## Adapter rules

自治体固有の取得・解釈は Adapter 内へ閉じ込めます。

AI は:

- 欠損座標を生成しない。
- 不明な災害種別を推測しない。
- アイコン名から意味を断定しない。
- 公式ソースに無い値を補わない。
- Raw と Evidence から正規化結果を追跡できるようにする。

## Contract changes

`RegionExport` を変更する前に:

1. `src/hinanex/models/export.py`
2. `contracts/region_export.schema.json`
3. `docs/HANDOFF_*.md`
4. `tests/test_export.py`
5. `tests/test_integration.py`

を確認してください。

破壊的変更は Add → Migrate → Remove を原則とします。

## Required checks

最低限:

```powershell
python -m unittest discover -s tests -v
python verify_d_mvp.py
```

Schema 変更時:

```powershell
python generate_contract_schema.py
git diff -- contracts/region_export.schema.json
```

実データ workflow が必要な変更では:

```powershell
python run_all_workflows.py
```

外部データへアクセスできず確認できない場合は、その事実を明記してください。
