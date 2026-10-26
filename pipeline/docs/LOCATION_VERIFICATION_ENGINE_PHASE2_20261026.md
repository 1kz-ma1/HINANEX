# Location Verification Engine — Phase 2：敷地・入口候補の証拠照合（2026-10-26）

**D内部・合成データだけの判定器。新規の実公式/OSM敷地データは取得していない。正式な位置の精度・避難先/入口・実際の安全性を承認しない。**

## 第1段階からの安全な拡張

[D Phase 1 PR #317](https://github.com/1kz-ma1/HINANEX/pull/317) で実装した `LOCATION_TRIAGE_INTERNAL_ONLY_UNAPPROVED` 結果を受け取り、別途得られた敷地や入口の**候補証拠**を見比べて、さらに絞った人間の検証キューを作る。

- GSIの `reference_point` は既存の原文から変更しない。敷地や入口に「吸着」させない。
- `candidate_geometry` は外部の未検証 Polygon。座標の内外・境界にあるという**計算上の関係**は記録できるが、公式施設との同一性も、災害危険区域・高低差も、安全に入れることも証明しない。
- `entrance_hints` は入口タグと位置の**候補**。OSM `entrance=main` や `access=yes` でも入口の現状・災害時の通行許可を証明しない。
- `common_id_raw` は本PRでは GSI CSV 出所を申告された未照合原文のみ（他のソースに混ぜない）。CSV/GSI GeoJSON、市の一覧を自動的に同一施設と判定せず、正式な取得・ハッシュ・ID結合はA/Cの別PRで行う。
- すべての `facility_geometry_verified=null`、`navigation_endpoint=null`、`navigation_allowed=false`、`human_c_approved=false` を維持する。
- 候補の件数が0でも**施設が存在しない証拠ではない**。逆に複数の敷地候補があっても勝手に1件に収束させない。

## 受入入力の境界

`triage_candidate_spatial_evidence(phase1, candidates)` は次を要求する。

- Phase 1のUNREVIEWED状態、未承認 `source_feature_key` とGSI原文 `reference_point`。
- 候補行ごとに `source_feature_key`, `provider`（OSM/MUNICIPAL_GEOJSON/GSI_CSV）, 出典URL、原本ハッシュの主張、候補geometry/entrance点とタグ。これは**入力元を独立に認証する機能ではない**。
- 多重Polygon、穴ありPolygon、複雑な線形など本実証で誤判定しうる幾何は拒否。現時点は単一外周の単純なPolygonのみ。自己交差、不閉合を拒否し、内外/境界を分ける。
- OSMのURL形式は厳密に検査するが、実際のOSM API照会やライセンス/取得日時/状態の確認はここでは行わない。

## 正式データを扱う前の必須ゲート

1. Aが実際の **GSI CSV共通ID** を正式取得・版/ライセンス/ハッシュ固定し、CがIDとGeoJSON間の対応を独立検証。
2. A/Eが敷地・入口候補の原本をライセンス・更新日・OSM等の出典付きで取得。市町村・区域・距離だけで同一施設と推定しない。
3. Cが候補の施設同一性・実際の敷地と入口・災害種別・通行規制・開設状況・公式資料の版を審査。
4. その後初めて、別PRでGIS参考表示・経路判定用の契約を検討。今回の出力は直接GISに渡さない。

公式参照： https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html （GSI CSV列順、共通ID）、 https://wiki.openstreetmap.org/wiki/Key:entrance （OSM entranceタグは入口の種類、通行権限ではない）。

## テスト
`cd pipeline && python -m unittest discover -s tests -p "test_location_evidence_overlay.py" -v`。
通常DテストはGitHub required testで実行。 `verify_d_mvp.py` は生成済みの既存評価出力が必要なため別ゲート。

**スコープ:** pipeline/**のみ。C #316の未承認台帳、D #317の基本評価、RegionExport、GIS UI、main、Renderに変更なし。Phase2をPhase1のbranch上に積んだDraft PRとして提出する。