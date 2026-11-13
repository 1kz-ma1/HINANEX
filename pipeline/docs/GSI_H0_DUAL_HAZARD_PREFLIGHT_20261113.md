# H0 / GSI洪水・土砂災害の公式GeoJSON原本を取り違えない事前検査

- 日付：2026-11-13（JST）
- 状態：**D内部のoffline・合成検証スライス**。公式タイルの独立再取得・原本真正性・C最終照合・E地図への統合・公開は **NOT RUN / NOT APPROVED**
- 担当：オーナー基盤トラック（Issue #360）。koutaの洪水体験PR #371、班員の江戸川区利用条件Issue #366とは独立
- 追跡：#305 Stream H0、#89 地域×災害2×2検証、C 市川土砂 #316、A/Cの出典・改版ゲート

## 1. 一次資料と観測した確定情報

| 正式資料 | URL | 確認できる範囲 |
| --- | --- | --- |
| 国土地理院「地理院タイル一覧」 | https://maps.gsi.go.jp/help/use.html | 指定緊急避難場所のGeoJSONレイヤは **zoom 10**。洪水は `skhb01`／`disaster1`、崖崩れ・土石流・地滑りは `skhb02`／`disaster2`。対応する指定は属性値`1`。共通属性 `name/address/remarks` |
| 国土地理院「指定緊急避難場所・指定避難所データ」 | https://web1.gsi.go.jp/bousaichiri/hinanbasho.html | **指定緊急避難場所と指定避難所は異なる**。公開には市町村の登録・公開同意という範囲制約がある |
| 国土地理院「ご利用上の注意」 | https://hinanmap.gsi.go.jp/index.html | 更新/未掲載の可能性がある。自治体の最新指定を必ず確認する。第三者への再提供時は区分・注意を正確に伝える |
| 国土地理院「市町村別公開日・更新日一覧」 | https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html | 一覧内の更新日は国土地理院DB更新であり、市町村長の個別指定日ではない |
| HINANEX既存市川土砂調査 #316 | https://github.com/1kz-ma1/HINANEX/pull/316 | 以前の `skhb02/10/909/403` では **800件（タイル全体）・住所に「市川市」を含む29件**の記録があり、AI転記との一致28件・住所差1件。独立の真正性・現在の同一施設・安全の承認なし。**今回の実タイル新規取得結果ではない** |

### ソース仕様の境界

- 洪水URL：`https://cyberjapandata.gsi.go.jp/xyz/skhb01/{z}/{x}/{y}.geojson`
- 土砂URL：`https://cyberjapandata.gsi.go.jp/xyz/skhb02/{z}/{x}/{y}.geojson`
- 同じ `z/x/y` でも異なる **災害別の原本**。異なるHazardのHTTPS原本SHA・C検証を流用しない。
- これらは「市町村の全指定避難先リスト」ではなく、地理院タイル仕様の **タイル内記録**。タイルの境界と行政界は一致しない。住所の接頭辞一致は自治体所属/施設同一性の独立認定ではない。
- `disaster2=1` はGSI公式データ上の指定に関する原属性で、現在の開設、建物/敷地/入口、浸水・土砂の現況、安全な経路・推奨先を保証しない。
- 上記規約に基づくデータの**再配信可否と条件**は別途人間レビューが必要。H0事前検査で公開許可を出さない。

## 2. 実装した最小機能

`pipeline/src/hinanex/gsi_hazard_preflight.py` は **ローカルraw bytesだけ**を読むD側事前検査。取得や公開、正規化/施設joinは行わない。

1. `hazard=flood|landslide` を明示指定。選択したレイヤー `skhb01|skhb02` と `disaster1|disaster2` の対応は固定。想定外hazard、別レイヤーURL、HTTP、外部host、URLクエリ/fragment、非z10、x/y範囲外・非正規の先頭ゼロは拒否。
2. rawを最大20MiBに制限。実行者が渡すSHA256をbytesと比較し、取得時刻をUTC形式で必須入力。SHA一致は**ローカルファイルの自己照合であり、GSIからのHTTPS取得の独立証明ではない**。
3. UTF-8 GeoJSON `FeatureCollection` の全Featureを検査。重複JSONキーやJSON外数値を拒否。対象の `disasterN` が厳密に整数`1`、名前/任意住所/備考の型、Point座標の型/範囲を照合。**別災害の値を推測で解釈しない**。
4. 正常時も返すのは **メタデータのみ**（raw SHA、タイルID、元URL、全Feature件数、未承認ゲート）。緯度経度・施設名・個々のID・表示/公開可能なrecordは生成しない。
5. 明示的な空 `features=[]` は `H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF`、ファイル未取得/HTMLエラー/JSON不正は例外HOLD。空＝自治体に施設なしではない。
6. 正常な非空構造でも `H0_LOCAL_STRUCTURE_ONLY`：`LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED`、`official_https_byte_replay=NOT_RUN`、`independent_c_acceptance=NOT_GRANTED`、`publication_approval=NOT_GRANTED`。

**重要な限界：** 別のhazardファイルを手元で改ざんして全属性を揃えても、単に自己申告SHAが一致するだけではそのURLから取得した証明にならない。このため本ツールのレポートを **C-accepted**、`REFERENCE_ONLY`、地図表示の許可に昇格させない。公式サイトの最新版確認・HTTPS byte replay・施設ID/原本/公表時点の独立C監査が次の必要条件。

## 3. 実行例（公式データを手動取得・保管してから）

```bash
cd pipeline
python -m unittest discover -s tests -p "test_gsi_hazard_preflight.py" -v
python -m unittest discover -s tests -v

# 例示用: 実際に独立取得・保存したrawのpath / SHA / UTC取得時刻を使う。
# GSI公式タイルURLとraw bytesが同じソース・同じ時点であることは、
# このコマンドではまだ証明できない。
python -m src.hinanex.gsi_hazard_preflight \
  --raw "/path/outside-repo/skhb02-10-909-403.geojson" \
  --source-url "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson" \
  --hazard landslide \
  --expected-sha256 "<実測rawの64桁SHA256>" \
  --retrieved-at-utc "<実際の取得時刻UTC>" \
  --report "/path/outside-repo/H0_skhb02_summary.json"
```

**受入の意味を誤らない:** このパス `909/403` は既存 #316 の**過去の検証タイル例**であり、現時点でのHTTP取得成功・施設数・対象自治体の完全性を保証しない。ファイル実物、厳密なURL、正しいraw SHA、UTCを記録できない場合は `NOT_RUN` にとどめる。

## 4. 合成テスト・変更範囲

- `pipeline/tests/test_gsi_hazard_preflight.py`：洪水/土砂両種、別災害混入、改変SHA、不正URL/範囲/タイムゾーン、無効JSON/重複キー/非JSON数値、markerのbool/string/0、名前/Point欠損、21件の合成テスト。
- `pipeline/**`のみ。既存 `flood_site_reference.py`、`run_verified_flood_site_reference.py`、`RegionExport v0.9`、E/GIS/B/F05、Renderへの変更なし。
- 新しい正式Adapter、地域×災害2×2の採用、公式データのライブ取得や全国分の先読み、公開ファイル生成はしない。
- 実機QA分類：`NOT_REQUIRED`（Pythonのoffline検査のみ）。**新しい地図画面**の実装時は Issue #372 にDQA登録。
- D単体・統合CIのPASSはGSIの現在の原本取得やC受入の代替にならない。

## 5. 次のゲートと後続判断

1. **H0 real source feasibility**: GSIの `skhb02` の指定tileを現時点の公式HTTPSから独立取得し、HTTPステータス/最終URL/取得UTC/bytes/SHA256を保存。データが存在しない場合、HTTP障害/未収録/空Featureを区別。rawはGitへcommitしない。公式条件・一覧更新日・利用条件のAレビューは別。
2. **C independent raw verification**: HTTPS byte replay・タイル範囲/属性・feature index・改版・スコープ・対象災害属性の独立検証と、人間の指定/同一性判断を厳格に分離。既存 #316 は過去資料であり、この時点の最新原本証明に流用しない。
3. **R0 second region**: `skhb01`・`skhb02`双方の公式取得が可能な地理的に離れた地域を**確認後に**選ぶ。行政単位に含まれるrecordとタイル単位の件数は混ぜない。
4. **D/E integration decision**: GSI原本と既存自治体 `shelter_location` を自動名称/座標joinしない。Cの受入と共有契約設計を共同確認後、Eに「出典付き参考地点」だけの別レイヤーを検討。開設・安全・ルート・最適化は常に別ゲート。

**Gate判定：H0合成・構造検査の実装は進めるが、`skhb02`地域対応・実データ承認・一般公開はすべてHOLD。**

## 6. 2026-11-13 公式HTTPS実取得トライと安全なローカル取得ツール

**2026-11-13の実行環境からの直接取得はDNS障害で失敗**した。`https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson` への `curl` は `Could not resolve host: cyberjapandata.gsi.go.jp` （exit code 6 / `HTTP=000`）を返した。**HTTP 404ではなく、Raw 0件や自治体の未掲載とも異なる**。この実行環境では HTTP応答、取得原本bytes、SHA256、現行のfeature数を証明できていない。

同じ範囲の取得を任意のMac等で再現するため、`pipeline/src/hinanex/gsi_hazard_acquisition.py` を追加。**明示実行時のみ**指定公式HTTPS URLへ1回GETし、公式URLとハザードの対応、リダイレクト拒否、上限20MiB、HTTP 200/最終URL一致、GeoJSON原文の全Feature構造検査を行う。検査を通った原本はリポジトリ**外**へ排他的に保存し、同じ場所に `.receipt.json` を作成する。既存証拠は上書きしない。出典のHTTPヘッダーは原文のまま保持し、掲載/更新/指定日へ変換しない。

### Macでの公式原本取得手順（任意の明示実行）

F02やF05の作業ブランチは触らず、既存cloneから独立worktreeを作成する例：

```bash
git -C "$HOME/HINANEX-f02" fetch origin feature/d-h0-gsi-dual-hazard-preflight-20261113
git -C "$HOME/HINANEX-f02" worktree add --detach "$HOME/HINANEX-h0-worktree" FETCH_HEAD
mkdir -p "$HOME/HINANEX-h0-evidence"
cd "$HOME/HINANEX-h0-worktree/pipeline"
python -m src.hinanex.gsi_hazard_acquisition \
  --hazard landslide \
  --source-url "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson" \
  --raw-out "$HOME/HINANEX-h0-evidence/skhb02-10-909-403.geojson"
```

- 成功： `H0_LOCAL_STRUCTURE_ONLY`（または`H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF`）＋`LOCAL_ARCHIVE_RECEIVED`、`http_status=200`、最終URL、Raw SHA256、UTC取得時刻、全Feature件数の**ローカル検査ログ**。ファイル `skhb02-10-909-403.geojson` と `skhb02-10-909-403.receipt.json` はGit外に保存する。
- DNS障害： `{"status":"H0_ACQUISITION_HOLD","reason":"DNS_FAILURE","http_status":null,"archive_created":false,...}`。HTTP 404や0施設を意味しない。
- HTTP404：`H0_ACQUISITION_HOLD`, `reason=HTTP_ERROR`, `http_status=404`。タイル応答が404でも自治体の0施設や全国的非公開とは判定しない。
- 別hazardのURL・別ドメイン・HTTPスキーム・リダイレクト・破損/改変/上限超過・非整数markerは拒否し、生rawは保存しない。
- 通信にHTTPプロキシを暗黙に使わない。会社/学校の明示プロキシ環境で接続できない場合は無理に回避せずネットワーク・許可条件を確認する。
- ツールはダウンロードを**定期実行しない**。GitHub Actionsは合成mockテストのみで外部公式原本を取得しない。

**証拠提出:** Issue #378または次のC専用Issueには、`.receipt.json` のステータス／原本SHA／HTTP／URL／UTC／件数を必要な範囲だけ転記する。Raw自体はGit・PRコメントへアップロードしない。受領者は利用者PCの取得ログとして扱い、独立Cの別HTTPS byte replay（URL/時刻/原本バイト/版/災害属性・feature index）と混同しない。人間による災害別指定・個別場所同一性、著作権・再配信条件、現在開設/安全/地図表示は未承認。

### H0追加の合成CIテスト

`pipeline/tests/test_gsi_hazard_acquisition.py`：ネットワークmockのみ。非公開専用ファイルへの保存、権限、出典HTTP/UTC/SHA、既存証拠上書き防止、Git内への保存拒否、URL/ハザード取り違え拒否、HTTP404・DNS分類、異常JSON/過大body、時刻無効、リダイレクト先不一致、空Feature≠自治体ゼロ件を検証。CLIがHTTP外部アクセスできることの証明ではない。

**次のゲート:** 実取得成功時はraw/source receiptをC独立検証担当に渡して別スコープで照合。C承認と公式Sourceの最新性・ライセンス判断が揃うまでD/RegionExportやE/GIS/Renderへ採用しない。
