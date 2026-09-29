# 江戸川区 shelter_location — C担当の初回検証記録

- 記録日: 2026-09-29
- 対象: 東京都江戸川区（13123） / `shelter_location`
- レビュー対象: `main` commit `da0a11cb3a8299e11e3da6e4780bfbc882e662ff`
- 判定: **needs_review**（静的なルール確認は実施、実データ出力との照合は未実施）
- 方法: 公式掲載ページとリポジトリのAdapter・評価器・既存テストを確認。CSV本文、生成JSON、テスト実行結果は未確認。

## Source / Evidence

公式ページ: https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html

確認できた事実:
- 江戸川区の「地図データ」ページに「避難所・避難所補完施設（CSV）」へのリンクがある。
- 防災データ欄の更新日は2025年12月11日と表示されている。
- ページには緯度経度を含むCSV等として地図データを提供すると記載されている。

Adapter: `pipeline/src/hinanex/adapters/edogawa_shelter.py`

- AdapterのSOURCE_PAGE_URLは上記公式ページを指す。
- SOURCE_URLは `https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv` を指定する。
- `supported_disasters`, `accessibility`, `capacity` はこのCSVから確定しないため `None` としている。
- CSV本文の列、レコード数、緯度経度の値、ライセンスの厳密な表記はこのレビューでは照合していない。

## null と 0 の静的確認

評価器: `pipeline/src/hinanex/evaluation/shelter_location.py`

| ケース | 期待する意味 | コード上の扱い |
| --- | --- | --- |
| 名称・座標が揃ったレコードが0件 | Validityを判定できない | `validity.score = None` |
| 座標が欠けたレコードがある | Completeness / Geospatial Usabilityの不足 | 比率に応じて0〜4の評価 |
| 全レコードで座標が欠ける | 位置情報の利用条件を満たさない | `completeness.score = 0`、`geospatial_usability.score = 0`、`validity.score = None` |
| 取得・正規化レコードが0件 | 妥当性を判定できない | `validity.score = None`、`geospatial_usability.score = None` |

上記は「評価済みで要件未達」と「未評価」を分ける現在のContractと整合する。既存の `pipeline/tests/test_shelter_location_assessment.py` には、座標がすべて欠損する場合の `validity.score is None` などのテストがある。ただし、このレビューではテストを実行していない。

## 実データで残る確認

1. `pipeline/` で依存を導入し `python run_all_workflows.py` を実行する。
2. `data/normalized/edogawa_shelters.json` のEvidence・レコード数・座標欠損を公式CSVと照合する。
3. `data/output/edogawa.json` の `assessments` で、未評価の項目が0へ変換されていないか確認する。
4. `datasets[].evidence → assessments → capabilities → gaps → recommendations` を `requirement_code` / `capability_code` でたどり、断定に根拠があるか確認する。
5. 結果を `valid` / `needs_review` / `misclassified` に更新し、source・expected・actual・実行日を記録する。

**現時点で実データの正しさや全テスト成功は確認済みとしない。** `data/output/` の生成JSONはGit管理されていない。
