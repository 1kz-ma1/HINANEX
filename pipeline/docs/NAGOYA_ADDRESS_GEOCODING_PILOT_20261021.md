# 名古屋市住所ジオコーディング・50件パイロット

2026-10-21 / Status: EXPERIMENTAL, NOT APPROVED FOR MAP OR ROUTING

## 背景と目的

既存の名古屋市屋内施設16区分Excelは名称・所在地を持つが緯度経度を持たない。既存の正規化では座標をnullとし、位置ベース探索をBLOCKEDとしている。過去の1602件は検証時点の観測値であり、最新件数や変換成功率の保証ではない。

このパイロットでは、住所を用いた位置参照点の候補取得・精度・欠損理由を50件以下で評価する。座標が得られても施設そのものの公式座標や入口座標、安全な避難先とは認定しない。

## 利用する実装・制約

- デジタル庁 Address Base Registry Geocoder（ABR）をローカルで稼働させる。
  https://github.com/digital-go-jp/abr-geocoder
- ABR側は独立して愛知県用のデータを取り込み、事前にcache build / serve等の公式セットアップを行う。ABR APIは実験的で、バージョンとDB版を記録する。
- このリポジトリでは追加のPythonライブラリ、公開オンラインAPI、外部位置情報サービス呼び出しは導入しない。
- ローカルの http://127.0.0.1:3000 /geocode のみオペレーターが明示的に実行する。初期prepare段階では一切通信しない。HTTP redirect禁止。
- クエリは 愛知県名古屋市 + 区名 + 原本所在地。ABRへは最大2件候補を要求し、候補が複数ある場合は未解決とする。
- 座標はGeoJSON形式の [longitude, latitude] から取得する。低解像度の町字代表点、不一致の住所、他区、余分な未照合住所、異常数値は採用しない。
- **地番（parcel）精度を自動的な候補成功に含めない。** デジタル庁ABR公式リポジトリの [Issue #256](https://github.com/digital-go-jp/abr-geocoder/issues/256) では一部の地番座標が実位置から大きくずれる事例が報告されている。名古屋の全地番に同じ問題があるとは断定せず、`NEEDS_REVIEW` として施設本人との独立照合を必須にする。
- ABR公式リポジトリの [Issue #254](https://github.com/digital-go-jp/abr-geocoder/issues/254) はGitHub Actions上での原本ダウンロード403事例を記録している。このためActions環境でABR生データを直接取得できることを前提としない。
- 過去のレコードIDと入力のSHA256、対象区名、ABRデータ版、位置精度、応答ハッシュを追跡できるようにする。

## 試験の操作手順

実際に使うのは隔離環境で取得・正規化された名古屋市の
pipeline/data/normalized/nagoya_shelters.json。
公式データの新規再取得や実データ評価の解禁を意味しない。

pipeline/ ディレクトリで以下を明示的に実行する。

~~~sh
python geocode_nagoya_pilot.py prepare --dataset data/normalized/nagoya_shelters.json --out data/geocoding_pilot/nagoya50
~~~

この処理は区を跨ぐ決定論的なラウンドロビン選定で、最大50件のmanifest.jsonを生成する。既存座標を持つ施設は除外する。ファイルは上書きせず、別回の実験では新たな出力ディレクトリを使う。

次にデジタル庁ABRの愛知県データセットをローカルで起動し、サービスのバージョンと利用条件を確認した後だけ次を実行する。

~~~sh
python geocode_nagoya_pilot.py resolve --dataset data/normalized/nagoya_shelters.json --out data/geocoding_pilot/nagoya50 --local-abr-url http://127.0.0.1:3000
~~~

出力は resolution.json。source recordの正規化座標やRegionExport、GIS、Scenario、開設状況・適合判定は**一切変更しない**。パイロット出力はGit管理外。

## 住所の行政区検証

入力の `administrative_area` は、[名古屋市公式の区役所一覧](https://www.city.nagoya.jp/shisei/gaiyou/1015754/1015781/index.html)に示される16区のみに限定する。対象外の区・住所が欠けた行は `skipped` に理由を記録して対象から除く。住所条件に合致するレコードが0件なら試験を開始せず失敗とする。地理的境界の実位置確認をこの文字列の区検証だけで代替しない。

## 判定区分

- UNVERIFIED_CANDIDATE: 一意の住所候補、区と住所が一致、街区・住居番号相当の精度。ただし独立した施設位置確認は未実施で、GIS公開不可。地番精度はここに入れない。
- NEEDS_REVIEW: 地番（parcel）精度、または異なる元レコードが同じ代表座標を持つ等の要検証。
- UNRESOLVED: 住所未一致、複数結果、区が違う、精度が粗い、座標不正等。施設不在や自治体の公開不足の意味ではない。
- PROVIDER_ERROR: ローカルABRの通信・応答が失敗した場合。ソース欠損として扱わない。

変換できた地点も全件 approved_for_map=false、data_promotion_authorized=false とする。自動的な人間承認・公式座標への昇格は存在しない。将来正式なGISに組み込むには別Contractの後方互換拡張、公式座標との照合、位置精度ラベル、本人操作、災害との適合判定の独立確認が必要。

## ABRの実機セットアップと検証集計

以下はDocker Composeを実行できる開発PCで、オペレーターが明示的に操作する工程です。ABR公式データの取込みと施設の実位置確認をCIで自動実行するものではありません。空き容量・利用条件を確認してください。

1. 公式 https://github.com/digital-go-jp/abr-geocoder をクローンし、同リポジトリ直下の .env.example を .env にコピーしてDBパスワードを設定する。.envはGitに追加しない。
2. 次を公式ABRリポジトリ直下で実行する。pref 23は愛知県、category allは住居表示・地番を含む対象。

    docker compose up -d postgres
    docker compose run --rm abrdb_app init --pref 23 --category all --pos
    docker compose run --rm abrdb_app import
    docker compose run --rm abrg_app cache build
    docker compose up -d abrg_app

3. コマンド docker compose ps と curl http://127.0.0.1:3000/health および curl http://127.0.0.1:3000/ で起動とAPI/DB版を確認する。
4. **外部公開の禁止:** 公式のDocker Composeは設定によって全インターフェースに公開され得る。公式 .env.example にある `PORT=3000`、`DB_PORT=5432` をそれぞれ **`PORT=127.0.0.1:3000`**、**`DB_PORT=127.0.0.1:5432`** に変更してから起動する。Composeの `ports` 定義がそのままであれば、この指定はそれぞれ `127.0.0.1:3000:3000` と `127.0.0.1:5432:5432` になる。`docker compose config` で実際のホストポートバインドを確認し、LAN・公衆ネットワークへの公開を行わない。別のポートを使う場合はホストポートとpilotの引数を整合させる。
5. HINANEXのpipeline/から、隔離環境に保存された公式名古屋市Excel由来のdata/normalized/nagoya_shelters.jsonを使う。必要なら既存の run_nagoya_workflow.py を明示実行する。元の原本・取得日・ハッシュを別記録に残す。
6. 同一データスナップショットで以下を順番に実行する。

    python geocode_nagoya_pilot.py prepare --dataset data/normalized/nagoya_shelters.json --out data/geocoding_pilot/nagoya50
    python geocode_nagoya_pilot.py resolve --dataset data/normalized/nagoya_shelters.json --out data/geocoding_pilot/nagoya50 --local-abr-url http://127.0.0.1:3000
    python report_nagoya_geocoding_pilot.py --pilot-dir data/geocoding_pilot/nagoya50

実行前には元データのSHA256と、抽出された施設ID・住所を元データから再計算して照合する。不一致があればローカルABRにも問い合わせず停止する。

7. 結果はgitignoredのdata/geocoding_pilot/nagoya50に保存される。summary.jsonとhuman_review.csvはGitにコミットしない。2回目の実験では上書きせず別フォルダを使う。

### 発表のための実データ診断と独立承認

- summary.json: 最大50件の対象数、UNVERIFIED_CANDIDATE比率、要レビュー・未解決・プロバイダ失敗数、座標精度、区別のサンプル数を集計。**候補取得率は位置精度や施設同一性の確認率ではない**。
- presentation_summary.md: 施設名・原本住所・候補座標は含まず、候補件数・未解決件数・精度・未検証の制約を発表用に記載する。人間の独立受入は0件として記録する。
- human_review.csv: 元ID、施設名、原本住所、候補緯度経度に対して、公式位置資料のURL、施設同一性、精度を人が確認するための空欄を持つ。全件NOT_REVIEWEDで生成。
- 公式施設座標として受入済みの件数は常に0、全件approved_for_map=false。実際の照合と公開向け地図への使用判断は別の受入ゲートとする。
- GithubのCIは合成データで分類と集計ロジックを試験するのみ。2026-10-21にローカルABR愛知県データによる50件実測を実施（結果は下記に記録）。**公式施設位置との独立比較は未実施**であり、CI結果から実測成功率を推測しない。

## 受入・検証

- Pythonの単体テストは合成データのみで行い、正例に加えて別区、複数候補、低精度、NaN、重複ID、旧データ、外部ホストを拒否する。
- 手動の実データ実験で50件の変換候補数、区別の未解決理由、精度分布、公式施設地図との位置誤差、同一点重複などを集計し、PASS/LIMITATION/NOT TESTEDを分離する。
- ローカルABR実データと名古屋50件の変換試験は2026-10-21に実施済み。**実地施設との位置照合は未実施**。合成テスト成功と実測結果は必ず区別する。
- 作業中のUI改善とは切り分ける。こちらの試験結果を公開GISへ自動同期しない。
- 住所・ジオコーディングデータの利用許諾、最新性、公開範囲は実運用に入る前に別途検証する。

## 2026-10-21 実測結果と住所不一致の追加診断（候補昇格なし）

同一パイロットの実測では、16区の公式屋内施設Excelを既存Adapterで正規化した1,602件から50件を抽出。ABR 3.0.52 / DB 3.0.29（愛知県23、category all）の結果は UNVERIFIED_CANDIDATE 6、NEEDS_REVIEW 1（parcel）、UNRESOLVED 43、PROVIDER_ERROR 0。未解決理由の内訳は「different_street_or_house_number」37件、「low_resolution_or_unknown_level」6件だった。**これらは住所参照点の診断結果であり、公式施設位置の正しさを保証しない。公式施設位置の独立確認は未実施。**

当初の`resolution.json`では不一致判定になったABR応答の住所文字列を保持していない。そのため既存パイロットを上書きせず、同一データ・同一ABR版のまま、37件に限定したローカル再照会を行う追加スクリプトを提供する。

```sh
# pipeline/ から、ローカルABRのhealthと127.0.0.1限定バインドを確認後に実行
python diagnose_nagoya_address_mismatch.py \
  --dataset data/normalized/nagoya_shelters.json \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --local-abr-url http://127.0.0.1:3000
```

- 入力JSON・manifest・resolution・summaryを相互照合し、抽出ID/住所の改変がないことを確認。通信開始前にスナップショット不一致を拒否する。
- ABRのhealth、API版、DB版、対象pref=23、category=allを検証。元の37応答のSHA256は履歴照合指標として保持する。ただしABRは`result_info.duration_ms`を毎回計測するため、**生JSONのSHA256が違うだけでは住所の意味的変化を示さない**。そのため各住所をローカルABRに2回照会して、**処理時間フィールドのみを除外した正規化JSON全体**が一致することを検証。住所・照合精度・座標・その他メタデータの差異があれば停止し、旧来の`UNRESOLVED`判定理由が変わった場合も停止する。古い出力を上書きしない。
- HTTPはlocalhost限定、リダイレクト拒否、proxy不使用。**個別の名前・ID・住所・住所候補・座標・レスポンスは出力せず**、gitignoredの`mismatch_diagnostics_aggregate.json`と標準出力に匿名件数のみ記録。
- 診断区分は次の4つ。これらは**現行ABRの再照会結果による文字列の観測パターン**であって原因・精度・施設位置の確定分類ではない。元のパイロットは個別の元レスポンスJSONを保存していないため、**SHA256が異なる当初の応答との意味的同一性は証明できない**。匿名集計には旧生レスポンスとのハッシュ一致数/差異数と、再照会2回の非時間情報一致数を必ず分けて記録する。
  - `source_suffix_not_matched`: ABR住所が元の住所の前方部分で止まる
  - `provider_has_extra_suffix`: ABR住所側に追加の末尾がある
  - `same_text_stem_number_difference`: 最初の数字より前の文字列は一致し、数字以降に相違がある
  - `town_or_other_text_difference`: 上記以外の住所文字列差
- 住居表示・地番体系の違い、真の番地違い、施設の位置誤差はこの機械的分類では確定できない。必要に応じて**ローカル限定**の公式施設位置資料による人間の独立照合で判別する。
- データの選定、元の50件ステータス、`UNVERIFIED_CANDIDATE`6件、施設位置受入0件、`approved_for_map=false`を一切変えない。RegionExport / GIS / 災害適合判定 / 正式座標には接続しない。
- Issue #286へはこの匿名化した集計と実測上の制約だけを掲載し、施設単位の内容や`human_review.csv`は絶対にコミット・投稿しない。
- 原本16ファイルのURL/取得時間帯/SHA256は個別のローカル監査記録で確認すること。元の実測集計に含まれていない場合は記録済みと断定しない。


### 再照会の失敗履歴（2026-10-21）

最初の37件診断は`ABR_RESPONSE_HASH_CHANGED`で停止した。ABR `result_info.duration_ms` が各API呼び出しで変わることを公式実装で確認したため、**初回結果を上書きせず**、上記の二重再照会方式へ変更。こちらの変更が実環境で成功したとはまだ判定しない。元の施設位置受入0件・GISへのNO-GOは不変。

### 住所不一致37件の実測結果とStage 2（2026-10-21）

ローカルABR 3.0.52 / DB 3.0.29で37件の匿名診断を完遂。現在の二重照会で処理時間を除くJSONは37件すべて一致した。初回の生JSONハッシュとの差は37件だが、古いレスポンス本文は保存していないため、**初回との意味的な同一性を証明するものではない**。

| Stage 1 住所文字列パターン | 件数 |
|---|---:|
| town_or_other_text_difference（残余カテゴリ） | 35 |
| source_suffix_not_matched | 2 |
| same_text_stem_number_difference | 0 |
| provider_has_extra_suffix | 0 |
| 合計 | 37 |

ABR unmatched_addressが空でない照会は10件。35件の文字列差との重なり、実際の町名・住所体系の違いは未判明。35件を町名誤りと断定しない。

この残余35件をさらに、**数字アンカーの有無／数字以降の文字列一致／ABRの住所マッチ粒度／未照合トークンの存在**へ分解する診断を同じDraft PRに追加。Stage 1の匿名レポートが存在し、かつ原本データ・元の50件レポートと整合するときだけ再診断する。

~~~sh
# pipeline/ から、Git管理外のローカルデータだけを使用
python diagnose_nagoya_text_difference_stage2.py \
  --dataset data/normalized/nagoya_shelters.json \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --local-abr-url http://127.0.0.1:3000
~~~

成功時は data/geocoding_pilot/nagoya50/text_difference_stage2_aggregate.json に**匿名集計のみ**を新規出力（既存ファイル上書き不可）。出力するのはカテゴリ別件数、数字以降の部分文字列一致数、既知のABRマッチレベル別件数、各種表記マーカー検出数等。個別住所・施設名・施設ID・候補座標・元ABR応答本文を保存・表示せず、対象37件の元分類をすべて再現できない場合は出力を中止する。

例えば both_have_numbers_text_stem_diff は数字の前の表現に差があることを示すだけ。numeric_suffix_observations.same は数字以降の文字列が同じという観測結果であって、その施設が同一位置にある証拠にはならない。oaza/aza・漢数字丁目も**表記特徴の件数のみ**。住所の自動補正／再ジオコーディングによる候補追加、GIS反映、災害適合判定、独立施設照合は行わない。

Stage 2のコードの合成テストが成功しても**35件の実データ解析結果を得たことにはならない**。Macローカルで上記コマンドを実行し、匿名JSONを確認するまでは結果を未測定とする。

### Stage 2実測の結果（2026-10-21）

ローカルABR v3.0.52 / DB v3.0.29で Stage 2を実行。Stage 1の37件の分類を全件再現し、残余35件の以下の匿名集計を得た。

- 数字アンカー: 双方にASCII数字があり、数字より前の文字部分が異なる28件。ABR側にASCII数字が存在しない7件。
- 双方に数字がある28件では、その数字から後ろの文字列が異なる28件。元住所とABR住所の数字以降が一致した事例0件。
- **ABR側で漢数字の丁目表記が見られた施設は35/35件。** これは表記差の強い仮説だが、35件が住所同一である証明ではない。
- ABRマッチレベル: rsdtdsp_rsdt 21、parcel 6、machiaza_detail 7、rsdtdsp_blk 1。ABR座標レベルは rsdtdsp_rsdt 21、machiaza_detail 13、rsdtdsp_blk 1。**住所照合レベルと座標参照点精度は異なるフィールド**であり、独立した施設位置確認や座標昇格は未実施。
- Stage 2対象の未照合部分が非空は8件。Stage 1の37件全体では10件。
- 元の50件の候補6・レビュー1・未解決43・ABRエラー0は不変。Stage 2でもGIS/避難安全性/実施設の受入は0件。

### Stage 3：限定的な漢数字丁目の表記差を測る実験

漢数字の丁目だけが原因ならどれだけ正規化できるかを知るため、**候補判定ロジック自体は変更せず**、新規のローカル匿名集計スクリプトを追加した。

~~~sh
# pipeline/ から実行。既存50件・37件・Stage 2のファイルを上書きしない
python diagnose_nagoya_kanji_chome_stage3.py \
  --dataset data/normalized/nagoya_shelters.json \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --local-abr-url http://127.0.0.1:3000
~~~

- 正規化範囲は**1〜100の標準形の漢数字が「丁目」に直結する場合のみ**。漢数字の町名・大字・番地を無差別に数字へ置換しない。不正な数詞や未対応形式は別カテゴリでカウントして変換しない。
- 元住所とABR住所をそれぞれ上記の限定的な文字列比較キーへ変換し、完全一致／元住所の末尾未一致／ABR側の余分な末尾／依然異なる／未対応数詞を**件数としてだけ**表示。番地差や町名差を推測補完しない。
- 実測時の原本データSHA256、元50件レポート、Stage 1・2匿名レポートと全件の再照会結果を照合。各住所はlocalhostの同じABRへ2回照会し、処理時間フィールド以外が変化したら出力を中止。Stage 1と2の既存集計件数を再現できなければ中止する。
- 出力ファイルは gitignored の data/geocoding_pilot/nagoya50/kanji_chome_stage3_aggregate.json。新規作成のみ。個別住所/施設名/ID/座標/HTTPレスポンスは記録しない。
- **文字列上の完全一致であっても、施設の正確な位置や災害安全性の証明にはならない**。Stage 3は候補取得率や座標精度を更新せず、承認を行わない。位置照合には別の公式施設資料と独立レビューが必要。
- 合成データのCI成功と**ローカル35件のStage 3実測完了は区別**して扱う。後者は匿名レポートの確認後にのみ記録する。

### Stage 3の実測結果とStage 4（2026-10-21）

開発Macの匿名Stage 3実測（ABR v3.0.52 / DB v3.0.29、dataset SHA256 = d5f7191a49d4f531fa890ccf437918789ed534138b1e89973d6181cf6aa1c3a3）：

| 限定的な漢数字丁目正規化を行った後 | 件数 |
|---|---:|
| 完全な住所文字列一致 | 27 |
| ABRは元住所の途中まで一致 | 8 |
| 表記統一後も異なる住所文字列 | 0 |
| 未対応の漢数字丁目 | 0 |
| 合計 | 35 |

完全な住所文字列一致27件はいずれもABRの unmatched_address が空であった。ただし、これは**27施設の位置を確認したことではない**。元の6件の未承認候補に足して33件が地図利用可能と主張することも不可。

今回の27件に対して、Stage 4で候補参照点の品質を**匿名集計でのみ**スクリーニングする。

~~~sh
python diagnose_nagoya_chome_stage4_reference_screen.py \
  --dataset data/normalized/nagoya_shelters.json \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --local-abr-url http://127.0.0.1:3000
~~~

Stage 4は元の原本データ、決定論的抽出50件、Stage 1〜3のローカル匿名レポートを相互検証し、同じローカルABRへ再照会した37件の分類が再現する場合のみ出力する。ABR応答は各住所2回の比較で処理時間以外の内容一致を要求。出力は gitignored の chome_stage4_reference_screen_aggregate.json を新規作成するのみ。

- 完全一致27件だけに限定して、ABR住所マッチレベル・座標レベルとも rsdtdsp_blk または rsdtdsp_rsdt、未照合住所が空、座標が有効範囲内のPoint、他の候補と同じ参照座標を共有しないかを確認。
- 地番精度を含む場合は別の要確認カテゴリ、町字詳細やレベル不明も独立レビュー待ちカテゴリ。住所の先頭部分だけが一致した10件は候補昇格しない。
- 重複判定では今回27件の参照座標同士だけでなく、元の実測で候補扱いだった6件・要確認1件の参照座標も比較。ただし**同一点かどうかは位置の独立受入・否認を意味しない**。
- スクリーニングに通った場合も high_resolution_reference_for_independent_review と呼び、**公式施設位置として承認・公開してよい候補という意味ではない**。実施設・敷地・入口と公式根拠の人間による照合は別工程。
- 既存の classify、正規化元データ、RegionExport、GIS、災害適合判定、地図に流通する座標は不変。Stage 4の実データ結果はMacローカルでコマンド実行するまで不明。

### Stage 4の実測と施設位置の独立照合へ進むローカル台帳

2026-10-21、ローカルABR API 3.0.52 / DB 3.0.29、同一dataset SHA256 d5f7191a49d4f531fa890ccf437918789ed534138b1e89973d6181cf6aa1c3a3 でStage 4を実行。27件の丁目表記後完全一致について次を得た。

| Stage 4住所参照点スクリーニング | 件数 |
|---|---:|
| 高解像度の住所参照点として独立確認へ進める | 21 |
| 地番由来の参照点で別途注意を要する | 6 |
| マッチ/座標粒度不足、無効座標、重複、未照合住所 | 0 |
| 合計 | 27 |

ここでの21件は**ABR住所参照点としてのスクリーニング通過**であり、実際の施設・入口・建物位置の承認ではない。元50件の通常候補6件も未承認のまま。Stage 1〜3の部分一致10件、初回低解像度6件は候補へ昇格しない。

この結果から、人間が公式施設資料と独立照合を進められるよう、プライベートな確認台帳を生成するReview Queueを追加。

~~~sh
# pipeline/ から。元50件とStage 1〜4のローカル結果が必要
python create_nagoya_independent_review_queue.py \
  --dataset data/normalized/nagoya_shelters.json \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --local-abr-url http://127.0.0.1:3000
~~~

- 既存の50件出力、Stage 1〜4の匿名集計を読み取り、Stage 4判定を同一ABRへ再照会して確認する。スナップショット・集計に不一致があれば台帳出力を中止。
- Git管理外のローカルフォルダに independent_facility_position_review_PRIVATE.csv を新規作成。このCSVには**施設名・原本住所・施設ID・未承認の参照座標**が含まれるため、**Gitへコミットせず、チャットやIssueへ本文を貼り付けない**。
- independent_review_queue_aggregate.json は匿名集計だけ。Stage 4由来のA優先候補21件、元の未承認候補6件、地番由来のB注意候補7件（Stage 4の6件＋元の1件）の合計34件が期待される。これは実行前の予想であり、位置承認済み34件を意味しない。
- CSVにはレビュー未完了を明示。照合者が公式施設根拠URL、根拠日付、施設種別（指定緊急避難場所・指定避難所・退避施設など）、施設同一性、原本住所、施設の敷地・建物・入口とABR参照点の関係を**独立資料に基づき手動確認**して記載。名称と住所だけで「施設位置確認済み」としない。
- 名古屋市は指定緊急避難場所と指定避難所を別の用途で定義している（https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html）。帰宅困難者向け退避施設とも混同しない。**施設分類・開設状況・災害適合性・経路安全性は位置確認とは別ゲート**。
- 台帳生成は元のスナップショット・各段階の判定・既存RegionExport/GIS/本番を変更しない。review_status はすべて NOT_REVIEWED で出力し、自動承認・外部公開・GISの書き込みは行わない。
- 公式施設位置として受入済みは0件。独立した施設位置照合が行われるまで公開地図連携はNO-GOを維持。

## 発表質問への回答例

「名古屋市の屋内施設の住所情報は取得できていますが、緯度経度の列はありません。そこで住所から座標候補を得る実験用のパイプラインを追加しました。候補点と公式施設座標は区別し、変換時の位置精度・版・不一致を記録します。座標が付いただけでは避難時の安全性・施設の開設状態・経路の通行可能性は証明できないため、正式な地図表示への自動昇格は行っていません。」
