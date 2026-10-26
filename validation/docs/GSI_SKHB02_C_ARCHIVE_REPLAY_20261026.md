# GSI skhb02 のC独立原本照合（2026-10-26）

状態：**独立したローカルの構造再検証。正式承認・公開不可。**

## 対象
AのDraft PR #310が出力した未承認の構造レポートと、保管された元GeoJSONバイトを独立に比較する。Aコードはimportせず、CがURL・出典ハッシュ・FeatureCollection・disaster2=1・元の施設名/座標/feature-indexと同じデータかを再検証する。

z10地理院タイルについて、点のWeb Mercator座標がタイル範囲内かを確認。タイルの範囲は市町村境界や危険区域ではない。タイルが空でも自治体に対象施設がないとは断定しない。

一致出力はC_LOCAL_MATCH_UNAPPROVEDまたはC_EMPTY_TILE_COVERAGE_UNKNOWNに固定。公式HTTPS取得の真正性、人間の独立審査、自治体掲載範囲、開設状況、避難行動の安全性、D/Eへの公開許可は一切承認しない。

## 実行
python validation/validation/verify_gsi_skhb02_archive.py --raw /outside-repo/skhb02.geojson --a-report /outside-repo/a-report.json --source-url https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson --report-out /outside-repo/c-report.json

このタイル番号はCLI書式の例であり、実際の地域掲載状況の証明ではない。既存出力は上書き拒否。

## 次の別工程
実原本の公式再取得・HTTPメタデータ/版固定・掲載市町村更新日・利用条件の確認、Cの実データ監査、人間による源/施設IDの確認、D/E公開ゲート。GSI指定緊急避難場所と土砂災害ハザード区域を混同しない。

合成テスト入口: python -m unittest discover -s validation/validation -p test_*.py -v。実原本の接続環境がないため、synthetic CI成功は地域別の受入を意味しない。