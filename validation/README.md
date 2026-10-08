# HINANEX — C / Validation

C担当は公式SourceとDのRegionExportの対応を検証します。出力結果を根拠に公式値の意味を推測しないでください。

## 洪水Scenario（2026-10-08）

- Review: [reviews/2026-10-08-flood-scenario-acceptance.md](reviews/2026-10-08-flood-scenario-acceptance.md)
- C独立raw監査: [validation/verify_flood_scenario_acceptance.py](validation/verify_flood_scenario_acceptance.py)
- 対象D: PR #41 / `role/d-pipeline`
- Current C verdict: **CONDITIONAL / NEEDS_REVIEW**, main統合は未承認

D側の `pipeline/` で `python run_all_workflows.py` を実行してから、リポジトリrootで次を実行します。

```powershell
cd C:\HINANEX
.\pipeline\.venv\Scripts\python.exe validation\validation\verify_flood_scenario_acceptance.py
```

このチェックはDの評価関数やModelをimportせず、生成済みRegionExport、Niigata公式raw CSV、Nagoya公式raw Excel bundleを突き合わせます。**単体テストのgreenやCスクリプト成功だけで公式記号の意味まで検証済みとはしません。** 元データの配布状況が変化した場合、固定件数を無理に通すのではなく、SourceとCレビューを更新します。
