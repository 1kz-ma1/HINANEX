# OSM 4施設の敷地・入口**候補原本**取得（A研究、2026-10-27）

**STATUS: 設計・合成テスト段階。外部Overpassの実データはこのPRで取得していない。**

## 入力となる真正の既存GSI原本
[Actions #40258746945](https://github.com/1kz-ma1/HINANEX/actions/runs/40258746945) の `skhb02-10-909-403.geojson`（800 Features、SHA-256 `cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84`）だけから4地点の座標を読み出す。対象 index 571 江戸川河川敷緑地、639 須和田公園、682 大洲防災公園、707 筑波大学附属聴覚特別支援学校（グラウンド等）。

**取得するのは「GSI参考点の半径300m以内にあるかもしれないOSM地物」の候補**。範囲外の公園全域・離れた入口を網羅しない。結果0は候補未発見であり施設なし・入口なしの意味ではない。施設の境界も安全な集合地点も生成しない。

- OSM: https://www.openstreetmap.org/copyright （**ODbL 1.0、© OpenStreetMap contributors**）。公開データだが出典表示、共有・翻案時のライセンス確認が必要。一般のOSMタグから避難時に通れるとは判断しない。
- Overpassの公開インスタンス: https://overpass-api.de/api/interpreter 。クエリ1本、半径300m×4点、入口node + 公園/学校等のway/relationに限定。リクエスト/サーバーのサイズと時間を制限。429/504等は自動再試行しない。出典が落ちても避難場所0件にはしない。
- GSI注意: https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html 。GSI原本とOSMの出典・ライセンスは別に保全。
- OSM原本のJSONは**GeoJSONではない**。way/relationのgeometryを勝手に単純なPolygonに変換せず、そのまま証拠として置く。
- 名前、住所、敷地、入口の同一性/安全性は全部false。query原文・sha、raw response・sha、HTTP観測、照合前の4参照点、ODbL帰属表示を保全する。

手動ローカル起動例（Git管理外の保存先）：

```bash
python data-research/tools/capture_osm_four_site_candidates.py \
  --gsi-raw /outside-repo/skhb02-10-909-403.geojson \
  --out-dir /outside-repo/osm-four-sites-UNREVIEWED \
  --fetch --acknowledged-osm-license --acknowledged-gsi-notice
```

未検証：①取得したOSM地物の施設所属、②データ鮮度、③敷地・入口が網羅されるか、④自治体の公式指定場所の範囲、⑤水害時の危険・入口アクセス。C独立審査とD #317/#318への照合は**別PR**で実施し、OSMノードを直ちに `navigation_endpoint` に入れない。

原本の手元保存は限られた期間のみ。GSI原本のGitHub Actions artifactは2026-10-29頃期限、ローカルに既存アーカイブがある場合はそれを再使用。新しいGSIタイルの自動再取得は設計にない。

## 2026-10-27 初回の手動実行と障害の切り分け

- [Actions #40449512069](https://github.com/1kz-ma1/HINANEX/actions/runs/40449512069) にて、`main` の指定、OSM/GSIの2種類の明示確認、保存済みGSI原本取得とファイル存在検査はPASS。
- 取得ステップのみ `OSM_REQUEST_FAILED_NO_AUTOMATIC_RETRY` でFAILED。旧版はHTTPコードと通信例外種別を同じコードに潰しており、**実際の失敗原因は不明**。監査・候補抽出・原本アップロードは未実行、OSM実原本は存在しない。
- この改修は、HTTPでは`OSM_HTTP_STATUS_<code>_NO_AUTOMATIC_RETRY`、通信では`OSM_TRANSPORT_TLS/TIMEOUT/DNS/CONNECTION_REFUSED/UNKNOWN_NO_AUTOMATIC_RETRY`または`OSM_TRANSPORT_OS_ERROR_NO_AUTOMATIC_RETRY`を出すだけ。**秘密情報を含みうるエラー本文、例外reason、ネットワークURL、レスポンス本文はログに書き出さない**。
- 取得先 `https://overpass-api.de/api/interpreter`、固定の4点・300mクエリ、TLS検証・リダイレクト拒否、原本GSI SHA、承認用ブール入力、再試行禁止、原本アーティファクト構成は**変更しない**。
- 実行の再試行は自動化せず、人間の新たな明示的判断に委ねる。HTTP 429/504等が出ても自動で接続先を切り替えない。取得先が受け付けない場合も、施設・避難可能性をゼロと推定しない。
- 本改修のテストは疑似例外を使用するオフライン単体テスト。HTTP 400/403/429/500/504、TLS/DNS/timeout/接続拒否を検査するが、実接続成功の証明ではない。期限は元のGSI artifact 2026-10-29 11:22:16 JST。
