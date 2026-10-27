# C evidence supplement — 市川4地点の班員から返却されたAIデスクレビューの検算（2026-10-27）

**判定：AIデスクレビュー資料として受領／原本のバイト照合・指定4 way幾何包含の再計算PASS／自治体掲載区分のウェブ表示を別途照合／人間C承認はNOT REVIEWED。**

[初回の研究・原本台帳](2026-10-27-ichikawa-osm-four-site-research-gate.md) と [共通レビュー学習ループ](../docs/REUSABLE_REVIEW_EVIDENCE_LEARNING_LOOP_20261027.md) に対する**追記**であり、元原本・従前のC状態・公開APIは変更しない。2026-10-27に班員から届いた成果物はMarkdown報告書とJSON補足の2ファイル。**報告書本文が「AIによるデスクレビュー補足、C担当人間による独立確認・承認は未実施」と明記**している。班員が提出した事実は人間の施設確認や本人署名を意味しない。

## 1. 提出資料と原本の来歴

- 返却ZIP SHA-256: `c0f2da958535c34d77cb6352278e8a51ae47e20abd4f2ee7b4fe20dcc22b592f`。内訳は `HINANEX_市川4施設_OSM原本_独立再計算と公的一次資料照合_20261027.md`（SHA `2ca395d6298dd5720f38cede29e60b76f2cbcede3c1cb284938b0b6cf1ec75e3`）と `HINANEX_市川4施設_デスクレビュー補足_UNAPPROVED_20261027.json`（SHA `4fce96052759f72af832e8b572d01597b21cf67bbbf00ab97a3cfecc963466b4`）。
- 原本の照合対象: [手動取得 run #40450664081](https://github.com/1kz-ma1/HINANEX/actions/runs/40450664081)、原本ZIP（artifact `12709684758`）、独立監査（artifact `12710028211`）。報告書内 `source_artifact_sha256=2e3ac8456ce97a8b0d7eccf36ded14fe9e4bde8c61aeb21dfe3ac0115d8d46a1` は手元の先行レビューZIPと一致。
- 元GSI SHA `cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84`、OSM JSON SHA `8ee92b8532ed761b59a59a0a240c4498548424438a122e8dda0af8b49336ce57`、OverpassQL SHA `c48a14e29a8aca377a785ddabb4dd2f70ff0f4feba0e48a0c97296d780ab800c` は**独立に再読した原本バイトと一致**。
- 実原本: OSM37要素（35 way, 2 relation, 0 node）、観測座標延べ962。OSM由来の snapshot `2026-10-27T04:35:36Z` はソースの申告時刻であり公式指定の有効時点ではない。
- 元ZIP/返却JSON/個別地物全文はGit管理外で保管し、必要ならアクセス制限付きで原本と照合する。Gitにはケースの検証要約とSHAだけを残す。

## 2. 今回独立に再計算できた技術的な命題

手元の**元のOSM JSON・GSI GeoJSON**を直接読み、元の報告書の計算式/距離値を信頼するだけでなく、別に検算した。

- ハーバサイン球面距離（R=6,371,000m）でGSI参考点から対応OSM wayの最も近い**記録頂点**までの距離を検算。
- Shapelyで対応4 wayの閉じた座標列からPolygonを構成し、pyproj `EPSG:4326 → EPSG:32654` でpoint/polygonを同じ投影に変換し `covers(point)` を評価。
- 下記4 wayの**各構成ポリゴンは有効かつ参考点を内包**。元原本の35 wayは全て閉じた形状として構造を確認（Shapely上のPolygon妥当性も35件PASS）。**relation 2件の完全な面構築/意味づけを同じ手順で再検証したわけではない**。提出書の「37ポリゴン全て妥当」は別途定義・検査方法が必要で、C全地物の正式承認とは扱わない。

| GSI index | 対応名を持つOSM要素（IDは原本照合） | 最短記録頂点までの距離 | 対応Wayポリゴン内 |
| --- | --- | ---: | --- |
| 571 江戸川河川敷緑地 | `way/1150931070` | 66.5m | 真 |
| 639 須和田公園 | `way/279274669` | 23.3m | 真 |
| 682 大洲防災公園 | `way/140474713` | 56.2m | 真 |
| 707 筑波大学附属聴覚特別支援学校（グラウンド等） | `way/1255472594`（OSM名称: 運動場） | 45.2m | 真 |

**意味の境界：** `covers=true` は**GSI参考点の座標がOSMに描かれた図形の内部/境界にあるという幾何的関係**。OSM wayの運営・敷地・行政上の指定緊急避難場所の正式な区域、災害時の立入や安全経路まで確認できたわけではない。参考点をOSM wayに自動割当したり、`entrance`や`facility_geometry`へ昇格させない。

## 3. 市川市・学校のウェブ一次資料表示と修正が必要なメタデータ

- [市川市危機管理課「避難場所・避難所一覧」](https://www.city.ichikawa.lg.jp/page/40332.html)の公開表示を別途確認した。市川・八幡・国分地区の一覧に次の名称/所在地/分類を確認：#571 江戸川河川敷緑地「市川南3・4丁目地先」（避難場所○/避難所欄空白）、#639 須和田公園「須和田2-34」（○/空白）、#682 大洲防災公園「大洲1-18」（○/空白）、#707 筑波大学附属聴覚特別支援学校（グラウンド等）「国府台2-5」（○/○）。**避難所欄空白を「指定されない」と断定するのではなく、閲覧した表の掲載状態として記録**する。これは災害種別・開設状態の検査ではない。
- **不整合：提出JSONは市公式ページの更新日を `2026-09-08` と記載。しかし今回アクセスした当該公式ページは `更新日: 2026年7月28日` と表示**。一次資料の版・改版履歴や提出側の閲覧証拠が揃うまで `SOURCE_UPDATE_DATE_CONFLICT / UNRESOLVED`。提出値を一律に正しいものとしてコピーしない。
- [学校公式交通案内](https://www.deaf-s.tsukuba.ac.jp/アクセス/交通案内/)は学校一般所在地 `千葉県市川市国府台2-2-1` と記載。市の指定グラウンド等 `国府台2-5` と表記が異なる。直ちに同じ公式指定ポリゴンや災害時の入口と解釈しない。交通案内に門が記載されていても**災害時グラウンドへ入れる入口の承認ではない**。

## 4. 未来に再利用する回帰テスト候補（新機能は未実装）

| 提案ID | 今回の反例/未確認 | 再利用する時の安全な期待値 |
| --- | --- | --- |
| `VERTEX_DISTANCE_NONZERO_BUT_CONTAINED` | GSI点はWayに内包されるが、最寄り頂点距離が23.3〜66.5m | 頂点距離だけで `OUTSIDE`/別施設にしない。OSM形状が成立する場合のみ幾何包含を**調査ヒント**に追加 |
| `MULTIPLE_NESTED_OSM_GEOMETRIES` | 公園・運動場の無名`pitch`も参考点を含むという提出報告（個別の無名要素は本メモでは未再照合） | 複数図形包含を単一の公式指定敷地に自動結合しない |
| `NEIGHBORING_DISTINCT_SCHOOL_OR_PARK` | #571柴又公園、#639第二中学校、#707学校敷地/運動場 | 近傍・名称類似だけで対応地物を決定しない |
| `OFFICIAL_POINT_VS_DESIGNATED_SUBAREA` | #707市の「グラウンド等」と学校一般所在地の違い | 校地と災害指定区域を別の命題・時点で照合 |
| `SOURCE_UPDATE_DATE_CONFLICT` | 提出 `2026-09-08` と今回公式ページ表示 `2026-07-28` の不一致 | 公式ページ表示/保全原本/確認日時を別フィールドとして残し、競合を `UNRESOLVED` にする |

これらは**決定論的なテスト案と人間レビューの論点**であり、新規自治体における自動承認規則、実測された自動化率、安全な地理判定、Cの意味承認ではない。別PRで合成の正例/反例/欠損/改版例を作り、他地域でも保留検証してから採用する。

## 5. 次のC人間レビューゲート

班員が提出したAIデスクレビューだけでは`review_disposition=CONFIRMED`を正式に発行しない。 [Issue #333](https://github.com/1kz-ma1/HINANEX/issues/333)で、各個別命題について**人が実際に見た公式資料、ページ/行、原本版、確認時点、矛盾と限界、本人による確認記録**を追加してからCの限定範囲の判断を検討する。

**現状**：`candidate_to_official_facility_identity_verified=false`, `facility_geometry_verified=null`, `entrance_position_verified=false`, `human_c_approved=false`, `navigation_endpoint=null`, `navigation_allowed=false`, `may_publish_or_route=false`。**USER-FACING/GIS/REGIONEXPORT/ROUTINGへの自動反映なし**。

**作業状態**：AI報告書受領=YES、独立ローカル技術再計算=PASS、ウェブ表掲載の個別表示照合=PASS、公式ページ更新日整合=UNRESOLVED、実際の人間C照合=NOT RECEIVED、公式敷地/入口/運用の正式承認=HOLD。
