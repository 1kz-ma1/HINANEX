# Git / GitHub Workflow

## 基本方針

`main` はデモ可能な安定版です。担当者は自分のブランチで作業し、PR経由で統合します。

## ブランチ例

```text
feature/a-edogawa-evidence
feature/b-analysis-dashboard
feature/c-validation-sheet
feature/d-new-adapter
feature/e-flood-map
fix/contract-null-display
```

## PRフロー

1. `main` の最新を取得
2. 担当ブランチを作成
3. 実装・文書更新
4. ローカルテスト
5. push
6. Pull Request
7. CIが成功してからmerge

D契約を変更するPRでは、以下を本文に必ず書きます。

- 変更したJSONフィールド
- Bへの影響
- Cへの影響
- `schema_version`を変更するか
- migrationが必要か

## main保護の推奨設定

GitHubのBranch protection / Rulesetで最低限以下を有効にします。

- Pull Request経由で変更
- CI status check成功を必須化
- force push禁止
- branch deletion禁止（main）

レビュー必須人数はチーム運用速度に合わせて設定してください。CI成功は必須にすることを推奨します。

## Merge方式

卒業制作では履歴を追いやすくするため、原則Squash mergeを推奨します。大きな共同実装でコミット履歴自体が意味を持つ場合のみ通常mergeを検討します。
