# F13｜F01洪水情報の根拠・未確認事項の可視化

- 作成日：2026-11-18
- 対象：`gis/gis/` にある既存F01「洪水情報だけを見る」
- 基準：main `ee935514d13fb0c20e1b025ced1f8b91d306a9f6`
- 状態：**Draft / 統合未承認 / 公開未承認**（2026-11-18統合前レビュー更新）
- 目的：2026-11-27実機QAの前に、確認済み事実と通信・掲載・現況の未確認事項を混同させない

## 既存仕様と差分

既存F01（PR #347／H-01・H-02）は、施設を選ばない洪水閲覧入口、公式タイルのON/OFF、地域選択、公式凡例、出典リンク、個別図面日付・掲載範囲の不明、Leafletの取得状態、過去の取得失敗警告を既に備えている。F13では新しいラスタ、警報API、判定器、施設選定画面を追加しない。

| 項目 | F01既存 | F13 |
| --- | --- | --- |
| 対象 | 想定最大規模・公式参考画像 | 同じ対象を「対象情報」として明示、現況と区別 |
| 出典 | 公式リンク・詳細欄 | 同じ根拠を一目で分かる出典欄に整理。既存公式リンク再利用 |
| 情報時点 | 個別の図面の日付は特定不能、配信開始日は公式詳細欄 | 配信開始2020-03-17と個別図面の作成・改訂日不明を並記 |
| 未確認事項 | 対象全域と最新性の注意 | 対象外判定、未取得、通信失敗、現在の警報、地域掲載範囲を区別 |
| 状態表示 | ON/OFF・取得中・部分エラー・履歴通知 | 状態名と根拠限界を明示、地域変更時の古い状態の流用を防止 |
| 操作 | 地域select、洪水checkbox、Escape、外側タップ | 既存操作のまま。読み上げのatomic statusと狭幅の情報欄を改善 |

## 表示規則・根拠

- **対象情報**：既存の国土交通省・国土地理院ハザードマップポータルサイトの洪水浸水想定区域（想定最大規模）画像。実際の現在警報・浸水予測ではない。
- **情報時点**：2020-03-17は画像タイルの配信開始日であり、自治体・個別河川の元図面の作成・改訂日とは別。
- **地域・地点が対象外かどうか**：既存資料だけでは**未確認**。404、`tileerror`、無着色、画像未取得から対象外・非浸水を確定しない。
- **非表示**：既存`officialFlood.checked=false`。現時点でレイヤーの取得を要求しない表示設定であり「浸水なし」ではない。
- **地域切替後**：以前の表示範囲に紐付く`partial`等の状態を新地域へ引き継がず、取得状態を未確認として案内。`MutationObserver`の`loading`通知だけでは新旧リクエストを相関できないので、通知だけでは保護を解除しない。**明示的な洪水レイヤーOFF→ON**の操作後にだけ通常の取得状態表示へ戻す。地域選択だけで地図viewportや新しいタイル取得が必ず変わるわけではない。
- **取得中**：既存`mapFloodRefreshStatus.dataset.state=loading`。未着色=浸水なしにはしない。
- **画像取得失敗検知**：既存`dataset.state=partial`。HTTP通信失敗・配信対象外・ブラウザ制限などの原因は、`tileerror`だけでは識別できない。
- **以前の閲覧範囲の失敗**：既存`mapRasterBanner.dataset.partial`と`externalFloodTileNotice`は過去履歴として扱い、現在の地域に確定的に結び付けない。
- **取得状態未確認**：ONかつ有効な現在バッチ状態がない場合。取得完了・全域掲載と断定しない。
- **地域コード未登録**：過去の地域結果を表示しない。登録外地域の対応可否は推測しない。

追加データ、地理座標、数値浸水深、時点の推定、ユーザーデータの保存、API、GPS、経路や施設安全評価はない。D RegionExportと共有Contract/Schemaには触れない。

## 検証経路

1. Node：`node gis/tests/hazard_information.test.js`。既存E requiredゲートの`map_controller.test.js`から呼び出し、F01/F13状態・対象/出典/時点/未確認・地域切替時の古い結果除外を合成DOMで確認。
2. HTTP Chrome：既存`gis/tests/demo_20261022_browser_smoke.js`から`hazard_information_browser.js`を実行。既存の本物のGIS `/gis/gis/`、Playwright Chromium、Leaflet 1.9.4を使い、**320/390/1440px**で情報欄の収まり、native Tab、Escape、公式URL、ON/OFFを確認。ラスタ外部取得はテスト内で遮断するため、公式タイルの可用性・配信カバレッジは評価しない。
3. Required `test`、GIS browser acceptance の **exact HEAD**、差分スコープ、lint等をPR作成後に確認。成功・失敗・未実行を分ける。
4. 2026-11-27実機QA：物理スマートフォンのタップ、スクロール、OS読み上げ、幅、現行の警報への誤読防止、地域切替時の地図と本文を人間が検証。自動Chromeと別に記録する。

## 公開・依存関係・競合

- `deploy/build_staging.py` は `gis/gis/**` を静的配布先の `/gis/gis/` にコピーする。**このF13の実装は既存の公開GISに直接影響し得る**ため、Draft PR作成やNode/Chrome PASSだけでは公開承認としない。mainへのmerge、Render LIVEデプロイ・公開判断は人間に委ねる。
- F04 S1 #430／S2 #432：`gis/prototypes/f04-synthetic-timeline/**`は変更せず。**`gis/tests/map_controller.test.js`のみ同名ファイルを使用**するため、両PRの統合順が決まったら差分とrequired testを再確認する。
- F07独立Prototype、F02/F05、D Contract/Schema、`pipeline/**`、`frontend/**`、`deploy/**`、`.github/**`は変更しない。
- 実災害時の安全・最新警報、自治体原図面の独立照合、外部URLの現在可用性、実端末・Safari・VoiceOver/TalkBack、Render LIVEの公開確認は別ゲート。現時点で統合・一般公開を承認しない。

## 参照

- `gis/docs/F01_HAZARD_INDEPENDENT_ENTRY_20261104.md`
- `gis/docs/F01_OFFICIAL_FLOOD_RASTER_PROVENANCE_20261104.md`
- 既存公式出典：<https://disaportal.gsi.go.jp/hazardmap/copyright/opendata.html>

## 2026-11-18 統合前レビュー：キャッシュ・非同期境界

- F13で内容が変わった静的ファイルだけ、`gis/gis/index.html`の識別子を変更する。`js/hazard_information.js?v=f13-evidence-20261118-v1`および`css/map_first.css?v=f13-evidence-20261118-v1`。そのほかの資材に手を触れない。
- ソース内にRender向け`_headers`や`Cache-Control`ポリシーは定義されておらず、実際のRenderレスポンスヘッダーとCDNキャッシュTTLは**未確認**。更新したquery識別子で旧URLキャッシュを分離するが、ブラウザ内に古いHTMLが保持される可能性・CDNキャッシュ設定の独立確認は残る。
- 単独の`region`変更は地域ごとの新しい公的洪水ラスタ取得を**保証しない**。GISの地図viewportは選択地域と独立の場合がある。現行`mapFloodRefreshStatus`には地域ID・request ID・真正なHTTP完了証拠がない。**状態は画像読込イベントの観測結果であって、地域の配信完了証明ではない**。
- **旧A→B切替**：`regionStatusStale`を維持し、旧`partial`や後着`loading`をB地域の結果にしない。`MutationObserver`は同期表示にだけ利用。連続切替・同一ONイベント・OFF時・再開時をNodeで検証。
- **明示的OFF→ON後**：既存Leafletレイヤー再追加による新しい取得試行に切り替える。ただし、`tileerror`にrequestIDが無いため、厳密な「Bの画像だけ」「Aの全非同期イベントを除外」までは保証できない。この不足を根拠なく解決したとは扱わず、UIは現在の警報・カバレッジ・地域別取得成功を一切主張しない。
- 仕様拡張して地域・要求単位の通信成功を表示したくなった場合には、既存Leafletのバッチ識別・タイル要求の世代追跡を別の設計レビューで行う。F13の統合前変更では実装しない。

## Render／既存GISの公開影響と回復

- `deploy/README.md`の記載：Render Static Siteは`main`をAuto Deployして`deploy/dist`から公開。ビルドは`python deploy/build_staging.py`を使い、その中で`gis/gis/**`が公開ディレクトリ`/gis/gis/`へコピーされる。
- **mainへ統合すると、その後に自動デプロイで既存GIS全体が変わる可能性がある**。Draft・CI成功とRender LIVE反映・一般公開許可は別。F13は専用の非公開試作ではなく既存GISへの直接変更。
- 想定リスク：HTMLと旧JS/CSSの不整合、CDNの旧HTML保持、JavaScriptのランタイム例外、画面幅320pxでの横はみ出し、既存のF01/F06リンク・地図操作の退行、外部GSI画像の通信エラー。GSIエラーは実災害の安全性を意味しない。
- 影響低減：キャッシュ識別子を更新、既存テストを追従、差分`gis/**`だけ、必須CIと実HTTP Chromiumの新HEAD検証。**公開前**にMerge Captainがステージングの現行SHA・Auto Deploy設定・HTTPレスポンスヘッダー・ロールバック手順を確認し、公開後に`/gis/gis/`からassetの200をDevTools Networkで確認。
- Renderダッシュボードの実設定・CDNキャッシュヘッダーとRender LIVE SHA／404は、この統合前GitHubレビューでは未確認。権限・ワークスペースが確定した人間が確認する。失敗時にはRender上の直前の正常デプロイへ復旧し、古いHTML/JS/CSS組合せを残さないことを確認する。**本PRからデプロイ・ロールバックを実行しない**。

## 2026-11-27 JST｜物理端末QA手順（NOT_RUN）

テスト場所は人間が明示したステージングまたは隔離した実機受入URL。実災害時の避難判断に利用しない。Chrome自動テストの成功を実機PASSとして流用しない。

1. **開始前**：QA対象HEAD SHAと配信`_staging.json`／Render Deploy SHAを記録。ネットワークで`/gis/gis/`がHTTP 200、`hazard_information.js?v=f13-evidence-20261118-v1`と`map_first.css?v=f13-evidence-20261118-v1`が200、同じ新バージョンで返ることを確認。Console error 0を目標に証跡を採る。旧HTMLが残った場合はFAIL。
2. **画面寸法**：320、390、1440px相当を記録。GISから「災害情報」→「洪水情報だけを見る」へ移動し、パネルが画面外へはみ出さず、上下スクロールで最下部の公式リンクと閉じるまで到達できること。左右スクロール不要、タップ対象・背景とのコントラストを確認。
3. **根拠**：対象・出典・情報時点・個別版不明・地域全域未確認・対象外の未確認事項を読み上げずとも視認可能であること。配信開始日を元図面改訂日と勘違いしない。公式URLがリンク先として確認できること。
4. **状態**：ON/OFF、取得中、タイル失敗時、過去エラー表示を区別。画像の無着色・未取得・HTTPエラーから安全・浸水なし・対象外を示さない。公式画像の取得可否はNetworkのHTTPやブロック理由として別記録。
5. **地域切替**：Aでエラー→B→A→Bを短時間に反復。直後には「地域切替後」が維持され、古い`partial`や遅延`loading`を現在の地域の取得成功として表示しないこと。OFF→ONで再取得試行し、地図の実viewportの変化と取得URLを別々に記録。地域選択だけでは新規取得されないケースも記録し、成功を補完しない。
6. **アクセシビリティ**：タップ/タブ/Enter/Space、Escでの閉鎖と表示メニューへのフォーカス復帰、OS読み上げ（iOS VoiceOver、Android TalkBack）で選択ラベル・状態通知・公式リンクの順序と重複読み上げを確認。実機がないOSは`NOT_RUN`。
7. **退行・公開**：他の「災害情報」メニューとF06公式リンク、地図の移動/ズーム、施設表示、非公開F04/F07への導線が増えていないこと、既存GIS URLの可用性を確認。Console/HARの秘密情報は添付しない。
8. **結果**：環境、OS/ブラウザ、幅、SHA、時刻、手順別PASS/FAIL/NOT_RUN、実スクリーンリーダー使用有無、出典・通信例外、画面記録を残す。1件でも安全性につながる誤認や既存GIS不表示があれば公開HOLD。

**現時点の実機QA = NOT_RUN／予定日 = 2026-11-27 JST。**