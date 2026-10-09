# 中間発表 / 位置指定 × 洪水：公式Source調査（2026-10-09）

**担当** A / Evidence。Dの候補判定・Eの地図UI・Cの独立受入をこの文書で代替しない。

## 目的と厳格な区別

従来の`shelter_location`（施設の位置）と`flood_shelter_selection`（災害別の公式raw適合性は原則UNKNOWN）を勝手に読み替えず、**洪水の指定緊急避難場所（行政の指定）**を別Sourceとして取得・検証する候補を調べる。

- 指定緊急避難場所：災害の危険から命を守るため、**災害種別ごと**に指定された場所。一般的な指定避難所（一定期間の滞在先）とは異なる。
- 公式指定が確認できること ≠ 当日の開設 ≠ 経路の安全 ≠ 建物の全条件に対する安全性。
- 災害種別が不明、座標なし、出典不明、または未照合の施設は近距離であっても「確認済み洪水対応候補」へ格上げしない。
- 現在地からの直線距離は探索の目安のみ。移動経路、浸水、広域避難の方針の代替ではない。

## A-1 国土地理院：災害種別「洪水」に限定された指定緊急避難場所

| 属性 | Evidence |
|---|---|
| Source | 国土地理院「指定緊急避難場所・指定避難所データ」 |
| Publisher | 国土地理院 / 市区町村から登録された情報 |
| Official overview | https://www.gsi.go.jp/bousaichiri/hinanbasho.html |
| Terms / caveats | https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html |
| Data format | CSV と GeoJSON で公開。地理院タイルはGeoJSON形式 |
| Flood GeoJSON tile template | `https://cyberjapandata.gsi.go.jp/xyz/skhb01/{z}/{x}/{y}.geojson` |
| Tile specification | https://maps.gsi.go.jp/help/use.html |
| Verified source catalog date | 2026-10-09（ページ内容の確認日、個別施設データの更新日ではない） |
| `published_at` / last municipality update | `null` / `null`（本レビューでは確定不可） |
| Dataset licence / download terms | 個別利用注意と国土地理院コンテンツ利用規約を要確認。ライセンス名称を推定で設定しない |
| Retrieval status | **SOURCE_DOCUMENTATION_CONFIRMED; PER-FACILITY_RAW_NOT_FETCHED** |
| Intended use | GSI洪水タイル等から施設単位の公式指定・位置・出典を**同一raw feature**で保持し、Cの独立照合で受入したものだけをD/Eへ渡す |

**限界:** 国土地理院の公開対象は市区町村が登録し公開に同意したものに限られ、未掲載＝指定なしではない。情報が最新でない可能性があり、最新状況は自治体確認が必要。地図表示だけで候補の実際の安全性を断定できない。

**2026-10-09追認（公式GSI仕様ページ）:** 国土地理院タイル詳細 https://cyberjapandata.gsi.go.jp/development/ には、GeoJSON施設の公式属性として `properties.name`（施設・場所名）、`address`（住所）、`remarks`（備考）、`disaster1`〜`disaster8`（災害種別）を列挙している。**`disaster1=1`は洪水対応指定**である（タイル`skhb01`は洪水専用）。ただし公式ページの説明は配布フォーマットの仕様であり、**江戸川区の実タイルの全行について値を確認したものではない**。feature固有ID・自治体コードのschemaはその仕様では確認できないため、Cは元データ行への位置・属性traceを別途検証する。

**未確認:** 実配布GeoJSONの現在のfeature内容/固有ID表記、タイル単位の重複・地域境界、収録範囲、正確なraw件数、江戸川区の洪水指定地点が現在どれだけあるか。本レビューではraw GeoJSONを取得していない。Dはフィールド名・自治体帰属・座標・災害別指定の意味を推測してAdapter化してはならない。

## A-2 江戸川区：水害時の避難方針と矛盾させない

| 属性 | Evidence |
|---|---|
| Source | 江戸川区「江戸川区水害ハザードマップ概要版」 |
| Publisher | 江戸川区 |
| Official URL | https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/5-1gaiyouban/index.html |
| Verified date | 2026-10-09 |
| Date of page publication/update | 本確認で正確な更新日未確定（`null`） |
| Format | HTML |
| License | 未確認（`null`） |

水害規模や居住場所によって、区外への**広域避難**や親族・知人宅等の避難先確保が案内されている。区内の待避施設（小中学校等）はやむをえない場合の避難手段であり、多くが浸水・孤立の可能性をもつ旨が公式に説明されている。

**UI必須警告:** 江戸川区で洪水指定緊急避難場所を表示できるようになっても「距離が最短だからそこへ向かうべき」「区内施設が区外避難より常に望ましい」「開設中」とは表示しない。発表デモでは **公式の広域避難方針を優先** する案内を併記する。

## A-3 D/C/E handoff gate

1. **A追加調査:** 実配布GeoJSON・CSVから実際のフィールド名・自治体コード・識別子・重複条件・洪水指定の原値・現在の更新情報を、出典とともに確定する。
2. **D:** 元Source featureの固有識別子・座標・正確な災害区分・Source URL・traceを保持し、独立した`flood_designated_site_discovery`系の参照モデルへ。既存`shelter_location` 152件へ名称だけでjoinしない。Scope未認定で推薦判定しない。
3. **C:** 元公式raw → 正規化施設ID → 災害別指定 → 座標の一対一追跡、地理的欠損と未確認分類、地図UIの誤表示を独立監査。2026-10-08の既存A/D/C raw監査がPASSでもこの新しいSourceの受入には使えない。
4. **E/B:** 現在地はブラウザ位置情報の許可または**手動地図選択**のみ。HTTPS環境と権限拒否を考慮し、ユーザーの位置はサーバー送信せずクライアント内の距離計算を原則とする。見つかった施設は**「指定情報の参考表示」**であり「今すぐ行くべき順」ではない。

## Release state

- [x] 公式Sourceと江戸川区の重要な避難方針を確認・記録
- [ ] 配布raw資料の実取得、施設ID・座標・災害フィールドの確認
- [ ] 指定施設のC独立受入
- [ ] D/Eによる安全なUI接続と端末での実データテスト
- [ ] Merge Captainの`main`反映判断

**中間発表用のテストfixtureは実際の避難判断で使わない。未確認データのまま実際の「行くべき施設」一覧を作らない。**
