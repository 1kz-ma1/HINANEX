# F13｜F01洪水情報の根拠・未確認事項の可視化

- 作成日：2026-11-18
- 対象：`gis/gis/` にある既存F01「洪水情報だけを見る」
- 基準：main `ee935514d13fb0c20e1b025ced1f8b91d306a9f6`
- 状態：**Draft / 統合未承認 / 公開未承認**
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
- **地域切替後**：以前の表示範囲に紐付く`partial`等の表示結果を新地域の結果として引き継がず、取得状態を未確認として案内。新規loading通知、または明示的な洪水レイヤー再有効化で現在の表示範囲の取得状態へ移る。地域選択だけでは地図viewportや掲載範囲は確定しない。
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
