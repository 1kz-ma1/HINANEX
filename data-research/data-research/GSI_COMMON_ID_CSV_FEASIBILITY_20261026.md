# GSI CSVの共通ID：原文保全と列順検査（2026-10-26）

**A-only構造検査・未承認。公式CSV原本はこのPRで取得していない。**

出典: [国土地理院 指定緊急避難場所データのCSV列定義](https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html)。`全国共通避難所・避難場所ID（共通ID）`は公式列として示されている。ただしCSVとGeoJSONの行がIDで同一視できるとは、この仕様だけからは証明できない。

- 全国版17列。都道府県/市町村版16列（施設の「都道府県名及び市町村名」列がない）。全て**指定緊急避難場所用**の列順であり、「指定避難所」用CSVとは混同しない。
- `common_id_raw`は文字列として保持し先頭ゼロを保全。空なら`null`（推測して補わない）。重複していたら要確認のままで自動上書きやJoinをしない。
- `landslide_designation_marker_raw=1`は「崖崩れ、土石流及び地滑り」指定というCSVの元値。空欄は空欄のまま（施設に対応しない災害という市の決定への一般化を避ける）。
- 地理座標はCSVの文字列精度を保存。欠損は`null`で、端末の位置やGeoJSON代表座標から補完しない。
- UTF-8(BOM対応) またはCP932は人間の指定した`--encoding`で検査。文字コードや版を自動推測しない。
- 解析結果は`GSI_CSV_ARCHIVE_INSPECTED_UNREVIEWED`。原本と出典URL、取得時刻、HTTP情報などは別の取得証跡で管理する。ここでの原本SHA256は入力ファイルのビット単位の要約に過ぎず、公式HTTPS真正性を証明しない。

## 操作例（正式原本が端末に別途取得されてから）

```bash
python data-research/tools/inspect_gsi_emergency_csv_archive.py \
 --archive /outside-repo/official-municipality.csv \
 --scope municipality --encoding utf-8-sig \
 --report-out /outside-repo/gsi_csv_id_UNREVIEWED.json
```

この手順はネットワークに接続しない。CSVファイルの取得場所・利用条件・更新日の記録、人間とCによる原文監査を別に実施する。CSVの`NO`や共通IDを他版のGSI GeoJSON index/施設と自動対応づけない。C #316の29件を名前だけで結合しない。

実データ受入前に、正式取得した市川市CSV（存在・公開・形式の確認）、出典バイトハッシュ、スキーマ/ライセンスの版をCが独立検証し、必要なら別PRで候補IDの突合・衝突レポートを作る。そのレポートがあっても入口や避難安全性とは別。

**テスト:** `python -m unittest discover -s data-research/tests -p 'test_inspect_gsi_emergency_csv_archive.py' -v`（合成CSVのみ）。変更範囲はdata-research/**で、D/C/E/RegionExport/本番データ変更なし。
