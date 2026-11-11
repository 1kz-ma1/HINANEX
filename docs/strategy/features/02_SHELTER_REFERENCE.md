# F02 避難施設の探索・詳細（単独で使える機能）

- 状態: **PARTIALLY_MERGED（独立の合成試作のみ）/ 残りはPROPOSED UX SPEC**。既存GISの検索/比較/本人選択はCURRENTだが、新たな完成UI・実RegionExport連携・人間C承認は未確定。
- 目標: 災害シミュレーションを動かさなくても、利用者が地域の**公的に掲載された避難施設情報**を調べ、何が未確認か把握できる。
- 既存資産: D `RegionExport` の `shelter_location` と `scenarios[]`、E `facility_list.js` / `facility_explore.js` / `facility_explore_ui.js`、江戸川の比較UX。既存機能の保守と、新しい完成UIの採用判断を混同しない。

## 単独体験

1. 地域を選び、検索・一覧で公的掲載施設/参考地点を探す。地域によりソースが異なれば統合検索で同じ施設と**自動名寄せしない**。
2. 施設名、公式記載住所/種別、掲載元、資料の版/対象災害の原記号を確認する。不明は空欄のまま示す（表示上は「未確認」）。
3. 施設ごとの詳細で「公式指定」「敷地・建物/入口」「災害別条件」「現在の開設」「参照点・正式な指定範囲」が別々の事実であることを理解できる。
4. 比較や本人選択は後段のオプション。**これだけで何かを選ばなくても完結**する。本人の選択はアプリによる推薦ではない。

## NEXT独立スライス案

- S-01: 地域・名前から公式掲載施設を検索し、座標なしも**一覧のまま**見られる。全件数/地図表示件数/座標欠損を区別。
- S-02: 施設詳細に**出典と属性別未確認理由**を優先配置。資料の更新/適用時点が不明なら明記。
- S-03: 公式掲載場所の位置精度は「参照点」/「正式指定範囲」等を別に説明。敷地境界・入口が未承認なら推測ピンを追加しない。
- S-04: 施設の比較UIは利用者テスト後に独立設計。既存2件比較UIは参考実装として維持、完成仕様への制約にしない。
- S-05: 原本の版や施設属性が変わった際、出典の差分と人間再確認要求を保持。自動承認しない。

## 誤認防止

- 避難施設の指定区分は地震/洪水/津波等で別。指定緊急避難場所、指定避難所、広域避難場所、救護所、物資拠点などを同じ役割へ自動統合しない。
- `supported_disasters` や公式raw列をUI独自の安全適合判定へ変換しない。Dの `CANDIDATE/EXCLUDED/UNKNOWN` を受け取る場合はDが既に付けた分類を**そのまま説明付きで表示**。
- Dの座標があることと、公式指定範囲の形状や避難時に使用可能な入口が確認済みなことは別。
- 最新の開設、収容、混雑、バリアフリー、道路や経路の安全性は公式の該当ソース/条件が無ければUNKNOWN。写真/非公式地図だけで上げない。

## 最小受入基準

- 地域内に座標無しの施設があっても一覧で名称/未確認を確認できる。施設未登録と通信障害を区別。
- 公式出典・元値・不明の理由を開ける。版が分からない属性を「最新」と言わない。
- 名称一致/近傍候補を別施設の公式登録として勝手に採用しない。
- UIは洪水ハザードモジュールをロードせずに機能する。スマホで検索/詳細が操作できる。
- 合成fixture/実データ/人間C承認/実機を検証報告で区別する。

## 連携予定

F01が渡した地域・ハザード文脈を将来F05で受け取っても、F02が勝手に施設適合性を計算しない。F02単体の参照情報はF05で選択肢に利用可能だが、施設/地点/路線の安全認定ではない。関連：[D洪水Scenario](../../../pipeline/docs/FLOOD_SCENARIO_CONTRACT.md)、[市川の個別検証 #333](https://github.com/1kz-ma1/HINANEX/issues/333)。

## 2026-11-11 F02 S-01/S-02 独立試作の実HTTPブラウザ検証

- 班員提出物の保管は [Draft PR #351](https://github.com/1kz-ma1/HINANEX/pull/351)。Issue #348 の**合成fixture限定**で、公式掲載施設を取得・承認する機能ではない。S-01/S-02の**表示体験のみ試作**した。旧GIS/RegionExport/F01/F05には未接続。
- 従来の提出者 `page.set_content` とNode合成テストに加え、**本物のChromeでHTML/CSS/JSをローカルHTTPから読み込む回帰**をBの必須CI `npm test`に追加。検索・一覧/詳細、選択元フォーカス復帰、UNKNOWN、検索0件と地域0件と疑似読込失敗の区別、320/390/1440px幅の表示、JavaScript例外/外部リクエストなしを検証。
- **初回実HTTP E2E PASS**: PR HEAD `b36b2ea6bf45d43c3f8b12ecc4508a151d2fb05b`、[GitHub Actions #42935557252](https://github.com/1kz-ma1/HINANEX/actions/runs/42935557252)のB Frontend testsに`F02_REAL_HTTP`ログあり。これは実URL読込成功であって、提出者のin-memory Chromium試験ではない。
- PRは2026-11-11に**最新mainへ同期（behind=0）**、テスト報告を追補した。最終HEADのCI結果とMerge Captainレビューは継続。**未統合Draft**で、本番での公開・実施設データ接続を認めるものではない。
- **NOT_RUN**: iOS/Android物理端末、Safari、音声読み上げ、実在公的出典の独立照合、位置承認、実データ/RegionExport契約へのマッピング・GIS/F05統合。以上は別ゲート。

## 2026-11-11 F02独立合成Prototype main統合の確定記録

- オーナーの指示により [PR #351](https://github.com/1kz-ma1/HINANEX/pull/351) をSquashでmainへ統合。**main SHA `e0d6f7a01644948acc8be787b727b22c926b2442`**。17ファイルは `frontend/prototypes/f02-shelter-explore/**` だけ。既存GIS・B本体・D RegionExport、共有Schema/Contract、災害データには変更なし。
- **PR最新HEAD `1dfe92cdc526666deb49eaefd9d7c2530d2dda44` の required `test` とChromeでの実HTTP E2E SUCCESS** ([#42936157773](https://github.com/1kz-ma1/HINANEX/actions/runs/42936157773))。main統合後もrequired `test` SUCCESS ([#42937034740](https://github.com/1kz-ma1/HINANEX/actions/runs/42937034740))。
- **DONE_IN_SCOPE**: すべて合成fixtureの施設一覧・詳細、位置未確認/資料未取得/UNKNOWN/0件/模擬読込失敗の表示と実Chrome HTTP検証、原本・テスト報告・提出画面の保管。
- **NOT DONE**: 公的に掲載された実施設の本体Consumer、F01・F05・GISへの接続、既存D Contractからの安全なマッピング、出典/適用条件のC受入、Safari/Android実機・読み上げ、人間による本番画面受入。**mainへの合成Prototype保管は本番の避難先案内の提供開始ではない**。
- 次のオーナーP0候補：B単独の**read-only RegionExport Consumer対応**を新PRで設計。既存 `frontend/src/region-export-loader.js` と `region-export-source.js` を再利用し、正式な属性が存在するものだけを表示。実在データの新しい「安全」「開設中」「指定災害」評価を作らない。C/GIS公開ゲートとは別に扱う。
