# 江戸川区 shelter_location — C担当の初回検証記録

- 検証日: 2026-09-29
- 対象: 東京都江戸川区（13123） / `shelter_location`
- コード基準: `main` commit `da0a11cb3a8299e11e3da6e4780bfbc882e662ff` のZIP
- 判定: **valid（今回確認した範囲）**。公式CSVと正規化結果の名称・緯度・経度、および評価のnull/0区別を確認。
- 注意: 全施設の現地での実在性、座標の地理的正確性、災害別適合性、安全性は確認していない。

## Source / Evidence

公式掲載ページ: https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html  
取得CSV: https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv

公式ページには「避難所・避難所補完施設（CSV）」が掲載され、防災データ欄の更新日は2025年12月11日。2026-09-29にAdapterの取得先からCSVを取得した。

- CSV: 24,777 bytes / SHA-256 `64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea`
- 列: `名称`, `URL`, `災害種別記号`, `コメント`, `緯度`, `経度`
- 元CSV: 152行。名称・緯度・経度の欠損はそれぞれ0件。
- `pipeline/run_edogawa.py` の出力: 正規化レコード152件。
- 独立したCSV/JSON比較で152件すべての名称、緯度、経度が行順で一致。正規化IDの重複は0件。
- `capacity`, `accessibility`, `supported_disasters` は各152件とも `null`。元CSVだけでは確定できない値を推測していない。

Evidenceには公式掲載ページ、提供者、CSV形式、取得方法、取得時刻が記録されている。江戸川区のオープンデータ利用条件ページ（https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/index.html）は、個別の指定がない公開データを「クリエイティブ・コモンズ表示2.1日本」で提供すると明記する。地図データページにはCC-BY表示があり、今回のCSVについて個別の別ライセンスは確認されなかったため、Adapterの `CC BY 2.1 JP` 表記には根拠がある。地図データの2025-12-11は公式ページで「更新日」と表示される。Adapterは同日をEvidenceの `published_at` に記録するが、初回公開日とは確認できない。このフィールドが最終更新日を含む設計かどうか、D担当/Contractとの意味確認が必要。

## Assessment / Capability / Gap

`python assess_edogawa.py`、`python assess_edogawa_capability.py`、`python analyze_edogawa_gap.py` を実行した。

| 項目 | 実際の出力 | 確認 |
| --- | --- | --- |
| `record_count` | 152 | 元CSVと一致 |
| Completeness / Validity | 4 / 4 | 名称と座標の欠損0件、範囲チェック対象あり |
| Machine Readability / Geospatial Usability | 4 / 4 | CSVとして取得・正規化、座標全件あり |
| Coverage / Timeliness / Traceability等の未評価項目 | `null` | 0へ置き換わっていない |
| Shelter Discovery | `FULL` | `shelter_location` の位置情報についての限定的な判定 |
| Gap / Recommendation | 0 / 0 | 現在のShelter Discoveryルールにおける出力 |

`build_region_export_from_paths` で1地域のRegionExportも組み立て、dataset 1、assessment 1、capability 1、gap 0、recommendation 0、evidence 1を確認。dataset、assessment、capability dependency の `requirement_code` はすべて `shelter_location`。

`FULL` はこのCapabilityの現在の位置情報要件に対する状態であり、災害別の安全な避難所選定やバリアフリー適合性まで保証しない。

## テスト結果

`pipeline/` から次を実行:

```text
python -m unittest tests.test_shelter_location_assessment tests.test_capability tests.test_gap tests.test_export -v
Ran 23 tests — OK
```

既存テストには座標欠損時の `validity.score is None`、0の確定ブロッカー、未評価メトリクスのUNKNOWN、NOT_FOUNDを自治体未公開と断定しないケースが含まれる。全リポジトリのテストは今回実行していない。

## 残る確認

1. `published_at` が公式ページの「更新日」を表してよいか、D担当/Contractで確認する。初回公開日と断定しない。
2. 別ソースまたは現地情報と施設の実在性・位置の地理的正確性を照合する場合は、独立した検証として記録する。
3. 他地域や他DataRequirementに今回の結果を一般化しない。

Raw CSVと生成JSONは実行時データであり、このPRにはコミットしていない。
