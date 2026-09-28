# GitHub Repository Setup

初回リポジトリ作成時の推奨手順です。

## 1. Repository

- Repository name: `HINANEX`
- Default branch: `main`
- 学校チーム内だけで進める期間はPrivateでも可

## 2. 初回push前

```powershell
python -m unittest discover -s tests -v
python generate_contract_schema.py
```

`.gitignore` によりRawデータ・生成JSON・`.env`・`.venv`が除外されていることを確認します。

## 3. Ruleset / Branch protection

`main` に対して次を推奨します。

- Require a pull request before merging
- Require status checks to pass
- 必須check: `test`
- Block force pushes

## 4. チーム合流

各担当は `docs/HANDOFF_*.md` を確認してから担当ブランチを作成します。

最初の統合時点ではディレクトリ大移動を行わず、現在動いているD import構造を維持してください。
