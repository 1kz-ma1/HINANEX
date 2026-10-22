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

### 2026-10-21：34件の独立位置照合台帳が完成／GSI別データでの照合準備

開発Macで独立位置照合台帳の生成に成功。匿名報告の `total_review_rows=34`（A_NEW 21、A_EXISTING 6、B_PARCEL 7）。50件の元パイロットから部分一致10件は除外。34行はすべて NOT_REVIEWED、施設位置としての公式受入0、地図反映権限なし。元データハッシュ d5f7191a49d4f531fa890ccf437918789ed534138b1e89973d6181cf6aa1c3a3、ABR API 3.0.52 / DB 3.0.29。**確認台帳自体は氏名ではなく施設名・住所・候補座標等を含み、GitHubやチャットにアップロードしない。**

公開されている別の公的データとして、国土地理院の**指定緊急避難場所・指定避難所データ**を確認：
- 国土地理院案内: https://web1.gsi.go.jp/bousaichiri/hinanbasho.html
- 利用条件・ダウンロード: https://hinanmap.gsi.go.jp/index.html
- データ仕様: https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html （施設・場所名、住所、緯度、経度、共通ID等）。GSIデータは**自治体から登録されたもの**で、最新性・網羅性は保証されず、同一測位から派生している可能性がある。市が2026-10-07に更新した一覧は2026-09-01時点（https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html）。**資料更新日と指定日の違いを維持する**。

Stage 5として、**CSVはオペレーターがGSIサイトの利用条件を読み同意して明示的に取得する**方式とし、ブラウザーでの同意や取得をスクリプトが代行しない。Mac内でのみ、34件の台帳とGSI CSVを「施設名＋住所の保守的な表記正規化後の完全一致」で照合。名称のみ／住所のみ一致、重複座標、異なる参照点は別分類。ABR位置とGSI登録点の距離を比較するが、距離は**位置の正確性・施設同一性・安全性の承認ではない**。分類用の距離帯は分析上の便宜的閾値であり災害用の閾値ではない。

~~~sh
# ダウンロードしたCSVは必ず pipeline/data/geocoding_pilot/nagoya50 内に置く（Git ignore）。
# ファイル名は例。サイト上の正式名称を確認後、適切なCSVを指定する。
python compare_nagoya_gsi_offline.py \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --gsi-emergency data/geocoding_pilot/nagoya50/gsi_emergency.csv \
  --gsi-shelter data/geocoding_pilot/nagoya50/gsi_shelter.csv

# 一方のCSVしか対象自治体で提供されない場合は、存在する方の引数のみ渡す。
~~~

- 追加スクリプトは**ネットワークアクセスなし**。GSI CSVには保守的な項目名と明示された名古屋市・区の住所を要求。名古屋市の全ての屋内施設が含まれるとは推測しない。
- private出力: gsi_cross_reference_PRIVATE.csv（施設情報・ABR参照点・GSI登録点・距離を含む。**アップロード禁止**）。
- 共有可能な匿名出力: gsi_cross_reference_aggregate.json（照合結果・距離帯・A/B優先別件数、GSI CSVのSHA256、読込レコード数）。ローカルの既存34件台帳も更新しない。両方とも新規作成のみで上書きは拒否。
- GSIと一致しても official_facility_positions_accepted=0、approved_for_map=false / data_promotion_authorized=false。建物の位置・入口・対象災害ごとの指定・開設状況・避難経路を独立確認しなければGIS反映は不可。
- CIは合成レコード・架空座標のみ。実際のGSIデータでの34件突合と独立した位置確認は、Macローカル実行まで **NOT TESTED**。

### Stage 5実測結果・Stage 6プライベート確認台帳（2026-10-21）

利用者がMacで実行した国土地理院GSI CSVのオフライン照合（名古屋市向け review queue 34件）の匿名集計が完了。GSI CSVは指定緊急避難場所 5,820行中名古屋市住所記載1,750行、指定避難所 3,117行中822行。これは**名古屋市の施設件数や網羅性の保証ではなく、各CSV内の住所文字列に対する抽出件数**。

| Stage 5結果 | 件数 |
|---|---:|
| 名称＋住所の厳格一致・一意のGSI参照点 | 31 |
| 厳格一致するがGSI側の参照座標が競合 | 2 |
| 住所は一致するが施設名未確認 | 1 |
| 計 | 34 |

一意対応31件のABR〜GSI参照点距離は25m未満10件、25〜100m未満14件、100〜500m未満7件、500m以上0件。A_NEW 21件中の厳格一致18件／競合2件／住所のみ一致1件。A_EXISTING 6件とB_PARCEL 7件は各全件厳格一意一致。しかし、**GSI点との一致・距離が近いことは施設の敷地・建物・入口の位置、災害適合性を証明しない**。公式施設位置の独立承認は0件。

次の Stage 6 は**元のプライベート台帳・Stage 5の個別CSV・Stage 5匿名集計・GSI原本CSV（同一SHA256）**を再計算して一致確認する、オフライン専用の優先度付き人間レビュー台帳。Git管理外の作業環境で次を実行。

~~~sh
cd ~/Developer/HINANEX
git pull --ff-only origin feature/d-nagoya-geocoding-pilot-20261021
cd pipeline
source .venv/bin/activate
python triage_nagoya_gsi_stage6.py \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --gsi-emergency data/geocoding_pilot/nagoya50/gsi_emergency.csv \
  --gsi-shelter data/geocoding_pilot/nagoya50/gsi_shelter.csv
~~~

- 出力 PRIVATE: gsi_stage6_review_PRIVATE.csv。実施設名・住所・参照点・競合GSI候補座標・同住所の別施設名が入る。**GitHub、チャット、共同資料にはアップロード・貼付け禁止**。公式の施設・敷地・建物・入口の根拠URL・日付・種別・確認者・レビュー結論を人間が追記するための空欄を備える。すべて NOT_REVIEWED のまま開始し、別の明示的な受入操作なしに更新しない。
- 出力共有可能: gsi_stage6_triage_aggregate.json。カテゴリ件数、P0/P1/P2優先度ごとの件数、注意点が重複した施設数のみ。個別施設情報・座標は書かない。
- P0はGSI登録座標が競合する、住所一致でも名称が異なる、対応が一意に確認できないなどの施設同一性・参照点の不確実性。P1は100m以上離れた参照点、地番由来の位置ずれリスク。P2はその他の標準的な公式施設照合。ただし**P2も未承認**。
- 2つ以上の要確認理由を持つ施設は、各理由の件数には含めるが、優先レビュー総数では1施設として扱う。Stage 5から判明している2件のGSI競合／1件の住所のみ一致／距離差7件／地番由来7件の重なりは、このStage 6匿名集計で判明する。
- Stage 5の個別出力と元GSIファイルから再計算した結果が違う場合はフェイルクローズ。以前のPRIVATE台帳は上書きせず、新規ファイル名に作成。ネットワーク／GIS mutation／RegionExport／mainは変更しない。
- データの提供日・指定区分、独立した施設位置の公式根拠（同一自治体が登録したGSI点との循環参照にならない証拠）を確認できるまで、位置承認0件、approved_for_map=false、data_promotion_authorized=false、避難安全判定NO-GO。
- CIは架空施設データのみ。Stage 6のMacローカル実測件数と個別確認の結果は**実行するまで不明**。

### Stage 6実測・人手による施設位置確認のゲート（2026-10-21）

Macで Stage 6のオフライン匿名集計 `NAGOYA_STAGE6_MANUAL_GSI_DISCREPANCY_TRIAGE_NOT_SITE_APPROVAL` を取得。dataset SHA256 `d5f7191a49d4f531fa890ccf437918789ed534138b1e89973d6181cf6aa1c3a3`、GSI両CSVのSHA256がStage 5と一致し、Stage 5件数も再現（`stage5_status_counts_reproduced=true`）。全34施設は依然 NOT_REVIEWED。

| 優先度 | 実測施設数 | 手動確認の要点 |
| --- | ---: | --- |
| P0_IDENTITY_OR_GSI_CONFLICT | 3 | GSIの異なる参照点2・同住所別施設名1 |
| P1_DISTANCE_OR_PARCEL | 9 | ABR-GSI参照点100m以上7・地番参照点7（重複あり） |
| P2_STANDARD_SITE_REVIEW | 22 | 重点注意フラグなし。ただし施設敷地・建物・入口の独立確認は未実施 |
| 合計 | 34 | 公式施設位置の承認数0 |

要注意フラグは合計17で、異なる施設数12、2つ以上のフラグがある施設数5。P0の3施設とP1の9施設を合わせた12件が先行確認対象。距離100mは**レビュー優先順位を設定するための便宜的閾値**であり、避難時の位置精度基準ではない。P2が「安全・確認済み」を意味することもない。

**次は自動診断を増やすより、同じローカルCSVを人間が検証する工程を優先する。**

- `pipeline/data/geocoding_pilot/nagoya50/gsi_stage6_review_PRIVATE.csv` は施設名・住所・参照点を含むため、Mac内に限って開き、`stage6_priority` でP0 → P1 → P2の順に確認。別の受入コマンドやGIS書込みは用意しない。手動レビュー済みを表示できる仕組みは将来別途設計。
- P0の2件の座標競合では、GSIに指定緊急避難場所と指定避難所の異なるレコードが存在する可能性も含め、**根拠のない同一視・点の平均化・座標選択をしない**。名称不一致1件も「改称」と即断せず、正式施設名の版・住所・施設同一性を検証。
- P1の100m以上離れた参照点7件と地番精度の点7件は同一施設を重複して含み得る。どちらが正しいかは自動判定せず、公式の独立した施設図・管理者資料・建物/入口の位置根拠を確認する。
- 各行の `official_site_evidence_url`、`official_evidence_date`、`facility_identity_evidence`、`site_position_evidence`、`entrance_or_building_evidence`、`facility_type_confirmed`、`reviewer`、`reviewed_at` を根拠とともに人間が記録する。ただしCSVへの記載とGIS/RegionExportへの正式採用は別の承認ゲートである。
- GSIは自治体登録に基づくため、他ソースとの完全一致を**独立測位の裏付け**とはみなさない。施設種別・災害適合性・開設状況・経路安全性の判断は位置の照合から独立した検証事項。
- 元50件のステータス・座標は変更しない。site_position_independently_verified=false、official_facility_positions_accepted=0、approved_for_map=false、data_promotion_authorized=false、GIS利用NO-GOを継続。Issue #286に匿名の実測値を記録。PR #283はDraft。

### Stage 7 — 近接登録点・工事注記の安全な再分類（実データ再検証待ち）

Stage 6で P0 3件（GSI登録点の競合2件、同住所・別名1件）となった施設を**ローカルで追加確認**。競合2件はどちらも指定避難所／指定緊急避難場所の異なるレコードで、ABRとの距離は各79.5m・77.1m、異なるGSI登録点の相互距離は小数第6位メートル表示で `0.000000m`。**丸めた表示から厳密に座標が同一とは断定できない**。別名1件はGSIの施設名が原本の工事注記を除いた基本名と一致しており、原本には令和8年7月11日〜令和9年3月31日の改修工事による使用不可が記載されている。これも使用可否の最新公式情報を独立確認するまで自動判定しない。

既存Stage 5/6実測値を変更・上書きせず、**versioned Stage 7**を追加：

- GSIの正確な生の経緯度は保持し、GSIの両種別も維持したまま、**全ペアの参照点間距離が1mm未満（0.001m未満）**の場合に限り `gsi_distinct_references_under_1mm` という**照合用の観測分類**へ分ける。大きな距離差は以前どおり競合。平均点や片方の「正しい座標」は作成しない。**この1mmは表記ゆらぎを抽出するための分析基準であり施設位置の測位精度基準ではない。**
- 施設名の工事注記は、**限定された形式（末尾 ※R?.?.?～R?.?.?まで…工事のため、使用不可）に完全一致する場合のみ**原文を保持したまま、施設基本名・令和を西暦へ変換した開始日／終了日・使用不可の原文理由を別の**確認用列**へ抽出。日付が不正、改修工事形式以外の注記、GSIの施設基本名と住所がともに一致しない場合は従来どおり不一致。工事期間終了後も**自動で使用可能に戻さない**。
- 元のStage 5のCSV/GSI原本hash/Stage 6のPRIVATE CSV/匿名集計をローカルで再計算し、いずれかの履歴・承認禁止条件が変わればフェイルクローズ。元の PRIVATE/匿名レポートは新規出力でも一切上書きしない。
- バージョン変更後も工事による使用不可の記載がある施設は**P0（施設運用状況の独立確認が最優先）**、100m以上の参照点差・地番由来はP1、近接登録点だけの見かけ上の競合であればP2（ただし**未承認・独立位置照合が必要**）という優先順位で再集計。
- Stage 7の合成テストとGitHub CIだけでは実際の2件が1mm未満か判定済みとは言えない。**Macで同じGSI CSVを指定して実行するまで、新しい優先度件数は未確定。**

~~~sh
cd ~/Developer/HINANEX
git pull --ff-only origin feature/d-nagoya-geocoding-pilot-20261021
cd pipeline
source .venv/bin/activate
python refine_nagoya_gsi_stage7.py \
  --pilot-dir data/geocoding_pilot/nagoya50 \
  --gsi-emergency data/geocoding_pilot/nagoya50/gsi_emergency.csv \
  --gsi-shelter data/geocoding_pilot/nagoya50/gsi_shelter.csv
~~~

- **匿名・共有可能**：`gsi_stage7_refined_aggregate.json` （修正前後の件数だけ）。
- **PRIVATE・Mac内限定**：`gsi_stage7_refined_PRIVATE.csv` （元の施設名・住所・GSI/ABR座標・原文工事注記・新しい判定列が入る）。GitHub/Issue/チャットには絶対に投稿しない。
- `approved_for_map=false` / `data_promotion_authorized=false` / 公式施設位置受入0。指定避難所・緊急避難場所の区分、工事期間の運用制限、独立した施設位置検証、災害適合性・開設状況・経路安全性は**別々の判定ゲート**を継続。

### Stage 7 Mac実測の確定結果と次の独立確認（2026-10-21）

Macの既存34行の非公開確認台帳およびGSI原本を使い、`refine_nagoya_gsi_stage7.py` の実測完了。原データSHA256は `d5f7191a49d4f531fa890ccf437918789ed534138b1e89973d6181cf6aa1c3a3`。GSI指定緊急避難場所CSV SHA256 `252f58cc0cd6957e52f03d9c803b7ff9326314c0e8b72f2adcff564d1e71c795`、指定避難所CSV SHA256 `6bbe27d1e3af5a627acb3be532c3a29aaaa332471d4c6cdfff4d633c6a456693` はStage 5/6と同一。Stage 5/6の過去出力・元データは未変更。34行は全件 NOT_REVIEWED。

| 優先度 | Stage 6実測 | Stage 7実測 |
| --- | ---: | ---: |
| P0（名称・GSI参照点の競合 → 現在の施設運用制限確認） | 3 | **1** |
| P1（距離差・地番参照点） | 9 | **9** |
| P2（通常の独立施設位置照合） | 22 | **24** |
| 合計 | 34 | **34** |

`near_coincident_distinct_gsi_reference_cases=2`：2件のGSI異なる生の座標値について、全ペア間距離が**1mm未満**と診断された。指定避難所・指定緊急避難場所の登録区分と生座標はそれぞれ保持。**同一点を測量で確認した／入口位置が正しい／安全と確認した、という判定ではない**。

`recognized_source_renovation_notice_name_matches=1`：原本の工事使用不可注記を分離すると、GSIの基本施設名＋住所と対応することが示された。ただし最新の運用可否・指定区分の変更・再開日は未検証。令和8年7月11日から令和9年3月31日までという**原本の記載期間**は保存し、期間経過時にも自動で「使用可能」にしない。

その他31件は `unchanged_standard_reference`、残存する分類不能な照合競合は0件。これは**参照照合における分類結果**であり、31件の敷地・建物・入口の公式位置確認を意味しない。

**次のゲート：コードの自動緩和ではなく人間による独立確認。**

1. P0の1件：原本の使用不可期間と自治体の直近の指定/利用制限情報を照合。名称の正規化だけをもって施設利用可能と判断しない。
2. P1の9件：ABR参照点とGSI登録点の差、地番精度、実際の敷地・建物・入口位置を独立した公式施設資料で検証し、点の自動選択や平均化をしない。
3. P2の24件：公式の住所・施設同一性・敷地/建物位置を独立確認する。GSIが自治体登録に由来するため、ABR/GSIが近いことだけでは独立測位の証拠としない。
4. **個別PRIVATE CSVの施設名・住所・座標をGitHub/Issue等へ貼り付けない**。確認理由・対応方針・全体の匿名集計のみ共有。施設位置の人手判定が済んでも、RegionExport/GISへの昇格は別の明示的承認ゲートを必要とする。

現時点：位置の正式受入0、`site_position_independently_verified=false`、`approved_for_map=false`、`data_promotion_authorized=false`、避難安全性・開設状況・経路の検証なし。PR #283はDraftで本番・mainへの採用を保留。

### 2026-10-21 — P0運用制限の公式一次照合とローカル確認画面

**公式の証拠（避難施設の指定と使用制限は別軸）**：

- 名古屋市防災ポータル「指定緊急避難場所・指定避難所の指定」、**2026年10月7日更新**、一覧は**2026年9月1日時点**：https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html
- 千種区「指定緊急避難場所及び指定避難所一覧（屋内施設）」**1ページ目、千種学区ア3**：https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai01chikusa0809.pdf
- 上記の同一行に、洪水・内水と土砂の指定緊急避難場所が「○」、指定避難所も「○」と記載される一方、**2026年7月11日〜2027年3月31日のリニューアル改修工事による「使用不可」**が明記されている。したがって、指定/適用災害種別は**原資料の指定のまま保管し、実際の使用制限を独立した状態・根拠として保持する必要がある**。指定「○」を現在利用可能という証明に使ってはならない。
- 名古屋市千種区の一般施設案内（**2025年10月16日更新**、https://www.city.nagoya.jp/chikusa/shisetsu/1019490/1016037.html ）は施設名称/所在地の裏付けになるが、2026年の改修期間より古く、**最新の開設・再開状況の裏付けには使えない**。
- P0を**「公式使用制限の資料上の存在確認」**まで進められたとする。災害発生時の個別開設、実際の利用可否、正しい敷地/建物/入口位置は**未確認**。指定・使用制限・位置・開設を単一の真偽値へ畳み込まず、`SOURCE_LISTED_UNAVAILABLE` と `CURRENT_OPERATIONAL_STATUS_UNVERIFIED` を別概念として扱う。制限期間終了後も再開を自動認定しない。今後の正式な利用可否・現地位置認定に人間の独立資料確認を必要とする。

**CSV閲覧が難しい開発Mac向けの PRIVATEな確認画面**を追加。既存Stage 7データを読み取るだけで、ローカルHTMLのP0/P1/P2カードを生成する。HTML表示には施設名・住所・調査用距離・原本注記が含まれ、**GitHubやChatGPT、共用ストレージにアップロードしない**。外部画像・JS・マップタイル・第三者スクリプト・外部データ送信・自動地図化はなく、自治体の公式リンクを手動で開くだけ。注意：外部の公的サイトへ移動すればブラウザーはその外部サイトへアクセスするため、リンク自体はユーザーの明示的操作のみ。

~~~sh
cd ~/Developer/HINANEX
git pull --ff-only origin feature/d-nagoya-geocoding-pilot-20261021
cd pipeline
source .venv/bin/activate
python view_nagoya_stage7_private.py --pilot-dir data/geocoding_pilot/nagoya50
open data/geocoding_pilot/nagoya50/gsi_stage7_review_PRIVATE.html
~~~

出力ファイルが既存なら誤って人間の手動メモを上書きしないため停止する。画面の「P1 · 距離/地番」に9施設を並べる。**各施設の元の名称・住所と、公式の施設図・敷地・入口の資料を確認し、観測点のどれが正しいかを選ぶことなく根拠を残す。** 残りのP2も地図公開・位置承認は不可。人間による独立位置評価とGISへの公開承認は別ゲート。

この追加は新しい正規化・公式出典の自動取得・RegionExport/GIS公開ではなく、Macローカルの人手レビュー支援。Stage 7実測 P0=1/P1=9/P2=24、公式施設位置承認0、NO-GO維持。

### PRIVATE確認HTMLのValueError修正（2026-10-22、既存Stage 7は再実行不要）

Stage 7の既存実測 `gsi_stage7_refined_PRIVATE.csv` には、**出力スキーマの問題**により `independent_site_position_approved` という列名が2回出力されていた。Stage 7の匿名集計自体は成功していたが、追加のローカル確認画面が共通CSVリーダーによる**重複ヘッダー禁止**で `Local review HTML aborted [ValueError]` を返し、HTML未生成となった。

実装上の対処は次の2点に限定：
- **将来作成されるStage 7 CSV**の列定義 `ADDED_FIELDS` から重複する承認欄を外し、出力前に全ヘッダー一意性を検証する。
- 既存のMacの `gsi_stage7_refined_PRIVATE.csv` はそのまま保存し、ローカルHTMLビューア `view_nagoya_stage7_private.py` だけで**従来の厳密なヘッダー順と重複箇所1つ**を例外的に読み取る。各行の承認欄2つが**完全一致**する場合に限り読込を許可し、不一致・別の重複・列欠損や行不正はフェイルクローズ。**上書き修復や再生成はしない。**
- 合成テストで従来の二重ヘッダー、将来の一意ヘッダー、矛盾した承認値、予期しないヘッダー・行長を検証。手動レビュー状態・位置承認フラグの拒否規則、プライバシー、無接続のHTML、RegionExport/GIS NO-GOは維持。

Macで再試行（現在の `pipeline` にいる場合も、リポジトリから更新後に実行）：

~~~sh
cd ~/Developer/HINANEX
git pull --ff-only origin feature/d-nagoya-geocoding-pilot-20261021
cd pipeline
source .venv/bin/activate
python view_nagoya_stage7_private.py --pilot-dir data/geocoding_pilot/nagoya50
open data/geocoding_pilot/nagoya50/gsi_stage7_review_PRIVATE.html
~~~

**PRIVATE.csvの削除、Stage 7の再実行、元データ/GSI CSV/集計の再ダウンロードは不要。** HTMLもPRIVATEのためMacから出さない。全34件NOT_REVIEWED、正式施設位置受入0、地図公開なし。

### 班員へ配布する最小限のJSON（2026-10-22、PR #292 の静的HTMLとセット）

Stage 7の個別 `gsi_stage7_refined_PRIVATE.csv` を班員へ配布することはできないため、**機械的に列を許可リスト方式で抽出するローカルJSON変換**を追加。UIはB側Draft PR #292、JSON変換は本D側の独立したDraft PRから提供する。双方とも未マージ・Render未公開。

- スクリプト：`pipeline/export_nagoya_team_review_json.py`
- デフォルト出力：`pipeline/data/geocoding_pilot/nagoya50/team_review_p1_LOCAL.json`（P1 9件のみ。選択を変える場合は `--priorities P0 P1 P2` など）。
- チーム共有用JSONに含めるのは `schema_id`、元データ指紋（SHA256）、掲載施設名・住所、確認優先度、**照合上の確認理由コード**、公式一覧トップページのリンク、空の資料確認欄・作業記録だけ。各施設IDは元の内部記録IDから決定的ハッシュで生成する。
- **絶対含めない**：ABR/GSI候補座標、個別GSI登録原文/ID、GIS座標候補の差分距離、PRIVATE証拠フィールド、正式な位置承認や災害安全性の判定。追加データ列は採用しない。
- Stage 7 PRIVATE CSVの過去版重複承認ヘッダーも、2値が一致しない限り拒否。Stage 7集計の元データSHA256、P0/P1/P2件数、全件NOT_REVIEWED、承認・公開禁止フラグをチェックし、行数不一致・未知のリスクコード・不正な入力は停止。
- 生成先は**gitignoredの開発Macローカルだけ**。ファイル上書きなし。標準出力は件数・禁止フラグだけで施設名や住所を出力しない。作成したJSONは作業者本人が共有相手・共有手段を確認したうえで限定配布する。公開Stagingの `deploy/dist` へのコピーは不可。
- Bの `hinanex.team-review.v1` で手動ロード→各施設の確認状態・確認者・根拠URL・メモをブラウザー内で編集→JSON書き出し。共同編集や自動マージは提供しない。変更を配る際はファイルごと別名保存し、同じ `dataset.source_fingerprint` と施設IDが揃っていることを確認する。
- Stage 7のP0=1/P1=9/P2=24は**位置の優先調査順であって、施設の安全判定ではない**。作業結果の根拠資料の発見は、地域の避難先掲載の権限を一切意味しない。

~~~sh
cd ~/Developer/HINANEX
git fetch origin
git switch feature/d-nagoya-team-review-json-20261022
cd pipeline
source .venv/bin/activate
python export_nagoya_team_review_json.py --pilot-dir data/geocoding_pilot/nagoya50
# 同じフォルダ内の team_review_p1_LOCAL.json を本人判断で班員へ配布
# 別のDraft PR #292から単体HTMLだけ取得（PRIVATE CSVは一切コピーしない）
git show origin/feature/b-offline-team-review-20261022:frontend/team-review.html > data/geocoding_pilot/nagoya50/team-review.html
open data/geocoding_pilot/nagoya50/team-review.html
~~~

実データの配布可否はレビュー結果の根拠となるライセンス・利用条件および班内の取扱い方針を人間が確認。データを公開サイトへアップロードしない。

### P1公式一覧の事前照合と班員JSON統合（2026-10-22）

- 名古屋市の公式一覧は**2026年9月1日時点**。公開ページ自体は2026-10-07更新。区別屋内施設PDFを2026-10-22に参照し、対象P1**9施設の施設名・掲載住所の一致を個別に確認**。天白3、守山3、緑1、東1、中村1。元資料は CC BY 4.0、出典は「名古屋市 指定緊急避難場所・指定避難所の指定」（`https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html`）。公式資料の「指定」と実際の開設・避難適合・建物入口を混同しない。
- `pipeline/nagoya_team_review_official_sources.py` は**公式に公開された施設名・住所・区別PDF URLだけ**の厳格な一致インデックス。個別施設名と住所の双方が一致した場合だけ、該当区PDFリンクを配布用JSON `sources[]` に付与する。部分一致や名称のみでは自動登録しない。時点の固定情報であり公式PDFの将来の変更監視・再検証は行わない。
- `review.status`・全確認チェックは**未確認のまま**。公式資料に名前があることは位置の独立した承認や運用状況・安全性の判断根拠にはならない。候補座標やprivate監査列を共有JSONへ移さない。
- 以前の `team_review_p1_LOCAL.json` を作ったMacでは、**既存ファイルを残して新しい名前で生成**する。記録済みの提出結果を上書きしないため `--output-name team_review_p1_sources_LOCAL.json` を新設（フォルダ移動できない単純なgitignoredファイル名のみ許可）。
- B側Draft PR #292は「未確認・出典不足のみ表示」・P0/P1/P2要確認理由の説明・最大20ファイルの**全件原子的な結果JSON統合**を追加。基準JSONの施設ID・名称・住所・優先度・要確認コード・元ソースSHAが同じかチェックし、同じ施設の異なる記録は競合として**一切統合せず**報告する。既存班員版から基準版へ**確認メモ等だけ**反映し、公式リンクは基準版に残す。
- CI成功でも人間の出典原文確認・Windows Edge/Mac Safariでの読込・再エクスポート・再インポートを経るまで受け入れ確定しない。PR #283 → #293 の依存関係・PR #292 の静的UI統合を慎重に扱う。Render/main自動公開はしない。

~~~sh
cd ~/Developer/HINANEX
git fetch origin refs/pull/293/head
# 既存の実行ファイルに触れず、新しいv2スクリプトへ取得（失敗時には配置しない）
if git show FETCH_HEAD:pipeline/export_nagoya_team_review_json.py > pipeline/export_nagoya_team_review_json_v2.py.tmp &&
   test -s pipeline/export_nagoya_team_review_json_v2.py.tmp; then
  mv pipeline/export_nagoya_team_review_json_v2.py.tmp pipeline/export_nagoya_team_review_json_v2.py
else
  rm -f pipeline/export_nagoya_team_review_json_v2.py.tmp
  echo "PR #293 exporter取得失敗"; exit 1
fi
if git show FETCH_HEAD:pipeline/nagoya_team_review_official_sources.py > pipeline/nagoya_team_review_official_sources.py.tmp &&
   test -s pipeline/nagoya_team_review_official_sources.py.tmp; then
  mv pipeline/nagoya_team_review_official_sources.py.tmp pipeline/nagoya_team_review_official_sources.py
else
  rm -f pipeline/nagoya_team_review_official_sources.py.tmp
  echo "公式出典インデックス取得失敗"; exit 1
fi
cd pipeline
source .venv/bin/activate
python export_nagoya_team_review_json_v2.py --pilot-dir data/geocoding_pilot/nagoya50 --output-name team_review_p1_sources_LOCAL.json
# B側の最新単体HTMLを、別ファイル名で取得。既存のJSON/HTMLを上書きしない
cd ..
git fetch origin refs/pull/292/head
if git show FETCH_HEAD:frontend/team-review.html > pipeline/data/geocoding_pilot/nagoya50/team-review-v2.html.tmp &&
   test -s pipeline/data/geocoding_pilot/nagoya50/team-review-v2.html.tmp; then
  mv pipeline/data/geocoding_pilot/nagoya50/team-review-v2.html.tmp pipeline/data/geocoding_pilot/nagoya50/team-review-v2.html
  open -a Safari pipeline/data/geocoding_pilot/nagoya50/team-review-v2.html
fi
~~~

HTMLでは `team_review_p1_sources_LOCAL.json` を基準に読み込んだ後、古い班員提出JSONを「班員の結果JSONをまとめて取り込む」でインポート。競合がなければ別名で出力する。**配布前にJSON内容・公式一覧の使用条件・配布権限を本人が確認**する。

### 公式区別PDFのバイト更新検知（独立オペレーター実行、2026-10-22）

`pipeline/check_nagoya_official_pdf_updates.py` は、既存P1・9施設の資料としてリンク登録済みの名古屋市**5区の公開PDF**だけを対象とする。URLはD側で固定した allowlist のみ。自動スケジュール・外部公開・Gitコミット・施設位置や安全性の自動承認は行わない。取得失敗、リダイレクト、意図しないContent-Type、PDFでない応答、12MiB超はfail-closedでレポート更新しない。個人がローカル環境で明示実行したときだけHTTPSで取得する。

最初に基準（**未審査のバイト列スナップショット**）を取得。その後で再取得と比較を行う。基準自体が正しい版かどうか、PDF本文が人の意味上変わったかどうかは**別途レビュー**。以前の基準に比較しない初回取得は変更検出ではない。

```bash
cd ~/Developer/HINANEX
git fetch origin refs/pull/295/head     # D公式PDF更新差分PR
# 必ず取得元・内容・ファイルサイズを確認し、既存ファイルを上書きしない
git show FETCH_HEAD:pipeline/check_nagoya_official_pdf_updates.py > pipeline/check_nagoya_official_pdf_updates.py.tmp
test -s pipeline/check_nagoya_official_pdf_updates.py.tmp && mv pipeline/check_nagoya_official_pdf_updates.py.tmp pipeline/check_nagoya_official_pdf_updates.py
cd pipeline
python check_nagoya_official_pdf_updates.py --mode baseline --pilot-dir data/geocoding_pilot/nagoya50
python check_nagoya_official_pdf_updates.py --mode compare --pilot-dir data/geocoding_pilot/nagoya50
```

- 初回：`official_pdf_snapshot_LOCAL.json`。2回目：`official_pdf_comparison_LOCAL.json`。既存ファイルの上書きは禁止。3回目以降は `--output-name official_pdf_comparison_day3_LOCAL.json` 等を明示する。
- 差分があれば `SOURCE_BYTES_CHANGED_REVIEW_REQUIRED`。一致していても `SOURCE_BYTES_UNCHANGED_CONTENT_NOT_VERIFIED`（公的意味・指定・開設や実地点の安全性は未評価）。
- 比較レポートには区名・固定公式URL・変更真偽・前後SHA256・前後のバイト数・取得日時・常に偽の安全ゲートだけを記録する。PDF原文ファイルは自動保存・配布しない。
- 自動巡回・PDF版管理・ページ別意味差分・班員通知は**Future Design**。バイト差分検出成功は「公式名簿の内容変更」の立証ではない。ネットワークを使う実行とオフラインCIテストを混同しない。
- 前提はD段階PR #283 → #293 → 本機能PR。main/Renderや既存Stage7 PRIVATE資産・D RegionExportは変更しない。

## 発表質問への回答例

「名古屋市の屋内施設の住所情報は取得できていますが、緯度経度の列はありません。そこで住所から座標候補を得る実験用のパイプラインを追加しました。候補点と公式施設座標は区別し、変換時の位置精度・版・不一致を記録します。座標が付いただけでは避難時の安全性・施設の開設状態・経路の通行可能性は証明できないため、正式な地図表示への自動昇格は行っていません。」
