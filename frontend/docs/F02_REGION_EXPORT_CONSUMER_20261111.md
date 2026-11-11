# F02 S-03 — RegionExport v0.9 read-only Consumer（実装仕様 / Draft）
2026-11-11 / Issue #355 / owner P0

## Decision
- **1地域のみ**：江戸川区 region.code=13123。既存D出力 pipeline/data/output/edogawa.json を frontend/src/region-export-loader.js から読む。配信パスは frontend/f02.html を基準として既存の ../pipeline/data/output/edogawa.json を解決する。
- 合成F02 Prototype (frontend/prototypes/f02-shelter-explore) は改変しない。新画面 frontend/f02.html は読み取り専用で、既存本番ナビにはまだ接続しない。
- Source of truth: RegionExport.meta.schema_version=0.9 / datasets[requirement_code=shelter_location]。既存GISやFrontendの評価ロジックを流用せず、表示専用の独立モデルに限定する。
- Dのrecordsの ID/name/address/facility_type/supported_disastersを保持する。supported_disasters は**D正規化レコードの値**であり、本人の避難先として適合・安全・開設中とは表示しない。D ScenarioやGSIとの名前照合・結合は**しない**。
- Dataset.evidence[] の source_name / publisher / license / published_at / fetched_at / HTTPS source_url を **Dataset全体の根拠・利用条件のD記録値**として表示する。値がない場合は未確認とし、B側でライセンスの推測はしない。個々のレコードと出典行の1対1照合を本UIが保証することはできない。公開日と取得日時、承認時点は混同しない。
- 施設座標は**有無のみ**を表示。数値があっても公式の範囲・入口・位置承認とはみなさず、地図/経路の目的地には渡さない。
- 見つからないDataset、取得/Parse/Contract失敗、Datasetのレコード0、検索一致0を分離し、合成fixtureにfallbackしない。
- 一覧の初期表示は最大50件。名称検索は全レコードに適用する。件数はこのDatasetの記録数であり自治体内の全避難施設数ではない。
- 新データにはネットワーク送信、ブラウザlocalStorage、個人入力、位置取得、外部API呼出なし（既存D JSONのsame-origin fetchのみ）。

## Implementation paths
- frontend/f02.html, frontend/f02.css
- frontend/src/f02-page.js: DOM textContent only, remote/unsafe URL notリンク化
- frontend/src/f02-shelter-reference.js: D v0.9のfail-closed表示モデル
- frontend/tests/f02-shelter-reference.test.js: 合成の契約テスト
- frontend/tests/f02-page-http-browser.test.cjs: 実HTTPのHTML/CSS/ESM/JSONをChromeで読み込むEnd-to-Endテスト。CIでは合成RegionExportのみ。環境変数F02_REAL_EXPORT_PATHを明示した場合はそのローカル生成JSONもlocalhostで配信して検証し、Chrome未導入ならFAIL
- frontend/scripts/check-f02-real-export.js: ローカル生成済みD JSONのB互換性チェック。欠損=NOT_RUN (exit 2)、不整合=CONSUMER_REJECTED (exit 1)、互換性=CONSUMER_COMPATIBLE (exit 0)。公式出典・施設単位検証・公開承認は含まない
- frontend/tests/f02-real-export-check.test.js: CLI判定・未確認ゲートの合成検証
- frontend/package.json / frontend/scripts/build-check.js: 新モジュール、CLIの構文チェック、F02ページ必須参照の検査

## Data and safety gates
- DのDataset records配列はJSON Schema上additionalProperties=trueだが、Consumerは実際に利用するフィールドの型を確認する。ID重複・region不一致・schema変更・不正座標は表示停止。
- 災害に対応する正式指定、開設現況、敷地/入口、収容可能人数、ペット/配慮事項、災害時通行可能性を**導出・表示しない**。
- Dataset.evidenceの存在は、施設別のA/C独立検証や公開権限の代替ではない。
- 公式資料の更新時点が不明なら「未確認」。未確認を「なし」「安全」「非公開」に読み替えない。
- 統合候補になるには、生成済み実D JSONでのHTTP読込、Chrome実操作、独立C検証・再配信条件、最新mainでのCI、Merge Captainによるスコープ審査が必要。Draft PRの通過だけでは公開許可なし。

## 江戸川区の公式出典と表示上のクレジット（2026-11-11確認）
- 公式地図データページ: https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html
- 公式CSV掲載先（D Adapter が参照する場所）: https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv
- 公式利用条件: https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/index.html
- 上記ページで「避難所・避難所補完施設」のCSV掲載と表示2.1日本（個別条件を除く）を確認。出典表示が必要。ただしファイルの生CSVの取得と公式行のC照合は、この検証環境から実施できなかった。
- D Adapterの `Evidence.license` は `CC BY 2.1 JP` と記録。Bはこれを引用表示するが、UI側で新たな利用許可や施設別の承認を推定しない。
- D正規化施設属性をHINANEXの画面で抽出・再構成している旨を同じ出典欄に表示する。元データの公式性とB画面の施設意味付けは別。
- 公式更新日は2025-12-11と記載されているが、初回公開日でも現在の施設開設日でもない。

## 生成済み実データを使うローカル受入手順（未実施・再現用）
前提: Python 3.12、D依存ライブラリ、Node.js 22、Chrome/Chromium（F02_BROWSER_BIN等で指定可能）。入力JSONはローカルの実行生成物であり、**GitHubへcommit/uploadしない**。

リポジトリrootから:
```bash
cd pipeline
python -m pip install -r requirements.txt
python run_all_workflows.py
python verify_d_mvp.py
python verify_a_handoff_integration.py
cd ..
node frontend/scripts/check-f02-real-export.js
```

構造・評価件数のCLI判定が `CONSUMER_COMPATIBLE`（exit 0）であることを確認したうえで、新画面を実HTTP Chromeで検証:
```bash
cd frontend
F02_REAL_EXPORT_PATH=../pipeline/data/output/edogawa.json node --test tests/f02-page-http-browser.test.cjs
```
PowerShellでは:
```powershell
cd frontend
$env:F02_REAL_EXPORT_PATH = (Resolve-Path ../pipeline/data/output/edogawa.json).Path
node --test tests/f02-page-http-browser.test.cjs
Remove-Item Env:F02_REAL_EXPORT_PATH
```

このChrome試験は別途指定された実JSONをlocalhostのみで配信する。画面読込、先頭最大50件、根拠表示、検索、未確認表記、JS例外、外部送信の有無を検証する。実JSONが欠損、Contract不整合、Chrome未導入なら実データ受入はPASSとしない。

**判定の分離:**
1. D生成成功・D Schema整合とCマニフェスト: D側の検証証跡が必要。
2. B `CONSUMER_COMPATIBLE` / `F02_REAL_EXPORT_HTTP`: 現物JSONをBが読み表示できたことだけ。
3. 行単位のC/公式一次資料照合、位置・入口・災害適合・開設情報: 別の独立検証が必要（本PRは未承認）。
4. クレジット・再配信条件の最終確認と公開範囲判断、Merge Captainのレビュー: 公開前の別ゲート。

## Verification status（2026-11-11 / PR #357 最新の検証）
- Source/contract review: root/frontend AGENTS、pipeline/contracts/region_export.schema.json、pipeline/docs/HANDOFF_B.md、既存B loader、GIS D adapterを確認。
- **Passed:** [GitHub Actions test run #42943642652](https://github.com/1kz-ma1/HINANEX/actions/runs/42943642652)、検証HEAD `d6d8e04c86f64548631f4c0453bf00e065d348e3`。required `test` SUCCESS。
- **Passed:** B `npm test` 88/88（失敗0・skip0）。既存F02合成Prototypeの実HTTP Chrome E2EもPASS。新F02 Consumerの実HTTP Chrome E2EもPASS（HTML/CSS/ESM/JSON各assetをHTTP配信、合成の正常/取得エラー/契約エラー/未収録/0件/検索0件、NFKC検索、元記号、出典、座標欠損、フォーカス、320/390/1440px横はみ出し、JS例外、外部通信）。
- **Passed:** B `npm run lint`、`npm run build`。E GIS等の追加Nodeテスト24/24 PASS。
- **Failed:** 現HEADで確認したCIテストではなし。
- **Not run:** ローカル機での手動操作、Safari/Android実機、物理タッチとスクリーンリーダー、**生成済み実D JSONを使うHTTP動作検証とCLI検証**、公式施設の行ごとのC受入と再配信/公開の最終審査。
- **Reason:** GitHubコネクタ経由の実装で本作業のローカルcheckoutと公式CSV実体がなく、`pipeline/data/output/edogawa.json` はGitHubに格納されていない生成成果物。今回のChromeテストは**合成データのみ**をlocalhostから配信した。Chromeの成功は実データ検証・公式位置承認・安全判定・公開許可ではない。
- Test repeat (frontend root): `node --test tests/f02-page-http-browser.test.cjs`（実Chrome必須、GitHub Actions CIではChrome未導入の場合FAIL、ローカル未導入ではSKIP）。
- Integration state: **Draft / merge: blocked**。実データ受入手順は用意したが実行していない。独立C検証と公式再配信/公開審査、実Dデータでの確認、Merge Captainレビュー前にmainへ統合しない。

## Next decision
このPRでは安全なB読み取り専用ページが成立するかを検証する。次のF05でのF01地域文脈引継ぎ、F07の終点承認、地図/GISへの統合を含めない。仕様の拡張は本IssueとDraft PRで人間のレビューを受ける。
