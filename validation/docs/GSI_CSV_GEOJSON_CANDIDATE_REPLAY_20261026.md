# GSI CSVとGeoJSONの独立候補照合（C内部・2026-10-26）

状態: C_GSI_CSV_GEOJSON_CANDIDATES_UNAPPROVED。新しい実CSVを取得していないため実データ照合は未実施。
公式CSV定義: https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html

このC実装は元のCSVファイルバイトとGeoJSONファイルバイトを再読し、指定された各SHA256と照合したうえで候補を抽出する。Aの#319のコード/出力に依存せず、全国17列・市町村/都道府県16列の違いを独立に検査する。

市川市の名前・住所・座標を自動比較する。結果は名前なし、同名複数、住所差、土砂災害フラグ不一致、座標差、文字列座標一致を区別。共通IDはCSV原文のまま表示するが、GSIタイルPointへの結合を承認しない。CSVの全国/市町村スコープ自体も別途真正性監査を要する。

元のタイル原本は https://github.com/1kz-ma1/HINANEX/actions/runs/40258746945 に取得証跡がある。GeoJSONの固定SHAは cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84。CSVは未取得。GitHub Actionsの成果物期限に注意。

実際のCSVが手元に取得された場合は独立監査・出典証跡が必要。次のコマンド例で --expected-csv-sha256 に実原本から記録した値を明示する：

python validation/validation/compare_gsi_csv_geojson_candidates.py --gsi-raw /outside/skhb02.geojson --csv-raw /outside/official.csv --expected-gsi-sha256 cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84 --expected-csv-sha256 ACTUAL_SHA256 --csv-scope national --out /outside/csv_geojson_C_UNAPPROVED.json

CSVが本当に国土地理院から正しく取得されたか、CSV版とGeoJSON版が同期しているか、市町村の指定/開設の最新状況、公式共通IDのGeoJSON側レコード同一性、入口、歩行路の安全性は本比較だけでは確定できない。
全件で common_id_to_geojson_verified=false、human_c_approved=false、navigation_allowed_count=0、safe_destinations_approved=0。

本PRはvalidation/**のみ。RegionExport、D/E、GIS、本番変更なし。合成入力のCI成功は実29件のCSV照合成功を意味しない。