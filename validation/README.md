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

GitHubの必須CI `test` は、現在 `validation/validation/test_*.py` の回帰テストを実行します（`.github/workflows/test.yml` の `C independent raw-source regression tests`）。ただし、ユーザー環境の公式raw原本を使う独立照合スクリプトはCIでは実行されません。**合成テストの成功と公式原本の受入を区別**し、後者は入力バイトのSHA256・取得日・担当者の検証記録を別途残してください。

このチェックはDの評価関数やModelをimportせず、生成済みRegionExport、Niigata公式raw CSV、Nagoya公式raw Excel bundleを突き合わせます。**単体テストのgreenやCスクリプト成功だけで公式記号の意味まで検証済みとはしません。** 元データの配布状況が変化した場合、固定件数を無理に通すのではなく、SourceとCレビューを更新します。

## D #44後の3地域の再受入れ

`role/d-pipeline` にマージ済みのD #44で `pipeline/run_all_workflows.py` を実行し、`verify_d_mvp.py`、`verify_a_handoff_integration.py`、`verify_flood_scenario.py` をPASSさせます。その後 `feature/c-flood-scenario-acceptance` に戻ってCの独立検証を実行してください（出力とrawがGit管理外で同じ作業フォルダーに残っている前提）。

```powershell
cd C:\HINANEX
.\pipeline\.venv\Scripts\python.exe -m unittest discover -s validation/validation -p "test_*.py" -v
.\pipeline\.venv\Scripts\python.exe .\validation\validation\verify_flood_scenario_acceptance.py
```

新潟のC側追加ゲート: 公式raw `2階以上` / `3階以上` / `全階可` と`fact.usable_floor_raw`が一致し、該当施設は`UNKNOWN`を維持すること。数値は最新Sourceから集計し、2026-10-08の256件を固定アサーションにしません。`○/×/－`等のODS固有の公式意味と実際の避難安全性は引き続き別ゲートです。

## 2026-10-13 江戸川区の施設同一性と資料の更新履歴

[独立監査の報告](reviews/2026-10-10-edogawa-water-join-snapshot-audit.md) および Draft [PR #136](https://github.com/1kz-ma1/HINANEX/pull/136) を参照。水害待避施設HTML・位置CSV・歴史的D RegionExport・Aの未承認候補台帳を突き合わせ、施設ID/座標/元URL/原文階数の一致を検査する。旧・現下小岩小学校では、2023年選挙資料と2025年学校移転・水害資料で、同じ名前が異なる住所を指している履歴を区別する。**同じ学校URLが複数の位置施設レコードにあっても施設同一性の確定キーに使わない。** 

専用合成テスト：`python -m unittest discover -s validation/validation -p "test_edogawa*py" -v`。実データに対するC最終承認・洪水単独の適合判定は引き続き別ゲート。前提A PR #133、D #135とIssue #134/#137を確認する。
