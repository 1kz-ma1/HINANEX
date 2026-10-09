# HINANEX Render Staging

HINANEXの`main`統合状態を、チーム全員が同じURLで確認するための共有Stagingです。

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

## main統合前にCIで確認すること

`.github/workflows/test.yml` の同一の必須 `test` ジョブで、D Python回帰・C独立検証・B Frontend（`npm test`、`npm run lint`、`npm run build`）・E GIS（地域データのread-only inspector含む）・Render staging bundle・Schema同期を全て実行します。いずれかが失敗したPRをgreenとして扱いません。

Render bundleの単体テストに加え、`deploy/tests/test_real_bundle_assets.py` は**現在のリポジトリに存在するB/Eの実ファイル**を一時ディレクトリへコピーし、独立したテスト用最小RegionExport（3自治体コードのみ）で配布bundleを構築します。HTMLで参照するローカルCSS/JSが配布物内に存在し、入口が`/frontend/`と`/gis/gis/`を指すことを検証します。テスト用JSONは一時ディレクトリ限定で、実データ・C監査証跡を読み取ったり削除・上書きしたりしません。

**まだ保証しないこと**：本番相当の`python deploy/build_staging.py`を用いた実自治体データの再生成・RenderへのHTTPデプロイ・外部洪水ラスタの全面的可用性・ユーザー実機の動作。公式GSI `skhb01`参考地点のC検証済みカタログは`pipeline/data/output/gsi_verified_tiles/`を任意で読み込む仕様ですが、現行のRenderビルダーでは追加配布を保証していません。公開サイトで9/9が表示されると主張せず、データがない場合は`未照合`のままとし、追加配布する場合はC受入・HTTPS provenanceのgateを別途設計してください。

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
