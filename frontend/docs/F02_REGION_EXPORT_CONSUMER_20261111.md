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

## Verification status（2026-11-11 / PR #357）
- **Passed:** [GitHub Actions run #42945680354](https://github.com/1kz-ma1/HINANEX/actions/runs/42945680354) at implementation HEAD `3ff193e3cf48021464f4e7f7139c7e7ffbde5093`: required `test` SUCCESS。
- **Passed:** B `npm test` **94/94**、失敗0・skip0。合成データでの既存F02 Prototype実HTTP Chrome E2E、今回のF02 Consumer実HTTP Chrome E2E、出典ライセンス/未確認表示、CLI判定を自動検証。
- **Passed:** B `npm run lint`、`npm run build`、関連Node追加テスト24/24。D Adapterと実データ生成元URL、公式公開ページの掲載・CC BY 2.1 JP原則を資料上で照合（出典は上記参照）。
- **Failed:** 最新の実装HEAD CIテストでは0。
- **Not run:** **生成済み実D JSONを使うCLI/HTTP Chrome動作検証**、公式CSV実バイトとCマニフェストの独立照合、施設行ごとのC受入、Safari/Android実機、物理タッチ/読み上げ、個別再配信・公開承認の最終審査。
- **Reason:** `pipeline/data/output/edogawa.json` はGit管理外の生成物で、現実のファイルは本実行環境から入手・生成できなかった。公式公開HTMLの一次資料は確認できたがCSVは取得できなかった。E側`gis/tests/fixtures/edogawa.json` は**合成contract fixture**で実Dデータではない。
- **Verification commands:** `node frontend/scripts/check-f02-real-export.js` と、frontend directoryで `F02_REAL_EXPORT_PATH=../pipeline/data/output/edogawa.json node --test tests/f02-page-http-browser.test.cjs`（詳細は前節）。CLI成功はB構造互換のみ・位置/指定/開設/災害適合の承認ではない。
- **Integration state:** **Draft / merge: blocked**。実データ受入手順は実装済み。行単位の独立C検証、実ファイルでの動作確認、公開審査、Merge Captainレビュー前にmainへ統合しない。

## Mac実行による実データ受入結果（2026-11-11・利用者提出ログ）
- 対象: ローカル `pipeline/data/output/edogawa.json`。生成日時 `2026-11-11T02:54:52.688619Z` はD生成時刻であり、自治体の公式データの公開日・更新日ではない。
- **Passed（利用者報告）:** `F02_REAL_EXPORT_HTTP: ... structural display PASS`、実Chrome HTTPでローカルD JSONを読み込んで画面表示し、Node試験1/1・失敗0。
- **Passed（利用者報告）:** `node frontend/scripts/check-f02-real-export.js` → `CONSUMER_COMPATIBLE`。RegionExport schema 0.9、江戸川区レコード152件、座標欠損0件、Dataset evidence1件、HTTPS出典URL1件、D記録license `CC BY 2.1 JP` を確認。152件は現在のD Dataset掲載数であり地域の全避難施設数ではない。
- **Evidence limitation:** 結果は利用者のMac標準出力をチャットで受領したもの。原JSON・公式CSV・実行環境のログを独立取得・照合していない。報告中の `input_provenance=NOT_INDEPENDENTLY_VERIFIED`、`official_row_review=NOT_RUN`、`publication_approval=NOT_GRANTED` を維持。
- **Not run / missing evidence:** `python verify_d_mvp.py` / `python verify_a_handoff_integration.py` の成功ログ未提出、正式Cによる原CSV行/施設ID/位置や指定の独立検証・最新性確認、個別再配信/公開審査、実端末のアクセシビリティ。
- **Decision:** Bの「実ファイル構造互換＋Chrome表示」ゲートは**PASS（利用者提出ログ）**。ただしD/C・一次資料・公開ゲートが未充足のためPR #357はDraft / `merge: blocked`継続。

## Mac検証追補（2026-11-13・利用者提出ログ）
- **Passed（利用者報告）:** `cd pipeline && python verify_d_mvp.py` → `HINANEX v1.0-D-MVP: READY`、RegionExport contract schema `0.9`、edogawa/niigata/nagoya 3地域のB/C contracts、manifest、JSON Schema が存在し整合。
- **Passed（利用者報告）:** `python verify_a_handoff_integration.py` → `A-D Integration: READY`、Formal requirement `shelter_location`。
- **D検証出力:** 江戸川区 152 records / D evidence 1 / Shelter Discovery `FULL` / gaps 0 / recommendations 0、新潟市 566 / 1 / `FULL` / 0 / 0、名古屋市 1602 / 16 / `BLOCKED` / 1 / 1。
- **Meaning boundary:** Capability `FULL` は位置ベースのShelter Discovery条件であり、災害適合、施設の安全性、開設、避難誘導の承認ではない。名古屋市の `BLOCKED` も自治体の避難所不存在を意味しない。
- **Still not formalized in D:** `shelter_disaster_compatibility`、`shelter_accessibility`、`shelter_capacity`、flood hazard/inundation depth。
- **B受入との結合判定:** 2026-11-11のユーザー提出 `CONSUMER_COMPATIBLE` / `F02_REAL_EXPORT_HTTP ... PASS` に加え、D-MVP/A-D検証成功ログが得られたため、**D契約生成/連携とF02読取・表示の技術ゲートは利用者提出ログ上PASS**。
- **Remaining gates:** 公式CSVの実バイトと normalized 152行の独立C突合、Source/ライセンス条件・更新日の最終確認、行単位の位置/指定/入口/災害適合/開設の承認、一般公開範囲の最終審査、Safari/Android/読み上げ等の追加検証。出典・座標・施設記録を安全判断に転用しない。
- **Evidence provenance:** 上記はユーザーがMacの標準出力として提出したログ。モデルはその実行環境/Rawファイルを直接取得していない。従来の `official_row_review=NOT_RUN`、`publication_approval=NOT_GRANTED`、`input_provenance=NOT_INDEPENDENTLY_VERIFIED` は変更しない。
- **Merge decision:** PR #357 はF02 read-only consumerの実装・D/B技術ゲート検証済み。ただし災害データの独立証拠・公開の承認が未解決のため **Draft / `merge: blocked`** を維持し、mainには統合しない。

## Next decision
このPRでは安全なB読み取り専用ページが成立するかを検証する。次のF05でのF01地域文脈引継ぎ、F07の終点承認、地図/GISへの統合を含めない。仕様の拡張は本IssueとDraft PRで人間のレビューを受ける。

## 2026-11-13 公開範囲の予備審査とクレジット修正（C一次資料レビュー連携）
- 正本: C `validation/docs/F02_EDOGAWA_PUBLICATION_GATE_20261113.md`（Draft PR #365）。対象は江戸川区の1地域 read-only B Consumerのみ。
- 江戸川区の公式オープンデータトップ（`https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/index.html`）は**個別の例外を除き**CC BY 2.1 JPを採用。公式地図データページ（`https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html`）には「避難所・避難所補完施設」CSV・表更新日2025-12-11・CC-BY表示を確認。
- 区の利用規約PDF（`https://www.city.edogawa.tokyo.jp/documents/10685/20150914_kiyaku.pdf`）では商用利用可・出典/URL・**編集加工の明示**・区が作成したと装うことの禁止・第三者権利・免責が示される。現在のBのDatasetクレジットだけを持ってライセンス承認や本番公開判断とはしない。
- Bの出典欄を小規模修正: 出典Dataset名・発行元とHINANEXの加工を明記、非公式の表示である旨を明記、**Dの`license`値が正確に `CC BY 2.1 JP` の場合のみ**条項へのHTTPSリンク `https://creativecommons.org/licenses/by/2.1/jp/`を表示。欠損・別値の場合は`ライセンスURL: 未確認`を保持。未知の文字列からライセンスURLや利用許可を生成しない。
- 新Chrome E2Eで合成のCC BY表示／欠損・別ライセンス／出典・加工表示／rel noopenerを確認。CI [Actions #43346598946](https://github.com/1kz-ma1/HINANEX/actions/runs/43346598946) at code HEAD `8edd7000a79798c8618b328fde1f385a0b77e7c2`: required `test` SUCCESS、B `94/94` PASS、Node関連 `24/24` PASS。
- **C Source→Export全行の技術整合は利用者Mac報告でPASS**: 江戸川区CSVのSHA256 `64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea`、152レコード/不一致0（C PR #365 / Issue #364）。施設の公式指定や実敷地位置・入口/災害適合/安全・開設の承認ではない。
- **判定:** 内部の読み取り専用参考表示を維持。一般ナビ・GIS・避難先推薦・外部公開への自動移行はなし。個別権利・ライセンス条件の正式レビュー、施設意味の個別根拠、公開範囲・運用・アクセシビリティの人間判断はHOLD。B PR #357はDraft / merge: blockedを維持。

## 2026-11-13 アクセシビリティ・誤誘導防止（開発環境スコープ）

- **追加のB変更:** `frontend/f02.html` の検索欄に `aria-controls=results`・`aria-describedby=record-count`、一覧に `role=group` とアクセス可能な一覧名を付与。静的CSVでは分からない現在の開設・混雑情報について、[江戸川区の公式防災アプリ・ポータル案内](https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/oshirase/bousaiapuri.html) への**ユーザーが選択する場合のみ開く**リンクを表示。表示時に外部へ自動通信しない。
- **施設詳細:** Dの `facility_type` は名称「（補完施設）」に基づく内部分類であり、公式の法的指定ではないと明示。元CSVから正規化/ExportへのC行変換の整合性が確認されても、個別の敷地・入口・法的指定・災害適合/開設承認ではないことを明示。RegionExportの属性は補完・変更しない。
- **追加E2E（合成データ）:** headless実HTTP Chromeで検索欄/一覧/公式リンクのアクセシビリティツリー上の名前、検索欄からTabで最初の施設へ移動、Enterで詳細選択し見出しへフォーカス移動、誤誘導防止文言、リンクのrel属性を検証。テストは公式の施設安全性を評価しない。
- **現物Mac実機（人間の手動確認・未実施）:** SafariとVoiceOverで①ページ先頭の「検証中・参考情報」が読める、②検索欄のラベルと件数が分かる、③Tab→Enterで施設を選択できる、④詳細の見出し/未確認文言/名称由来の施設分類に到達する、⑤外部の公式案内リンクが区の公式情報へ遷移する、⑥320 CSS px相当/表示文字拡大でも主要操作を失わない、を記録する。iPhone VoiceOver・Android TalkBackは別の実機/担当レビューが必要。
- **公開/安全境界:** 静的CSVに現在の開設状態を混ぜず、HINANEXは避難先推薦・ルート案内を行わない。A正式出典利用条件は [Issue #366](https://github.com/1kz-ma1/HINANEX/issues/366) / A Draft PR #367（AI一次資料予備レビュー）で**人間判断を未承認**。一般ナビ/外部公開、GIS接続はNO-GO。

## Mac Safari/VoiceOver向けローカル限定プレビュー（非公開、2026-11-13）

`frontend/scripts/serve-f02-preview.cjs` は、実D `edogawa.json` にBの `CONSUMER_COMPATIBLE` 構造検査を実施した後、**127.0.0.1:自動割当ポート**にだけサーバーを起動する。次の7パス以外は応答させない: `/frontend/f02.html`, `/frontend/f02.css`, F02/region-export-loader/sourceのJS（4ファイル）、`/pipeline/data/output/edogawa.json`。リポジトリの原CSV、正規化JSON、`.git`、一般 `index.html`、他地域JSON、任意のURLパスは404。Host検査でDNSリバインディングを制限。no-store・no-referrer・nosniff・CSPで外部自動接続を抑制し、Gitデータ全体を配信しない。

**Macコマンド（現在のcloneを更新可能な場合）**

```bash
cd "$HOME/HINANEX-f02"
git status --short
git pull --ff-only origin feature/b-f02-region-export-consumer-20261111
cd frontend
npm run preview:f02
```

初期ゲート失敗時は `F02_PREVIEW_BLOCKED` を出してサーバーを起動しない。成功すると `F02_PREVIEW_LOCAL_ONLY: http://127.0.0.1:<port>/frontend/f02.html` と出力する。表示されたURLを**MacのSafariで開く**。テスト完了時はサーバーを実行中のターミナルでCtrl+C。

**手動確認を依頼する対象（AIがPASSを代行記録しない）**
1. Safari で読み込み、ページ先頭の「F02 検証中・参考情報」と公式開設情報へのリンクの区別を視認。
2. キーボードTab/Enterで検索欄→施設一覧ボタン→詳細見出しへ移動。選択した後の施設ID、D名称由来分類、未確認の説明を確認。
3. Command+F5でVoiceOverを有効化し、検索欄の名前「施設名で検索」、一覧の名前「施設記録一覧」、状態、件数と施設選択/詳細が読めることを確認。設定によりFnキーが必要な場合あり。操作後Command+F5でOFF。
4. Safariの表示を200%程度に拡大し、狭い幅でも検索・出典リンク・詳細表示が水平スクロールなしで理解・操作できるかを確認。
5. 通信失敗/契約不一致・実データ元資料の新しさや現在の開設状況を保証できないことを明示。現況情報は江戸川区の公式防災アプリ・ポータル案内を利用する。

**テスト可能な証拠:** Node合成HTTP回帰ではallowlisted配信、raw/.git非公開、Host制限、CSP、B元HTML/JSON配信を検証する。Chrome CDPでARIA/Tab/Enterを検証する。**これらはSafari/VoiceOver実機テストの代替にならない**。また、Macのlocalhostは配信/公開承認を意味しない。一般公開・main統合・GIS避難先誘導は引き続きHOLD。

## 2026-11-13 施設選択によるスクロール最上部ジャンプ修正

- **報告:** Mac SafariのローカルF02プレビューで施設を選択するたびにページが最上部付近へ戻り、連続閲覧が困難。
- **原因コード:** `renderList()`で選択時に一覧の全ボタンを再生成し、`detailTitle.focus()`がフォーカス先へスクロールするため、閲覧中の位置が失われる。
- **修正:** 選択時には既存の施設ボタンDOMを破棄しない。該当ボタンの`aria-pressed`のみ更新し詳細を再描画、見出しへ`focus({preventScroll:true})`でフォーカスする。デスクトップ幅では詳細パネルを `position: sticky` として一覧の閲覧位置で見えるようにする。データの契約/元CSV/安全の意味は変更しない。
- **回帰テスト:** 合成50件の長い一覧でスクロール後の施設選択を2回実施し、`scrollY`が変化せず、ボタンDOM、ARIAの選択状態、見出しフォーカス、右詳細表示が保たれることをChrome HTTP E2Eで確認する。通常の検索・キーボードEnter操作の既存テストも維持。
- **実機再確認待ち:** Mac Safariでページ中ほどの施設を連続クリックし、スクロール位置が維持されるか。狭い画面でも勝手に最上部へ戻らないか。VoiceOverの読み上げやフォーカス順序は別途人間の評価が必要で、自動Chrome成功を実機PASSへ代用しない。
- **公開/統合判定:** 非公開read-only・Draft / `merge: blocked`は維持。施設開設/指定/安全/経路/許諾判断を変更しない。
