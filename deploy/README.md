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

## 2026-10-14: 発表用・検証理解デモ

Portal `/` に、C-owned固定説明データ #226、staging配布 #227、B読み取り専用画面 #228 の `/frontend/historical-evidence-demo.html` を最優先で案内するカードを追加。既存 `/frontend/` と `/gis/gis/` の入口は維持する。Eガイド付きパネルからも同じデモへ移動できる（#229）。旧3地域地図ツアーはデータ欠損/出典閲覧の補助であり、歴史予測の証拠ではない。

このデモは実災害の予測精度を示さず、T0機械照合・T1比較不可・合成負系を別々に説明する。Renderでの実配信/人間の実機確認・90秒実演は別途確認する。
