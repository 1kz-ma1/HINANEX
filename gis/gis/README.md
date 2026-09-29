# E — GIS / Map

D担当が生成する `pipeline/data/output/{region}.json`（RegionExport schema 0.9）を読み込み、位置情報を地図へ可視化するE担当のMVPです。

## 起動

`file://` 直開きではブラウザのOrigin制約によりD出力の相対fetchができないため、リポジトリrootからHTTP配信してください。

```powershell
cd HINANEX
python -m http.server 8000
```

ブラウザで `http://localhost:8000/gis/gis/` を開きます。

Dのruntime outputが未生成の場合は、D側で `python run_all_workflows.py` を実行するか、画面の「JSONを選択」からRegionExportを読み込めます。

## 表示レイヤー

- 背景地図: 国土地理院・地理院タイル
- 洪水参照: ハザードマップポータルサイト「洪水浸水想定区域（想定最大規模）」
- 自治体境界: 表示確認用fixture（分析正本ではない）
- 避難所: D `shelter_location` recordsのうち、緯度・経度が両方存在するrecordのみ

座標欠損recordは捨てず、全records数・地図表示数・座標欠損数をUIへ表示します。E側では住所からの暗黙geocodingやハザード区分の独自推定を行いません。

詳細仕様は `../E_GIS_SPEC.md` を参照してください。
