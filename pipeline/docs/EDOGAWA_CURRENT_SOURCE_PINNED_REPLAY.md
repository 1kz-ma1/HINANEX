# 江戸川区：現行Dの原本固定RegionExport再生成（2026-10-13）

目的：最新の江戸川区公式原本をA/Cと同じSHA256で固定し、Dの既存処理を **江戸川区だけ** オフライン再生する。過去のD JSONや再取得URLに依存させず、施設の洪水適合性も推測しない。

## 実行コマンド

7件の原本はshared PR #139のGitHub-hosted runnerで収集する。ZIP展開後の raw-unreviewed ディレクトリには municipal_locations.csv / water_facilities.html / snapshot_manifest.json を含む。

```powershell
cd pipeline
python run_edogawa_evidence_slice.py --archive-dir "C:\\HINANEX-evidence\\raw-unreviewed" --output-dir "C:\\HINANEX-evidence\\D-current-UNREVIEWED"
```

出力：edogawa_current_D_UNREVIEWED.json（現行1地域RegionExport）／edogawa_D_source_trace_report.json（採取原本のSHA256・Scenario集計）。出力フォルダは未作成または空とする。生原本・出力はGit管理外に保管する。

内部では、Dの既存 EdogawaShelterAdapter.normalize、assess_shelter_location、assess_shelter_discovery、analyze_capability_gap、edogawa_facts/evaluate_flood_scenario、build_region_export、assert_valid_region_exportを使用する。既存の本番data/output、B/Eの表示、他2地域、共有ContractやSchemaは変更しない。

## 実原本での結果

- 実行：https://github.com/1kz-ma1/HINANEX/actions/runs/38332536238
- 元の江戸川区位置CSV SHA256：64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea（152件）
- 公式水害HTML SHA256：96001e1a22cdc19580f0c4483e01f2f2e1e6d8b2c595ee5d751f24bf836d4deb（異なるsource。施設IDの自動joinをしない）
- 生成した現行RegionExport SHA256：c09a3913052412566825fbe6df57f165c5a334b4e7d781a6051e8e12bb80ad28
- 位置152件／一意な施設ID152件。2026-09の履歴Dの152件とID・名称・緯度経度・元URL・追加属性の差分0。
- 洪水Scenario 1件。全152件 join_status=UNVERIFIED、status=UNKNOWN。CANDIDATE/EXCLUDEDとも0件、公式災害適用rawを推測補完していない。
- shelter_discoveryはFULLだが **位置ベース探索能力の指標**。洪水適合性・実際の開設状況・避難安全性を保証しない。
- PR #133のA提案スクリプト→PR #136のC独立検証スクリプトを同じrunnerで実行。C source-to-output監査111水害行、152元位置行、A候補56/52/3を確認。A/C結果は未承認のまま。

## 制約と統合条件

今回の結果はGitHub Actionsの **非公開UNREVIEWEDアーティファクト**にのみ格納され、mainやRenderには反映されていない。3地域フルrun_all_workflows、Cの人手による物理施設同一性承認、D/Cの洪水単独意味論、ステージングの画面受入は別工程。

担当順：#139原本→#140 D再生成→#133 A候補→#136 C独立照合→人間Cによる正式サイト照合→D/C水害待避と洪水単独の審査。**安全判定0件のまま承認済みへ格上げしない。**
