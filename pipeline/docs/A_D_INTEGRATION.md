# A → D Integration Check

A担当が調査・整理したEvidenceと、D担当の実装済みPipelineが同じ前提で接続できていることを再現可能に確認するためのチェックです。

## 目的

このチェックはAの判定をDへコピーするためのものではありません。

責務は以下のまま分離します。

```text
A
  公式ソースを調査しEvidenceを整理
  ↓
D
  Adapterで公式ソースを取得
  ↓
  Normalize
  ↓
  Assessment
  ↓
  Capability
  ↓
  Gap / Recommendation
  ↓
  RegionExport
```

Aの `discovery_status` とDのAssessment / Capabilityは意味が異なるため、値を同期・上書きしません。

## 現在の正式対象

D-MVPで正式に実装済みの縦スライスは次のみです。

```text
shelter_location
  -> Shelter Discovery
```

A handoffに含まれる洪水・アクセシビリティ等は、将来候補として保持します。D側の正式な `requirement_code` が追加されるまでは、このIntegration Checkの処理対象にしません。

## 自動テスト

通常のDテストに含まれます。

```powershell
python -m unittest discover -s tests -v
```

`tests/test_a_handoff_integration.py` は、コミット済みの

```text
../data-research/handoff/HINANEX_A_final_handoff.json
```

を読み、次を確認します。

- AとDの対象3地域・region_codeが一致する
- AとDのProject release / RegionExport schema versionが一致する
- 正式なDataRequirementが現時点で `shelter_location` のみである
- 各地域でAの公式Source pageとD Adapterの公式Source pageが一致する
- A handoffに未調整の正式 `requirement_code` が混入していない
- RegionExport側で Dataset → Assessment → Shelter Discovery dependency を追跡できる

自治体側のデータ件数は変化し得るため、レコード件数そのものはCIの固定値にしません。

## 実データによる再現確認

まずDの3地域Workflowを実行します。

```powershell
python run_all_workflows.py
python verify_d_mvp.py
```

続けてA-D Integrationを確認します。

```powershell
python verify_a_handoff_integration.py
```

成功時は次の形式で表示されます。

```text
A-D Integration: READY
Contract schema: 0.9
Formal requirement: shelter_location

東京都江戸川区
  records: <current count>
  D evidence: <current count>
  capability: FULL
  gaps: <current count>
  recommendations: <current count>

新潟県新潟市
  ...

愛知県名古屋市
  ...
```

レコード数やCapability結果は最新の公式データとDの評価結果をそのまま表示し、テスト都合で固定しません。

## Cへの引き渡し

このチェックが成功した後、Cは以下を独立して検証します。

```text
A Evidence
  -> D NormalizedDataset
  -> DatasetAssessment
  -> CapabilityAssessment
  -> Gap
  -> Recommendation
```

Integration Checkが成功しても、Dの評価内容が人間の観点で妥当であることまで保証するものではありません。その判断はCのValidationで行います。
