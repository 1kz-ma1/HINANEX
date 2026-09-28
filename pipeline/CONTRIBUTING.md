# Contributing to HINANEX

このリポジトリは、卒業制作チームがA/B/C/D/Eの担当を並行して統合するための共通基盤です。

## 基本ルール

- `main` は常に動く状態を保つ。
- 原則として `main` へ直接pushしない。
- 変更は担当別ブランチからPull Requestで統合する。
- PR前に `python -m unittest discover -s tests -v` を通す。
- DのJSON契約を変更する場合は、B/Cへの影響とSchema version更新要否を明記する。
- `score=null` と `score=0`、`NOT_FOUND` の意味を変更しない。

## ブランチ名

```text
feature/a-<topic>      A: データ調査
feature/b-<topic>      B: UI
feature/c-<topic>      C: 検証
feature/d-<topic>      D: データ基盤
feature/e-<topic>      E: GIS
fix/<topic>            不具合修正
docs/<topic>           文書のみ
```

## PR前チェック

```powershell
python -m unittest discover -s tests -v
python generate_contract_schema.py
```

`contracts/region_export.schema.json` に意図しない差分が出た場合は、そのままコミットせず原因を確認してください。

詳細は `docs/GIT_WORKFLOW.md` を参照してください。
