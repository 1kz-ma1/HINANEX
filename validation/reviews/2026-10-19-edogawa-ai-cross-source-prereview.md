# C — 江戸川区施設同一性・災害区分のAI独立レビュー案（2026-10-19）

**AI PRE-REVIEW / 未承認 / human reviewer欄・D昇格は変更せず。** C #265/PR #270に対する追加調査メモで、A原本7件からの読み取りと独立したソース照合の未承認提案に限定する。正式C比較のSHAs/時点は [正式比較引継ぎ](../docs/EDOGAWA_REAL_C_COMPARATOR_HANDOFF_20261019.md) を参照。

## 独立した具体的なソース事実

| 提案した確認対象 | 水害一覧原本 | 位置CSV原本 | 別の公式記述 | 判定できる範囲 |
|---|---|---|---|---|
| 現下小岩小学校 | 番号60 / 南小岩5丁目5番1号 / `2階以上` | 23行 / 35.7254506,139.8784285 / icon空欄 | 小学校一覧：現所在地。2025-04-30発表：2025年4月から学校供用 | **2資料の現校舎という表記が一致**。座標と水害敷地の行政的対応までは未承認 |
| 旧下小岩小学校 | 番号「-」 / 南小岩7丁目8番1号 / `大規模水害では使用不可` | 114行 / `旧下小岩小学校（体育館のみ使用）` / 35.7276762,139.8831013 / `fire.png` | 小学校一覧：2023年3月末閉校 | **旧敷地と現校舎の住所は別**。`体育館のみ使用` と `大規模水害では使用不可` は異なる出典の異なる用途で矛盾を勝手に解消しない |
| 都立葛西工科高校（文字列表記揺れ） | 番号108 / 都立 葛西工高等学校 / 一之江7丁目68番1号 / 03-3653-4111 / `2階以上` | 19行 / 都立葛西工科高校 / 35.683604,139.8788767 / fire.png | 江戸川区都立・私立学校表＋東京都立学校アクセスで所在地・電話一致 | **学校名・住所・電話の一致候補**。CSV座標の地理的実体と災害時の利用可否は未承認 |
| 関東第一高校（文字列表記揺れ） | 番号109 / 私立 関東一高等学校 / 松島2丁目10番11号 / 03-3653-1541 / `3階以上` | 8行 / 関東第一高校 / 35.708171,139.8602629 / fire.png | 江戸川区都立・私立学校表＋学校法人公式概要で所在地・電話一致 | **学校名・住所・電話の一致候補**。用途・現開設・洪水指定は未承認 |

**重要な逆例**：現・旧下小岩小学校の位置CSV行は学校リンクURLがまったく同じ一方、緯度経度は異なる。名称・URL・近さだけでjoinすると誤識別の危険がある。

## 3レビューIDへのAI提案

| CレビューID | AIで確認した事実 | 残る人間の判断／現状 |
|---|---|---|
| `C-SITE-OLD-NEW` | 異なる住所、閉校時点、旧第二小学校の敷地に新校舎、現在/旧の別座標 | **要個別承認**：旧体育館と校舎の運用範囲、行政上の指定時点、具体的な物理施設ID |
| `C-MUNICIPAL-CROSSSOURCE` | 4候補の表記・住所・電話・一部CSVの値の照合、CSVに住所列なし、現旧URLは同一 | **要個別承認**：CSV行を特定の水害一覧行と結ぶ「実物理施設」の同一性・期間。現状承認0件 |
| `C-GSI-FLOOD-SEPARATION` | GSIは災害種別別の指定緊急避難場所を提供し、自治体の「水害時待避施設」ページは緊急時のやむを得ない施設を説明 | **未取得**：今回の7原本に江戸川区の個別GSI洪水featureはない。`skhb01`指定、開設、安全・経路の結論はUNKNOWN |

## 人間に残す最小レビュー操作（C自体の受入仕様は勝手に変えない）

1. **施設を実際に結合する場合だけ**、対象施設・元原本行・時点・物理住所/配置をC担当が確認し、承認する組だけを列挙（承認できない組はUNKNOWN）。
2. **災害別の判定をDへ追加する場合だけ**、自治体の指定やGSI元feature・適用条件を独立に確認。`fire.png`を洪水情報として解釈しない。
3. **本人確認を伴う承認**をGitHubの正式PR Review等で別途残す。AI作成のこのメモおよび構造検査のPASSは承認行為ではない。

## 現時点の安全な出力

`approved_cross_source_pairs=0` / `flood_scenario_classifications_added=0` / `D source acceptance=HOLD`。本メモは原本の再配布、施設join、D/E/GIS/Renderへのデータ移行を行わない。

## 公開参照元（各取得日時は保存原本マニフェストに固定）

- 江戸川区 [水害時待避施設](https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html)／[施設位置CSV](https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv)／[区立小学校一覧](https://www.city.edogawa.tokyo.jp/e068/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/shogakko.html)。
- [区立学校新校舎発表 2025-04-21](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/kohokocho/press/2025/04/0421.html) と[2025-04-30事後発表](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/kohokocho/press/2025/04/0430.html)。
- [都立・私立学校](https://www.city.edogawa.tokyo.jp/e004/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/toritsushiritsu.html)、[都立葛西工科高校](https://www.metro.ed.jp/kasaikoka-h/access/access.html)、[関東第一高校](https://www.kanto-ichiko.ac.jp/about/outline/)。
- [国土地理院：指定緊急避難場所・指定避難所](https://www.gsi.go.jp/bousaichiri/hinanbasho.html) と [免責事項](https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html)。