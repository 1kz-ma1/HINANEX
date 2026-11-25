# 市川市4施設 OSM原本の「観測位置」別レビューキュー（A、2026-10-27）

**本処理は調査候補の機械的な仕分けだけを行う。施設同一性・敷地・入口・災害時の安全性・経路・開設の承認ではない。利用者向け公開は禁止。**

## 目的

- 手動取得 #327、独立監査 #329 と監査ゲート #330 が生成する原本5ファイルを入力する。
- A 独立監査の SHA・固定GSI原本・4地点・固定Overpassクエリ・OSMライセンス・未承認状態の検査が **PASS した場合のみ**、未検証OSM要素を `node/way/relation` のIDを変えずレビュー用に列挙する。
- GSI参考座標に対してOSM原本に**実際に記録された座標点**のいずれかが300m以内にある場合に限り、対象参考点の `observed_vicinity` キューへ並べる。距離は球面近似による「観測された点までの距離」であり、敷地境界や実際の歩行距離ではない。
- wayの記録点やrelationのmember geometryだけを扱い、敷地が点を含むかどうかのPolygon判定、OSM名寄せ、入口の許可、所有者/運営者判定、GIS経路判定は実施しない。大規模公園・河川敷では施設範囲をこの情報だけで評価できない。
- 1つのOSM要素は複数の参考点に重複掲載できる。ただし各行の `associated_gsi_feature_index` は常に `null`。それぞれの参考点リストは「同一施設」を意味しない。
- 原本に有効座標がないものは `no_observed_coordinates_needing_review`、4地点の300m内に近い**観測点がない**ものは `not_near_any_observed_vertex_needing_review` に残す。どちらも除外確定ではなく**要審査**。0件は施設・敷地・入口が存在しない根拠ではない。

## 入出力と運用

```bash
python data-research/tools/triage_osm_four_site_raw_vicinity.py \
  --evidence-dir /outside-repo/osm-4-ichikawa-UNREVIEWED \
  > /outside-repo/osm-vicinity-review-UNREVIEWED.json
```

- **入力**: GitHub管理外に展開した **5ファイルだけ** の原本ディレクトリ。実行のたび独立監査を再実行し、失敗なら終了コード2でBLOCK。元原本とmanifestを書き換えない。出力は標準出力へJSONのみ。
- **出力**: 4参考点別の非排他的な候補一覧、座標なし要素、観測点上は近くない要素、元原本SHA、OSM出典・ライセンス、全承認フラグfalse。
- **禁止**: 未審査の情報を `facility_geometry`・`navigation_endpoint`・RegionExport・GIS・公開APIへ自動反映しない。#571 江戸川河川敷緑地の所在地・入口不一致は本処理の結果にかかわらずHOLD。
- **制限**: 観測座標点しか距離を見ないため、線分が付近を横断・Polygonが参考点を包含しても近接判定できない場合がある。近接の有無と実際の到達可否は別問題。OSM `entrance=main` と `access=yes` も承認根拠ではない。任意の取得欠損やバージョンの継続性を保証しない。
- **安全境界**: `OSM_FOUR_SITE_OBSERVED_VICINITY_UNREVIEWED` 状態のみを出し、`candidate_to_official_facility_identity_verified=false`、`human_c_approved=false`、`navigation_allowed=false`、`may_publish_or_route=false`。現行D #317/#318には直接接続しない。

## 検証とリリース判断

`python -m unittest discover -s data-research/tests -p 'test_triage_osm_four_site_raw_vicinity.py' -v`。

実データ取得・実OSM原本・4施設との同一性検証は未実行。既存のGSI保存原本には別途SHA監査証跡があるが、OSMが未取得なのでこのツールの実原本への適用はまだ不可。実OSM取得後は、A原本監査とCの独立した同一性/入口/災害別評価を順に実施する。運用チケット: [#328](https://github.com/1kz-ma1/HINANEX/issues/328)。

**スコープ**: `data-research/**`のみ。RegionExport契約変更なし。Render/GIS UI/既存手動ワークフローに変更なし。