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

## F03/P-02独立QAの非公開境界（2026-11-13）

F03端末保存の独立試作（[PR #359](https://github.com/1kz-ma1/HINANEX/pull/359)）は、**ソース/テスト証跡としてリポジトリへ取り込めても、本番相当のRender Stagingには配信しない**。ビルド時に次を明示的に除外する。

- `frontend/prototypes/f03-storage-contract-qa/**`（ページ・JS・CSS・説明）
- `frontend/docs/F03_P02_STORAGE_CONTRACT_QA_20261111.md` と `frontend/docs/evidence/f03-p02-20261111/**`
- `frontend/tests/f03-storage-contract.test.js` と `frontend/tests/f03-storage-http-chrome.test.js`

対象は`deploy/build_staging.py`の公開Front-endコピーのみ。**Git上のテスト・証跡・ソースは保持**し、CIのF03回帰は従来どおり実行する。既存のB分析ページ、他の試作、GIS、RegionExport/Schemaは変更しない。テストでは配布物の中にQA用ファイルがないことに加え、他の公開資産が残ることを確認する。

これは **F03の正式保存仕様/同意/保存期間・権限の承認ではない**。新規F03ファイルが増えた際には配布ホワイトリストの再審査が必要。将来の一般公開は独立Issue/PRとオーナー受入を必須とする。

## F02 read-only施設参照の非公開境界（2026-11-13）

[PR #357](https://github.com/1kz-ma1/HINANEX/pull/357) は、**実在施設の出典利用条件・施設属性の意味・公開範囲の承認が未完了**（[A Issue #366](https://github.com/1kz-ma1/HINANEX/issues/366)）。同PRのコードと回帰テストをmainに保全できるよう、**F02独立画面、CSS、専用モデル・コントローラ、ローカル専用プレビューサーバ、検証CLI、専用テスト・文書**をRender配布物から明示的に除外する。

| 対象 | 公開バンドルでの扱い |
|---|---|
| `frontend/f02.html`, `frontend/f02.css` | 除外（外部URLから開けない） |
| `frontend/src/f02-page.js`, `frontend/src/f02-shelter-reference.js` | 除外 |
| `frontend/scripts/serve-f02-preview.cjs`, `frontend/scripts/check-f02-real-export.js` | 除外（Git/CLI/テストには保持） |
| `frontend/docs/F02_REGION_EXPORT_CONSUMER_20261111.md` | 除外 |
| `frontend/tests/f02-page-http-browser.test.cjs`, `f02-preview-http.test.cjs`, `f02-real-export-check.test.js`, `f02-shelter-reference.test.js` | 除外（Git上ではCI対象） |

**非対象・変更なし:** 既存 `/frontend/`分析画面、既存合成F02 Prototype、`/gis/gis/`地図、D RegionExport配信、共通Contract/Schema、F03の非公開制御。特に、`/pipeline/data/output/edogawa.json` は既存の配信範囲のままであり、本措置によって公式データの公開・再配信を新規承認したわけではない。**既存の配信データ自体も正式な公開審査を別途要する。**

F02の実JSON検証を行う際は、Git内のローカル専用 `npm run preview:f02` を用いる。Loopback以外への公開/新たなナビ接続は禁止。F02の正式公開は、#366の人間による具体的利用条件審査、施設属性・安全性の非保証表示、アクセシビリティ、オーナーの公開判断を満たした別PRで行う。本ガードは**列挙した既知ファイルにだけ適用**されるため、新たなF02ファイルを追加するときは再度配布境界を確認する。

## F05/P0ローカル導線試作の非公開境界（Issue #373 / 2026-11-13）

[Draft PR #371](https://github.com/1kz-ma1/HINANEX/pull/371) のF05画面は、F01洪水情報とF02施設記録を本人操作で別々に確かめるための **ローカル限定の試作**。公式CSVの再配信・避難先の安全性・現在開設状況・経路の公開承認は受けていない。**Gitのソース保全とRenderの外部配信は分ける。**

Render配布物の `frontend/**` コピーから次を明示的に除外する（`deploy/build_staging.py`）：

- `frontend/prototypes/f05-flood-journey/**` — ディレクトリ全体。後で追加されるネストした試作JS/CSS/文書も非配信。
- `frontend/src/f05-journey-model.js` — F05のローカル遷移ガード。
- `frontend/tests/f05-journey.test.js` — GitHub上のテストは保持し、Render配布物からのみ除外。
- `frontend/docs/F05_MINIMAL_JOURNEY_20261113.md` — 未公開のレビュー文書。

**F02 #370・F03 #368の除外は維持する。** 既存の公開B地域分析・合成F02試作、GIS、RegionExport配信には影響を与えない。RegionExportの実施設記録JSONは現行配信対象であり、今回のF05配信除外は**データ自体を非公開化することでも、公式原本の利用許諾を承認することでもない**。公式CSV利用条件と第三者権利の別ゲートは [#366](https://github.com/1kz-ma1/HINANEX/issues/366)。

`deploy/tests/test_real_bundle_assets.py` はF05の既知4種の非公開資材に加え、将来のネストしたF05試作アセットを**一時checkoutに合成配置**し、ソースには存在しても配布物に存在しないことを全件確認する。F02/F03の既存除外・合成F02プロトタイプ・Frontend/GIS/RegionExportの維持を同時に回帰する。

**統合順序**：本Deploy共有PR（required `test` PASS / human Merge Captain確認）→main先行マージ→Render上のF05直URL非配信確認→#371の最新mainへの追従とCI/Owner判断。#371の現行F05モデルによるloopbackリンク抑止は**外部からHTMLが配布されないという保証ではない**。正式F05公開は、別Issue/PRで必要な人間の範囲承認後のみ実施する。

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
