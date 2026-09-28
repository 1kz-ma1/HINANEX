# HINANEX Niigata repair patch for v0.8

現在のプロジェクトから v0.6 固有の新潟市ファイルだけが欠落していたため、それだけを復旧するパッチです。

追加されるファイル:
- run_niigata_workflow.py
- src/hinanex/adapters/niigata_shelter.py
- tests/test_niigata_adapter.py

既存の v0.7/v0.8 の共通ファイルは上書きしません。

適用後:
python run_niigata_workflow.py
python build_region_contracts.py
python -m unittest discover -s tests -v
