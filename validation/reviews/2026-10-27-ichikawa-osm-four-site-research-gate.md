# C向け事例台帳: 市川市4地点の実OSM原本取得と未承認レビュー（2026-10-27）

**証拠種別: A研究原本 + 独立した技術整合監査の記録。C人間の施設同一性審査は未着手/未受領。** 人間の独立レビュー済み、正式な避難場所/入口/敷地、全国適用可能、と**読み替えない**。

運用ルールは [共通レビュー学習ループ仕様](../docs/REUSABLE_REVIEW_EVIDENCE_LEARNING_LOOP_20261027.md)。担当班員への作業依頼とレビュー結果の受入は [Issue #333](https://github.com/1kz-ma1/HINANEX/issues/333) に記録する。実原本取得・証拠は [Issue #328](https://github.com/1kz-ma1/HINANEX/issues/328)。

## 1. 実行済み / 失敗 / 未実施の分離

| 段階 | 実績・範囲 | 現時点の意味 |
| --- | --- | --- |
| GSI原本 | [Actions #40258746945](https://github.com/1kz-ma1/HINANEX/actions/runs/40258746945) の `skhb02/10/909/403.geojson`。800 features、原本SHA `cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84` | 1タイル分。市川市全件/市境界内全件の網羅性は未検証 |
| 初回OSM取得 | 2026-10-27 [Actions #40449512069](https://github.com/1kz-ma1/HINANEX/actions/runs/40449512069) **FAILED** `OSM_REQUEST_FAILED_NO_AUTOMATIC_RETRY` | 当時のコードは例外を統一していたため原因のHTTP/TLS/DNS区別は**不明**。原本0件・監査未実施。「OSMの施設0件」ではない |
| 診断改善 | A [PR #332](https://github.com/1kz-ma1/HINANEX/pull/332) をmain統合、取得エラーの分類のみ追加。CI成功 | 初回障害原因の遡及特定ではない。自動再試行・取得先変更なし |
| 2回目OSM取得 | 2026-10-27 [Actions #40450664081](https://github.com/1kz-ma1/HINANEX/actions/runs/40450664081) **SUCCESS**、main `594424495bb65628ac5092ba986cd2c707b6836b`。OSM/GSIの明示確認、既存GSI原本再利用、固定Overpass 4×300mクエリ、原本SHA/監査・アップロード成功 | **取得の成功**。対象施設への所属・入口・指定区域・安全性の証明ではない |
| 元OSM原本 | `OSM-Ichikawa-4-sites-UNREVIEWED` artifact **12709684758**。JSON 74,406 bytes、SHA `8ee92b8532ed761b59a59a0a240c4498548424438a122e8dda0af8b49336ce57` | 37 OSM地物 = **way 35, relation 2, node 0**。元の要素はGSIに**未割当** |
| 固定クエリ | SHA `c48a14e29a8aca377a785ddabb4dd2f70ff0f4feba0e48a0c97296d780ab800c` | Overpass API `https://overpass-api.de/api/interpreter`、HTTP 200。ソースが主張するsnapshot `2026-10-27T04:35:36Z` は独立の公開時点認証ではない |
| 独立A技術監査 | `OSM-Ichikawa-4-sites-UNREVIEWED-AUDIT` artifact **12710028211**、SHA/固定元GSI/クエリ/全未承認フラグの検証 **PASS** | 技術的バイト整合。Cの一次資料照合・施設事実確認・人間の採否とは別 |
| C人的判断 | [Issue #333](https://github.com/1kz-ma1/HINANEX/issues/333) **OPEN / レビューを班員に依頼済み、成果未受領** | 施設同一性・敷地・入口・災害時の運用・ナビゲーションは**HOLD** |

元の研究成果物はGitで公開しない。上記GitHub Actionsのアーティファクト保持期限は、OSM原本が **2026-10-30 13:37:16 JST**、監査レポートが **13:37:17 JST**（記録時の期限）。期限切れは実原本が存在しなかった根拠ではない。追跡に必要な保管済み原本とSHAの照合を別管理し、利用条件を守る。

## 2. 4地点別の調査キュー（C判断ではない）

| GSI source feature index / 原文名 | OSM観測点近傍の候補 | 将来の失敗モードとして調べること |
| --- | ---: | --- |
| `571` 江戸川河川敷緑地 | 2 | 別名のOSM地物「柴又公園」が近傍に入る。公園・河川敷の広い区域と自治体の指定区域の違い、参考点と入口を誤結合しないこと |
| `639` 須和田公園 | 6 | 公園と近隣学校を名称・近さだけで結ばないこと |
| `682` 大洲防災公園 | 5 | 無名wayと公園境界を同じものと推定しないこと |
| `707` 筑波大学附属聴覚特別支援学校（グラウンド等） | 24 | 校地、校舎、グラウンド、周辺施設を区別し、指定対象が全敷地か一部かを確認すること |

**注意**：2/6/5/24は原本OSM要素の非排他的な**観測点から半径300m以内のレビューキュー**。37という総数とたまたま同じ和でも、37箇所の独立避難先や網羅率を意味しない。ノード0は検索条件に一致する入口nodeが0だった事実にすぎず、入口の不存在ではない。OSMタグ・近接値は原本に記録された観測で、施設一致を証明しない。原本に登録された観測点数 **962** は測地/敷地境界の検査点数ではない。

現状の許可状態：`associated_gsi_feature_index=null`、`facility_geometry_verified=null`、`navigation_endpoint=null`、`candidate_to_official_facility_identity_verified=false`、`human_c_approved=false`、`navigation_allowed=false`、`may_publish_or_route=false`。外部の正式審査なしに変更しない。

## 3. これまでの事例を共通の失敗モードへ接続する

| 既存の検証材料 | 確認できた/提案された現象 | 今後の回帰テストに変えるときの区別 |
| --- | --- | --- |
| [市川C draft #316](https://github.com/1kz-ma1/HINANEX/pull/316) | GSI市川住所接頭辞の29原本レコードと自治体資料の**AI転記文字列**で28件完全一致、#571だけ住所表記の範囲差。**元自治体PDF版の独立バイト証跡・人間承認は未完了** | `NAME_MATCH_ADDRESS_DIFF` と `SOURCE_VERSION_NOT_ATTESTED`。文字列一致だけでGSI↔市の施設同一性を許可しない |
| [江戸川区C事前レビュー](2026-10-19-edogawa-ai-cross-source-prereview.md) と [委任手順](../docs/EDOGAWA_DELEGATED_REVIEW_HANDOFF_20261019.md) | 旧校舎と新校舎、同じURLを使用しているが異なる物理敷地等の例を整理。既存レビューは事前案/正式承認とは別 | `RELOCATED_SITE_TIME_CONFLICT`、`SHARED_URL_DIFFERENT_PHYSICAL_SITE`。名前・URL一致の反例テストに使う |
| [名古屋位置パイロットIssue #286](https://github.com/1kz-ma1/HINANEX/issues/286) | 住所からの推定位置候補と自治体原本の照合、誤一致・座標衝突・未解決の人間審査が課題 | `GEOCODE_REFERENCE_NOT_OFFICIAL_POINT`。ジオコーダ出力を許可済み入口や正式地点に昇格させない |
| 今回の実OSM 4地点 | `NO_ENTRANCE_NODE_IN_BOUNDED_QUERY`、`LARGE_CAMPUS_PARTIAL_DESIGNATION`、`NEARBY_DIFFERENT_NAME` の調査仮説 | 反例/条件付きテストに利用するが、個別要素の事実が人間によって確定したわけではない |

これらの分類タグは**設計上の候補名**であり、実際に全国の他地域で誤判定が再現したという統計的な主張ではない。未知・不一致は解消したふりをせずレビュー待ちとする。

## 4. 返却されたAIデスクレビューの扱い（2026-10-27追記）

班員が返却した **Markdown＋JSONはAIによる独立デスクレビュー補足**であり、資料の本文が**人間のC独立確認は未実施**と明示している。別途このセッションで原本SHA・37件内訳・指定4 wayの `covers(point)` と最寄り頂点距離を再計算しPASS。4つとも頂点まで23.3～66.5m離れていてもOSMポリゴン内であり、頂点距離だけで「敷地外」とする誤推論を防ぐ**回帰テスト候補**になった。

- [再計算・一次資料表示照合・更新日矛盾・未承認境界の記録](2026-10-27-ichikawa-ai-desk-review-independent-replay.md)
- 更新日について、提出側 `2026-09-08` と市公式ページ表示 `2026-07-28` が不一致。**SOURCE_UPDATE_DATE_CONFLICT / UNRESOLVED** を維持。
- **現状：AI机上検算受領、実際の人間Cによる資料確認・施設同一性・指定敷地・入口・災害時安全・公開承認は未受領 / HOLD。** 原本ZIPや返却JSONはGit管理外。

## 5. 班員の人間C確認が返ってきたら追加するもの（まだ未実施）

班員から提出されたものをそのまま「C承認済み」としない。次の順でオーナーがレビュー記録を受領する。

1. **ケースごと**に検証命題、GSI feature key + OSM type/ID、元のSHA、資料URLとページ/行、取得/適用/確認の日時を照合する。
2. 判断は `CONFIRMED`、`UNRESOLVED`、`REJECTED_CANDIDATE`、`NOT_REVIEWED` のいずれかを**対象の命題だけ**に付与。根拠がなければ未解決。公式ソース間の矛盾は勝手に丸めない。
3. AIの提案と**実際に人が開いた資料**を区別し、誰がどう確認したかを記録。実名などは非公開に保管し、Gitに載せる場合は役割/監査参照IDのみ。
4. 人間による一次資料検証 → オーナーの対象限定採否（認証可能な方法）→ 改善可能な決定論的なチェックを抽出。**C受領と本番運用承認を分離**する。
5. 各再利用ルールについて、明確な正例・誤結合する反例・欠損・改版事例を作り、**別地域**の留保データで再現性を検証。結果が出るまでは将来設計のまま。
6. 追加の人間レビュー結果が返ってきた時点で、**新しい記録/PR**として追記し、ここに今は存在しない `CONFIRMED`・署名・実測省力化率を捏造しない。

**人間レビューの結果を扱う際の保留原則**：対象施設が公式資料に載っていることと、災害時にその敷地の任意の点へ入れることは別命題。利用者への経路・開設・安全性の主張は、明示的な別の安全ゲートを経るまで不可。
