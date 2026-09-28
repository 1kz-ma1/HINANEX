# Contributing to HINANEX

このリポジトリは、卒業制作チームが A/B/C/D/E の担当を並行して統合するための共通基盤です。

AI を利用する開発では、最初に root の `AGENTS.md` を読み、対象ディレクトリに追加の `AGENTS.md` がある場合はそれも守ってください。

## 基本ルール

- `main` は常に動作確認済み・統合可能な状態を保つ。
- `main` へ直接 push しない。
- `main` への最終 merge は Merge Captain が行う。
- Approve と Merge は別物として扱う。
- 変更は担当ブランチ / feature branch から Pull Request で統合する。
- 前提 PR がある場合は PR 本文に `Depends on: #<番号>` を明記する。
- 古い base で通ったテストだけを根拠に merge しない。main 統合前に最新 main へ追従し、再テストする。
- D の JSON 契約を変更する場合は、B/C/E への影響と Schema version 更新要否を明記する。
- `score=null` と `score=0`、`NOT_FOUND` の意味を変更しない。

## 担当別の統合ブランチ

通常作業は担当別 branch 上で進め、毎回 main へ入れる必要はありません。

```text
role/a-data
role/b-frontend
role/c-validation
role/d-pipeline
role/e-gis
```

担当内で複数作業を並行する場合は、role branch から短命 branch を切ります。

```text
feature/a-<topic>
feature/b-<topic>
feature/c-<topic>
feature/d-<topic>
feature/e-<topic>
fix/<topic>
docs/<topic>
```

短命 branch は原則として対応する role branch へ PR を出します。

## main への統合タイミング

担当ごとの作業を進めたあと、統合したいタイミングで一度手を止めます。

Merge Captain が以下を確認して main への merge 順を決めます。

1. critical fix
2. 共通 Contract / Schema / CI / Infrastructure
3. 他 PR へデータや API を提供する provider
4. provider に依存する consumer
5. 独立した feature
6. docs / cleanup

PR の作成順や番号順に機械的に merge しません。

## 前提 PR が未マージのとき

後続作業を止める必要はありません。

前提 branch から次の branch を切る、または適切な role branch を base にして開発を継続できます。

ただし:

- `Depends on: #<PR番号>` を明記する。
- 前提未解決の PR は Draft / blocked 扱いにする。
- 前提 PR が main に入ったら、後続 PR を最新 main へ追従させる。
- conflict 解消後に tests / CI を再実行する。
- Merge Captain の確認前に main へ merge しない。

## Breaking Contract の変更

共有 Contract の破壊的変更は原則として **Add → Migrate → Remove** で進めます。

1. 新フィールド / 新構造を追加
2. Consumer を移行
3. 移行完了を確認
4. 旧構造を削除

一つの PR で provider と全 consumer を同時に壊す変更は避けてください。

## PR 前チェック

変更領域に対応するテストを実行してください。

D / pipeline:

```powershell
cd pipeline
python -m unittest discover -s tests -v
python verify_d_mvp.py
```

Schema を変更した場合:

```powershell
cd pipeline
python generate_contract_schema.py
git diff -- contracts/region_export.schema.json
```

`contracts/region_export.schema.json` に意図しない差分が出た場合は、そのままコミットせず原因を確認してください。

## AI-authored PR

AI が作成・修正した PR には最低限以下を記載します。

- Summary
- Why
- Scope
- Depends on
- Contract impact
- Tests
- Data assumptions
- Known limitations

AI は `main` への merge、force push、テスト削除による失敗隠蔽、防災データの推測補完を行ってはいけません。

## 詳細ルール

- AI 共通ルール: `AGENTS.md`
- D / pipeline: `pipeline/AGENTS.md`
- D の Git 運用ドキュメント: `pipeline/docs/GIT_WORKFLOW.md`
- 統合チェック: `pipeline/docs/INTEGRATION_CHECKLIST.md`
