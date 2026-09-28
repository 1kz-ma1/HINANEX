# HINANEX v1.0-D-MVP 最終差分

v0.9の評価・統合エンジンを変更しすぎず、GitHubでA/B/C/Eが安全に合流できる状態まで仕上げる差分です。

## 追加・変更

- GitHub Actions: Python 3.12 / unittest / Schema同期チェック
- PR / Issueテンプレート
- `.gitignore`強化（Raw・生成JSON・秘密情報を除外）
- `.editorconfig` / `.gitattributes`
- A/B/C/Eの引き渡し文書
- Architecture / Git workflow / Integration checklist
- D-MVP v1.0完了条件
- `verify_d_mvp.py` によるローカル最終受入確認
- version metadataを `src/hinanex/version.py` に集約
- Project release `v1.0-D-MVP` とRegionExport contract `0.9` を分離
- 他担当用ディレクトリの受け皿を追加

## 適用後の確認

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

すでに3地域workflowを生成済みなら:

```powershell
python verify_d_mvp.py
```

Raw/出力を再生成する場合:

```powershell
python run_all_workflows.py
python verify_d_mvp.py
```

## GitHub投入前

`docs/GITHUB_SETUP.md` と `docs/GIT_WORKFLOW.md` を参照してください。

GitHubの`main`でActionsの`test` jobがgreenになれば、D担当v1.0-D-MVPを正式完了扱いにできます。
