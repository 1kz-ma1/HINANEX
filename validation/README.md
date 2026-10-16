# HINANEX — C / Validation

## 本番発表向け Phase 1：公式原本の差分を独立検証

公式原本を再取得する際は、[Cの原本比較手順](docs/FINAL_SOURCE_RECAPTURE_20261016.md)を参照してください。
既存の7資料取得・byte検証・内容preflightを**両方の取得回**に実施した後、
`compare_edogawa_source_snapshots.py` でSHA256・取得時刻・元資料件数の変化を比較します。
変更が検出されても施設同一性・災害種別は**自動承認しません**。
別資料の洪水指定や現在の開設状況も推測しません。


C担当は公式SourceとDのRegionExportの対応を検証します。出力結果を根拠に公式値の意味を推測しないでください。

## 過去災害再現検証（Historical Replay、2026-10-13提案）

- 設計仕様: [docs/HISTORICAL_REPLAY_VALIDATION_SPEC_20261013.md](docs/HISTORICAL_REPLAY_VALIDATION_SPEC_20261013.md)
- 検証の3パターン: 整合（MATCH）/ 判定保留（ABSTAIN）/ 不一致（MISMATCH）。比較不可（NOT_EVALUABLE）は統計上別扱い。
- 2019年台風19号・江戸川区は**候補事例**であり、再現検証や実機デモは**未実装・未承認**。当時利用できた入力と事後実績の混入を禁止。
- 基礎受入 [Issue #89](https://github.com/1kz-ma1/HINANEX/issues/89) と独立C監査を先行。A/B/D/Eへの実装依頼は別Issue/PRで管理する。

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
