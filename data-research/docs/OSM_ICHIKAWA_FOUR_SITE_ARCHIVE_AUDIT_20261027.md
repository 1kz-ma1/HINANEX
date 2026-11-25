# 市川市4施設 OSM原本アーカイブのオフライン独立監査（A / 2026-10-27）

**対象は未審査の原本と取得証跡です。避難先の同一性、敷地、入口、安全性、開設状態、経路を承認しません。**

## 前提と範囲

- A #326 の固定4点OSM原本取得ツール、Shared #327 の `workflow_dispatch` 手動取得に続く、オフラインの第三者確認用処理。
- `OSM-Ichikawa-4-sites-UNREVIEWED` アーティファクトは手動取得が成功して初めて生まれる。2026-10-27時点で**実OSM取得未実施**。原本ZIPをGitにcommitしない。
- Git管理外に展開された原本5ファイルの完全性、サイズ、SHA-256、固定GSI GeoJSON SHA、800 Features、4施設のindex/名称/土砂指定/参考座標、固定OverpassQL原文、HTTP観測、ODbL帰属表示とすべてfalseの承認フラグを照合する。
- OSM node/way/relationの件数とID重複、原本に含まれる未検証のOSM snapshot時刻主張を検査する。ソースHTTP観測や時刻は**第三者署名による真正性確認ではない**。
- 取得できたOSM地物のID一覧は**全件を施設に未割当のまま保持**する（`associated_gsi_feature_index=null`）。半径300m内にあっても施設同一性を自動判定せず、`navigation_allowed=false`を固定する。
- 0件は「この取得経路で候補が見つからなかった」だけで、施設・入口の不存在を意味しない。

## 使用方法

既に取得したActionsアーティファクトの内容を**リポジトリ外**のフォルダに展開後、リポジトリルートで実行する。

```bash
python data-research/tools/inspect_osm_four_site_evidence.py \
  --evidence-dir /outside-repo/osm-4-ichikawa-UNREVIEWED \
  > /outside-repo/osm-4-audit-UNREVIEWED.json
```

失敗時は終了コード2でBLOCK。コードはネットワークアクセスも原本書き換えもせず、JSONレポートを標準出力する。出力も未審査で、GIS/公開API/ナビへ投入してはいけない。

## テスト

```bash
python -m unittest discover -s data-research/tests -p 'test_inspect_osm_four_site_evidence.py' -v
```

合成テストは9ケース。GSI原本SHA固定、OSM/query改ざん、独立Overpassクエリ範囲の改変、承認状態の偽装、HTTP出典の改変、重複OSM ID、0件を検査する。**実OSM取得、実アーティファクトに対する監査、人間によるC承認は未実施。**

### 次のゲート

[Issue #328](https://github.com/1kz-ma1/HINANEX/issues/328)で人間がOSM ODbLとGSIの注意事項を確認し、手動Actionsを起動した後、本監査で照合する。その後、D #317/#318とCの独立承認は別PRで行う。

**影響範囲**: `data-research/**`のみ。Contract、RegionExport、GIS、Renderの変更なし。#571 江戸川河川敷緑地の住所範囲・入口の問題は引き続きHOLD。
