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

今回の名古屋Excel正規化の回帰テスト（サンプルWorkbookを使用・ネットワーク接続なし）は次を実行します。

```powershell
cd C:\HINANEX
.\pipeline\.venv\Scripts\python.exe -m unittest discover -s validation/validation -p "test_*.py" -v
```

GitHubの既存CIは `validation/validation` のこの新規テストを自動実行しません。実行結果を別途記録し、ユーザー環境の公式raw監査と区別します。

このチェックはDの評価関数やModelをimportせず、生成済みRegionExport、Niigata公式raw CSV、Nagoya公式raw Excel bundleを突き合わせます。**単体テストのgreenやCスクリプト成功だけで公式記号の意味まで検証済みとはしません。** 元データの配布状況が変化した場合、固定件数を無理に通すのではなく、SourceとCレビューを更新します。

## D #44後の3地域の再受入れ

`role/d-pipeline` にマージ済みのD #44で `pipeline/run_all_workflows.py` を実行し、`verify_d_mvp.py`、`verify_a_handoff_integration.py`、`verify_flood_scenario.py` をPASSさせます。その後 `feature/c-flood-scenario-acceptance` に戻ってCの独立検証を実行してください（出力とrawがGit管理外で同じ作業フォルダーに残っている前提）。

```powershell
cd C:\HINANEX
.\pipeline\.venv\Scripts\python.exe -m unittest discover -s validation/validation -p "test_*.py" -v
.\pipeline\.venv\Scripts\python.exe .\validation\validation\verify_flood_scenario_acceptance.py
```

新潟のC側追加ゲート: 公式raw `2階以上` / `3階以上` / `全階可` と`fact.usable_floor_raw`が一致し、該当施設は`UNKNOWN`を維持すること。数値は最新Sourceから集計し、2026-10-08の256件を固定アサーションにしません。`○/×/－`等のODS固有の公式意味と実際の避難安全性は引き続き別ゲートです。
