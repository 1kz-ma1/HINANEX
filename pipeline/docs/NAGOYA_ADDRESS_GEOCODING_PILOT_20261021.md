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
- ABRのhealth、API版、DB版、対象pref=23、category=allを検証。元の37応答のSHA256が一致しなければ停止する。古い出力を上書きせず、診断レポートを新規作成する。
- HTTPはlocalhost限定、リダイレクト拒否、proxy不使用。**個別の名前・ID・住所・住所候補・座標・レスポンスは出力せず**、gitignoredの`mismatch_diagnostics_aggregate.json`と標準出力に匿名件数のみ記録。
- 診断区分は次の4つ。これらは**文字列の観測パターン**であって原因・精度・施設位置の確定分類ではない。
  - `source_suffix_not_matched`: ABR住所が元の住所の前方部分で止まる
  - `provider_has_extra_suffix`: ABR住所側に追加の末尾がある
  - `same_text_stem_number_difference`: 最初の数字より前の文字列は一致し、数字以降に相違がある
  - `town_or_other_text_difference`: 上記以外の住所文字列差
- 住居表示・地番体系の違い、真の番地違い、施設の位置誤差はこの機械的分類では確定できない。必要に応じて**ローカル限定**の公式施設位置資料による人間の独立照合で判別する。
- データの選定、元の50件ステータス、`UNVERIFIED_CANDIDATE`6件、施設位置受入0件、`approved_for_map=false`を一切変えない。RegionExport / GIS / 災害適合判定 / 正式座標には接続しない。
- Issue #286へはこの匿名化した集計と実測上の制約だけを掲載し、施設単位の内容や`human_review.csv`は絶対にコミット・投稿しない。
- 原本16ファイルのURL/取得時間帯/SHA256は個別のローカル監査記録で確認すること。元の実測集計に含まれていない場合は記録済みと断定しない。

## 発表質問への回答例

「名古屋市の屋内施設の住所情報は取得できていますが、緯度経度の列はありません。そこで住所から座標候補を得る実験用のパイプラインを追加しました。候補点と公式施設座標は区別し、変換時の位置精度・版・不一致を記録します。座標が付いただけでは避難時の安全性・施設の開設状態・経路の通行可能性は証明できないため、正式な地図表示への自動昇格は行っていません。」
