# HINANEX D担当 MVP 完了条件 v0.9

D担当の「中間発表MVP向け基盤実装」は、以下をすべて満たした時点で完了とする。

## 必須条件

1. 江戸川区・新潟市・名古屋市の3地域で公式データ取得workflowが実行できる。
2. 各地域で Raw -> Normalize -> Assessment -> Capability -> Gap -> Recommendation が生成できる。
3. B向けの1地域1JSONを3地域すべて生成できる。
4. 3地域JSONが同一のRegionExport Schemaに適合する。
5. CがSourceからRecommendationまで判定根拠を追跡できる。
6. `manifest.json` が生成できる。
7. 全ユニット/回帰テストが成功する。
8. `python run_all_workflows.py` で全工程を再現できる。

## 完了後にDが担当するもの

ここから先は「Dの新規基盤開発」ではなく統合作業として扱う。

- Aが追加した公式データソース用Adapter追加/修正
- BとのJSON契約結合で発見した不具合修正
- Cの人手検証で発見した評価ルールの修正
- EのGIS利用で必要になった正規化項目の調整

## 今後の拡張候補（MVP完了条件には含めない）

- shelter_disaster_compatibility
- shelter_accessibility
- shelter_capacity
- flood hazard / inundation depth
- Population Exposure Analysis
- 複数Capabilityの総合Data Gap分析

MVP完了前にこれらへ広げず、まず現在の縦パイプラインをIntegration Readyに保つ。
