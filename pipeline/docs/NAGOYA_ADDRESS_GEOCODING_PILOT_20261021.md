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

## 判定区分

- UNVERIFIED_CANDIDATE: 一意の座標候補、区と住所が一致、住宅番号・街区・地番相当の精度。ただし独立した施設位置確認は未実施で、GIS公開不可。
- NEEDS_REVIEW: 異なる元レコードが同じ代表座標を持つ等の要検証。
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
4. **外部公開の禁止:** 公式のDocker Composeは設定によって全インターフェースに公開され得る。Docker Compose overrideで、ABR APIはホストバインド127.0.0.1:3000:3000に、PostgreSQLも127.0.0.1のみに制限してから起動する。LAN・公衆ネットワークへの公開を行わない。
5. HINANEXのpipeline/から、隔離環境に保存された公式名古屋市Excel由来のdata/normalized/nagoya_shelters.jsonを使う。必要なら既存の run_nagoya_workflow.py を明示実行する。元の原本・取得日・ハッシュを別記録に残す。
6. 同一データスナップショットで以下を順番に実行する。

    python geocode_nagoya_pilot.py prepare --dataset data/normalized/nagoya_shelters.json --out data/geocoding_pilot/nagoya50
    python geocode_nagoya_pilot.py resolve --dataset data/normalized/nagoya_shelters.json --out data/geocoding_pilot/nagoya50 --local-abr-url http://127.0.0.1:3000
    python report_nagoya_geocoding_pilot.py --pilot-dir data/geocoding_pilot/nagoya50

7. 結果はgitignoredのdata/geocoding_pilot/nagoya50に保存される。summary.jsonとhuman_review.csvはGitにコミットしない。2回目の実験では上書きせず別フォルダを使う。

### 発表のための実データ診断と独立承認

- summary.json: 最大50件の対象数、UNVERIFIED_CANDIDATE比率、要レビュー・未解決・プロバイダ失敗数、座標精度、区別のサンプル数を集計。**候補取得率は位置精度や施設同一性の確認率ではない**。
- human_review.csv: 元ID、施設名、原本住所、候補緯度経度に対して、公式位置資料のURL、施設同一性、精度を人が確認するための空欄を持つ。全件NOT_REVIEWEDで生成。
- 公式施設座標として受入済みの件数は常に0、全件approved_for_map=false。実際の照合と公開向け地図への使用判断は別の受入ゲートとする。
- GithubのCIは合成データで分類と集計ロジックを試験するのみ。**愛知県ABR実データによる50件変換と現地座標の比較は未実施**であり、実変換成功率を推測しない。

## 受入・検証

- Pythonの単体テストは合成データのみで行い、正例に加えて別区、複数候補、低精度、NaN、重複ID、旧データ、外部ホストを拒否する。
- 手動の実データ実験で50件の変換候補数、区別の未解決理由、精度分布、公式施設地図との位置誤差、同一点重複などを集計し、PASS/LIMITATION/NOT TESTEDを分離する。
- ローカルABR本番データのセットアップ、名古屋50件の実変換、実地施設との比較は現時点では未実施。合成テスト成功を実データの変換成功と表現しない。
- 作業中のUI改善とは切り分ける。こちらの試験結果を公開GISへ自動同期しない。
- 住所・ジオコーディングデータの利用許諾、最新性、公開範囲は実運用に入る前に別途検証する。

## 発表質問への回答例

「名古屋市の屋内施設の住所情報は取得できていますが、緯度経度の列はありません。そこで住所から座標候補を得る実験用のパイプラインを追加しました。候補点と公式施設座標は区別し、変換時の位置精度・版・不一致を記録します。座標が付いただけでは避難時の安全性・施設の開設状態・経路の通行可能性は証明できないため、正式な地図表示への自動昇格は行っていません。」
