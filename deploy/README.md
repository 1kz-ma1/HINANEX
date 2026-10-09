# HINANEX Render Staging

HINANEXの`main`統合状態を、チーム全員が同じURLで確認するための共有Stagingです。

## ステージングの入口（2026-10-09 UX改善案）

スマートフォンでトップページに開発用語が多く、`Frontend / GIS` の違いが分かりにくいという実機フィードバックを受け、`deploy/staging-index.html` を**入口として再整理**しています。

- ヘッダーに小さく「チーム検証用」、本文は「防災情報を、見て・確かめる。」と、利用者の目的で始める。
- 既存パスはそのまま、`/frontend/` は **地域の分析を見る**、`/gis/gis/` は **地図で情報を探す** とする。Capability等の内部概念は入口カードに並べない。
- 長文の `main` / D Pipeline / RegionExport 説明は標準HTML `details`（**この環境について**）へ移動。開発・検証用で実災害の避難判断に使えない注意は、閉じた領域には入れず画面下に常時表示する。
- モバイルは上端から必要な情報が見える1列のタップしやすいカード。ページ全体の縦方向中央寄せは廃止。JS依存やログイン機能・新たなデータ解釈は追加しない。
- 実際の Render Staging は **main** が自動デプロイ元。UIのPRが別ブランチ上にあっても、`main` のマージとRenderデプロイが完了するまでは **公開URLの画面は変わらない**。main最終マージはMerge Captainのみ。

静的入口のみを改善するもので、`frontend/` や `gis/gis/` の実装・D JSON生成・C根拠の整合性は変更しません。構造確認テストは`python -m unittest discover -s deploy/tests -v`に含まれます。

## 公開構成

Render Static Siteのbuild時にD Pipelineを再実行し、公開対象だけを`deploy/dist/`へまとめます。

```text
deploy/dist/
├─ index.html
├─ frontend/
├─ gis/gis/
└─ pipeline/data/output/
   ├─ edogawa.json
   ├─ niigata.json
   ├─ nagoya.json
   └─ manifest.json
```

FrontendとGISは同じD RegionExportを参照します。runtime artifactはGitへcommitしません。

## Render設定

- Repository: `https://github.com/1kz-ma1/HINANEX`
- Branch: `main`
- Auto Deploy: enabled
- Build Command:

```bash
python -m pip install --upgrade pip && python -m pip install -r pipeline/requirements.txt && python deploy/build_staging.py
```

- Publish Directory: `deploy/dist`

現在のD-MVPはsecretを必要としません。将来token等が必要になった場合も、値はGitへcommitせずRender Environment Variablesで管理します。

## URL

公開先のoriginを`https://<service>.onrender.com`とすると:

- Landing: `/`
- Frontend: `/frontend/`
- GIS: `/gis/gis/`
- RegionExport: `/pipeline/data/output/edogawa.json` 等

## Build failure policy

Pipelineの再生成、RegionExportの必須top-level構造、またはfilenameと`region.code`の対応が不正な場合、buildはfail closedします。

古い/壊れたRegionExportへ暗黙fallbackして新しいdeployを成功扱いにはしません。

## ローカル確認

D出力を生成済みなら:

```powershell
python deploy/build_staging.py --skip-pipeline
python -m http.server 8000 --directory deploy/dist
```

`http://localhost:8000/`からFrontend / GISを確認できます。

実データを含めてRender相当のbundleを作る場合:

```powershell
cd pipeline
python -m pip install -r requirements.txt
cd ..
python deploy/build_staging.py
```

## Release flow

```text
feature/role PR
  -> main merge
  -> Render auto deploy
  -> shared staging URLでIntegration Acceptance
  -> RC判定
```

Stagingは開発・発表確認用であり、防災判断を行う本番サービスとして扱いません。
