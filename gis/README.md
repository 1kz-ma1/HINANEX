# HINANEX — E / GIS

`gis/` は E担当（GIS / Map / 空間可視化）の領域です。

実装入口は `gis/` サブディレクトリです。

- UI / 起動方法: `gis/README.md`
- E仕様: `E_GIS_SPEC.md`
- テスト: `tests/`

Dの `RegionExport` をconsumerとして利用し、自治体固有Rawデータの解釈や暗黙geocodingは行いません。
