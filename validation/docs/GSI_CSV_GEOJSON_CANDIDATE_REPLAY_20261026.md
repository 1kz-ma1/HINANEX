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
## 2026-10-27 実原本A/C候補照合・座標桁数差の検証

- GSI全国CSV: [Actions #40426421393](https://github.com/1kz-ma1/HINANEX/actions/runs/40426421393)、HTTP 200、UTF-8 BOM・17列（ヘッダーあり）、**115,925データ行**、原本17,010,296バイト、SHA256 `7e3078fdf52cc25703aa06ad4bbbe168e88e14c66f1d6cf97c720a38414b94fc`。Aの検査は土砂災害指定1が67,458、共通ID入力115,925、重複共通ID0。
- GSI skhb02 GeoJSON: [Actions #40258746945](https://github.com/1kz-ma1/HINANEX/actions/runs/40258746945)、原本SHA256 `cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84`、タイル内800件。
- CSVの市川市名の行 **126件**、うち土砂災害指定1 **93件**。GeoJSONの住所接頭辞が「千葉県市川市」の29件すべてで、CSVの同名候補が**各1件**、住所・指定フラグ完全一致、重複共通IDなし。
- CSV座標は小数点以下6桁より多い精度を持つ行がある。GeoJSON座標と数値完全一致は1件のみだが、**CSVの緯度・経度を各6小数桁に丸めると29/29一致**。最大数値差を緯度依存の平面近似に換算すると約0.0654m。丸め一致28、完全一致1。これは地点の安全性を表す距離ではない。
- 誤検出修正：旧C照合器では28件が `NAME_ADDRESS_AGREE_COORDINATES_DIFFER` になる。新分類 `TEXT_AND_COORDINATES_AGREE_AT_GSI_6DP_UNAPPROVED` は**入力GeoJSONが6小数桁以下**で、CSV高精度値を6桁に `ROUND_HALF_UP` した両座標が一致した場合のみ適用。わずかでも丸め閾値を超えた場合は従来どおり相違として報告し、距離閾値による曖昧承認はしない。変更後も共通IDはGeoJSONへ正式に結合しない。
- #571 江戸川河川敷緑地は全国CSV上の共通ID原文候補 `E1220300052201`、CSV/GSI GeoJSONの名称・住所・座標6桁丸め一致。**市川市PDFの所在地「市川南3・4丁目地先」との表示範囲差、および安全な入口・到達地点未検証は継続**。
- 取得ファイルのSHA一致は確認しているが、別時点のCSVとGeoJSONの版完全同期、自治体境界、C独立人間の承認、現在の開設、実際の災害時の安全・経路や入口は**未確認**。`navigation_endpoint=null`, `human_c_approved=false`, `navigation_allowed_count=0`を維持。
- 実原本の29件照合は読み取り専用のPython監査により行い、ZIP原本/派生ランタイムJSONはリポジトリにコミットしない。今回のPRの新ユニットテストは合成値で座標丸め境界を回帰検証する。**CI成功はこの実原本での本モジュール再実行を意味しない**。
