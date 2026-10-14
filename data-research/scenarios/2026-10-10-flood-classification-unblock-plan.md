# 洪水対応施設を「判定可能」にするための公式根拠・施設照合ゲート（2026-10-10）

- 担当：**A / Data Research**。Dの評価値、Cの独立受入、Eの地図表示はこの文書で変更しない。
- 対象：東京都江戸川区 13123、新潟県新潟市 15100
- ステータス：**公式ページ/コードの照合調査まで完了。施設ID単位の同一性確定と新潟ODS記号の自治体承認は未完了。CANDIDATE/EXCLUDEDは増やしていない。**
- 既存資料：[A 2026-10-08再検証](2026-10-08-flood-source-reverification.md)、[Scenario仕様](flood-shelter-selection.md)、D `pipeline/docs/FLOOD_SCENARIO_CONTRACT.md`、[Issue #48](https://github.com/1kz-ma1/HINANEX/issues/48)、[Issue #89](https://github.com/1kz-ma1/HINANEX/issues/89)
- 調査日：**2026-10-10**（日本時間）。HTTPレスポンス原本のA独立アーカイブ/SHA256はこの調査では作成していない。既存2026-10-08 Cのraw照合結果を本調査で再実行したとはみなさない。

## 1. 結論：何が実際に解消したか

| 地域 | 現存の公式Source | 位置データとの結合 | 原文の意味 | Dの施設別Scenarioを今すぐ変更できるか |
| --- | --- | --- | --- | --- |
| 江戸川区 | 区の水害時「待避施設」HTML。各行に番号・施設名・住所・電話番号・使用可能階数 | **未確定**。公式待避施設HTMLと位置CSVは別Source。検証済み共通IDなし | 水害時の緊急待避施設／利用可能階数。**洪水単独の指定緊急避難場所とは限らない** | **不可**。元行・住所・施設IDの対応をCが検証し、D/CがScenarioの意味を別途承認するまでUNKNOWN |
| 新潟市 | 市の自治体標準ODS「指定緊急避難場所一覧」CSV | **同一行の直接照合済み**（前回Cのraw-row監査） | `災害種別_洪水` 列があるが**各raw記号の列固有の公式定義は未承認** | **不可**。市の防災課または正式の当該CSV項目定義で記号意味・階条件を明示確認するまでUNKNOWN |

**この文書は「判定を減らさず増やせる経路」を示すが、現時点で青/灰マーカーを根拠なく生成しない。**

## 2. 江戸川：公式資料で新たに確認した具体的な照合キー

### 2.1 Source A-EDO-WATER（別Source）

- 出典：江戸川区「地域防災拠点に避難、待避施設（小中学校等）・自主避難施設へ避難（19ページ～20ページ）」
- URL：<https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html>
- Publisher：江戸川区
- Page updated：**2025-12-19**（ページ明記）。初回公開日：未確認
- Source format：HTML table
- 公式欄：`番号 / 名称 / 住所 / 電話番号 / 使用可能階数`。掲載対象は小中学校のほか高等学校等にも及ぶ。
- 施設の例（あくまで**公式HTML側の行**。HINANEXの位置レコードと突合済みという意味ではない）：
  - No.1 `小松川小学校(注)`・`平井4丁目1番23号`・`3階以上`
  - No.4 `旧平井二小学校`・`平井6丁目1番17号`・`2階以上`
  - No.107 `都立 紅葉川高等学校`・`臨海町2丁目1番1号`・`すべての階`
  - 番号なし `旧下小岩小学校`・`南小岩7丁目8番1号`・`大規模水害では使用不可`
- 自治体は待避施設を「避難時間がない・困難等でやむを得ない場合に緊急避難する施設」と説明し、自主避難施設は別扱い。施設ごとの**利用階条件**や利用不可の注記を削除してはならない。
- 利用条件/個別ライセンス：未確認。Source本文の公開を根拠に原文大量転載・再配布の可否を確定したことにはしない。

### 2.2 Source A-EDO-LOCATION（既存D CSV）

- 現行D Adapter：`pipeline/src/hinanex/adapters/edogawa_shelter.py`
- 正規化元（コード指定）：`https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv`
- 公開元ページ：`https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html`
- Adapterが現在必須として要求：`名称 / URL / 災害種別記号 / コメント / 緯度 / 経度`
- 出力施設ID：`13123|名称|緯度(小数7桁)|経度(小数7桁)` のSHA256由来、**自治体公式の共通施設IDではない**。
- `ShelterRecord`生成処理では現在**住所を保持しない**。名称・座標のみを公式水害HTMLの施設名・住所へ結び付けることは同一施設の確証ではない。
- `災害種別記号` は位置CSV上でアイコンURLであるためDは適合性へ読み替えていない。現方針を維持する。

### 2.3 A→D照合準備仕様（提案であり、確定joinではない）

1. D/Cが位置CSVに住所の実列があるか原本から確認する。**存在しない場合はNULLを保持**し、無関係な住所を捏造しない。公式HTMLの住所を位置レコードの住所として転写することも、施設同一性が確認されるまでは禁止。
2. 施設名完全一致だけで `DIRECT_SAME_SOURCE` へ昇格させない。正式共通IDがあれば最優先。なければ**別々の公式Sourceの施設名・住所・旧称・施設区分・行位置**をAが証跡化し、Cが独立して1対1の同一施設確認を行う。
3. 必要な照合台帳（将来のA-owned証跡）の列：`location_record_id`, `location_source_url`, `location_source_record_trace`, `water_facility_number_raw`, `water_name_raw`, `water_address_raw`, `water_floor_raw`, `water_source_url`, `review_status`, `reviewer`, `evidence_timestamp`, `raw_sha256`, `notes`。
4. `review_status` は `UNREVIEWED | CONFLICT | VERIFIED_PAIR` に限定。**名称等から自動で VERIFIED_PAIR にしない**。重複施設、旧校名、複合校、住所の丁目・番地表記揺れ、福祉避難施設等はCONFLICT/UNREVIEWEDに留める。
5. `VERIFIED_PAIR` にするにも、A証跡・C独立再検証・Dの用途別規則審査を必須とする。**VERIFY_PAIR ≠ 洪水適合性の肯定**。 `水害待避` と `洪水単独指定` の意味が異なることをUIで明示する必要がある。
6. 照合できない位置レコードはUNKNOWNのまま。公式HTML行に対応しないというだけで `EXCLUDED` にしない。

## 3. 新潟：同一行は追跡できる。問題は「災害種別_洪水」値の意味

### 3.1 Source A-NII-ODS

- 出典：新潟市公式 <https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/>
- 公式カタログ：`指定緊急避難場所一覧(CSV:171KB)`、担当課：**防災課**、更新日：**2026-09-25**、形式：CSV
- 公式CSVリンク：<https://www.city.niigata.lg.jp/shisei/seisaku/it/open-data/index.files/151009_evacuation_space.csv>
- 国の参照：デジタル庁「自治体標準ODS（正式版）」<https://www.digital.go.jp/resources/open_data/municipal-standard-data-set-test>。指定緊急避難場所一覧は定義書Aに属し、**定義書Aは2026-08-01版**。
- 検証境界：本調査でカタログHTMLは確認したが**最新CSV配布ファイルと定義書Excelのバイトを取得・解析していない**。2026-10-08のC監査（566件）は履歴上の検証事実であり、本日再検証した値ではない。
- 前回Cの確認済みraw分布（歴史スナップショット）：`○=16`、`×=239`、`2階以上=173`、`3階以上=9`、`全階可=74`、`－=55`、計566。カウントを評価定数へ組み込まない。
- 令和8年3月修正版の**河川別**洪水ハザードマップの階数凡例は確認済みだが、**そのPDFの凡例をODS CSV「災害種別_洪水」列の値に一対一対応させる自治体の宣言は未確認**。
- 正式な CSV列固有の対応表が未確認な間、Dは `CANDIDATE/EXCLUDED` を増やさずrawと `usable_floor_raw` を保持。

### 3.2 防災課へ確認する具体的な問い合わせ事項（未送信）

1. `2026-09-25`更新CSVの列 `災害種別_洪水` の値 `○`・`×`・`－` は、それぞれ何を表すか。**「指定の有無」「施設利用条件」「河川別非開設」「常時開設」「安全性」** のどの概念か区別して教示いただきたい。
2. 同列の `2階以上`、`3階以上`、`全階可` は、**すべての対象河川・すべての洪水規模について有効なのか、河川/地区/災害想定により異なるのか**。
3. 同列 `－` は「該当なし」「指定なし」「河川別非開設」「不明」のどれか。土砂災害欄や河川別PDFの凡例をこの列に適用してよいと明記された資料はあるか。
4. 2026-08-01国のODS定義書Aと、新潟市のCSVの独自値の関係・自治体の追加規則・根拠資料（**対象列、発行者、更新日、URL**）を教示いただきたい。
5. 指定緊急避難場所と指定避難所・**現在開設中**を区別したい。CSVは静的指定情報のみか、実際の開設状況を含むか。
6. 情報利用時の最新改訂基準と公式問い合わせ窓口・許諾情報を確認したい。

Aは質問送付・自治体からの回答受領を**行っていない**。非公式な推測回答を判定根拠にしてはならない。

## 4. 実装への引き渡しと順序

| Step | Responsible | Deliverable | Required acceptance |
| --- | --- | --- | --- |
| A1 | A | 本資料、公式Source一覧、ページ版・未確認事項・実際の利用階rawの証跡 | 本PRをレビュー、正式なrawアーカイブ／SHA256は別途記録 |
| A2 | A + 自治体 | 新潟CSV列固有 `raw value → official meaning` 対応表（未確認は未確認） | 担当課公文書または公式FAQ/公開仕様への直接リンク・日時 |
| A3 | A | 江戸川の各公式HTML行と位置CSVの人手照合用台帳（架空の一致を記載しない） | 出典行ID、双方原文、住所・施設名・版、レビュー状態 |
| D1 | D | 必要なら既存D Adapter/Scenarioに**後方互換**の住所・公式行追跡を追加。既存ID・座標・rawは不変 | 単なる名寄せ結果を確定joinとしない。Contract互換はB/E/Cでレビュー |
| D2 | D | Aで承認済みの意味・施設対応に限定してシナリオ結果を更新、未確定はUNKNOWN | 合成fixtureで判定増加と fail-closed の両方を再現 |
| C1 | C | 公式HTML/CSV行→照合台帳→Scenario→GIS表示をDから独立して監査 | raw digest/版/名称と住所/一対一/洪水意味の一致 |
| B/E | B/E | 表示区分の根拠と利用階条件・未判定を可視化 | 開設・危険・推奨への短絡禁止、GSI別Sourceを維持 |
| Captain | Human | main統合・公開デモ採用可否 | 最新main、Required test、C独立承認、#48 / #89との整合 |

## 5. 判定のまま残すケース（データ安全テスト条件）

- 名称だけ一致、住所が欠落・矛盾、2施設が同名、廃校等の旧称だけが一致：**UNKNOWN**。
- 江戸川公式HTMLに当該名前がない：**UNKNOWN**、EXCLUDEDにしない。
- 江戸川「大規模水害では使用不可」と記載された旧校舎：その条件をそのまま保存するが、単独洪水一般のEXCLUDEDに自動変換しない。
- 新潟ODSで `×` とされる行：正式な洪水列の意味が承認されるまで **UNKNOWN**。
- 新潟ODSで `2階以上` とされる行：**階条件rawを残したUNKNOWN**、無条件CANDIDATEにしない。
- GSI公式掲載データとDが同地点に見える：**別Source**。共通キーのない紫点とD点を自動joinしない。
- C未実施／自治体の公式定義不在／ソース変更／HTTP取得失敗：**UNKNOWN**、未収録・未取得は施設なしを意味しない。

## 6. 今回の判定と追跡可能性

**A事実調査：ページ構造・自治体担当・出典の更新日まで確認。  
A施設別照合：NOT DONE。  
A新潟CSVの列固有意味：NOT VERIFIED。  
D評価変更：NOT DONE。  
C独立受入：NOT RUN。  
E地図の現在の黄土/青/灰マーカー：既存D statusの表示のみ。**

10/22の発表で言えるのは、**「出典がある条件を保全し、判定不可ならそう表示する」**こと。施設単位で洪水適合性が確定したと主張してはいけない。

## 7. 原本を入手してからA照合台帳を生成する手順

- A専用の候補台帳生成: `data-research/tools/edogawa_review_ledger.py`。合成テスト: `data-research/tests/test_edogawa_review_ledger.py`。
- 入力は (1) 江戸川区の水害待避施設ページを保存したHTML（HTTPレスポンス原本と一致するかは別途C検証）、(2) 江戸川区が公開する位置施設CSVの原本、(3) Dが同じCSV原本から生成したRegionExport JSON。原本をこのrepoへコミットしない。
- 出力は未確認候補台帳JSON、各入力SHA256、公式HTML表・行、施設名・住所・使用可能階数の原文、厳密な施設名一致の調査ヒント、別ソース住所の有無。
- 表示上の注記 `(注)` を末尾から外すのは名称の調査ヒントに限る。名前が一致しても `VERIFIED_PAIR` にはせず、出力ステータスは常に `UNREVIEWED` または `CONFLICT`。洪水Scenario判定は増やさず、現行UNKNOWNを維持する。

実行例（Windows PowerShell、ファイルパスは保存した場所に応じて変更）:

~~~powershell
cd C:\HINANEX
python -m unittest discover -s data-research/tests -p "test_*.py" -v
python data-research/tools/edogawa_review_ledger.py --water-html C:\HINANEX-evidence\edogawa-water.html --location-csv pipeline/data/raw/edogawa/20251211_hinanhokan.csv --region-export pipeline/data/output/edogawa.json --out C:\HINANEX-evidence\edogawa-proposals.json
~~~

作成した `edogawa-proposals.json` は**内部確認用で正式な施設名寄せ結果ではない**。A行と元データ照合 → C独立受入 → DのScenario意味論審査 → C回帰テストという経路を経ること。住所・施設名の対応付けだけで洪水指定や開設中を証明しない。

### 今回の未検証範囲

2026-10-10の初回調査では公式CSV原本を取得できなかった。その後、ユーザーが公式CSVの保存ファイル、旧D RegionExport、江戸川区公式水害HTMLの保存ファイルを本チャットに提供した（後述§8）。**自治体サイトからのA独立再取得、当該バイトのオンライン最新版一致確認、C独立受入、洪水別の施設適合性判断は引き続き未実施。**また既存GitHub required `test` workflowは `data-research/tests` のunittestを呼ばないため、当該単体テストをローカルで別途実行する必要がある。CI greenをAツールの実行成功と表現しない。

## 8. 2026-10-10 ユーザー提供の3ファイルから得た一次照合結果（未承認）

### ファイル内容とSHA256（アップロードされた保存版に対する測定値）

| Input | Bytes | SHA256 | 留保 |
| --- | ---: | --- | --- |
| 江戸川区水害待避施設HTMLを保存したページ | 78,357 | `0d7dbf91ce630643f4868cf9d8547eb7acb4398035304d91833731956c44e772` | 公式URLがHTML metadataに埋め込まれている保存ページ。HTTP原本の最新一致やサイト再取得は未検証 |
| `20251211_hinanhokan.csv` | 24,777 | `64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea` | ユーザーが保管したCP932 CSV。市区側の現行バイトとの独立照合は未実施 |
| `edogawa.json` | 83,405 | `f285f9cadb9424a79f0107ddadccd7ba64f2b807f43fea54291d5fc99672da7a` | 旧D RegionExport（元の配布データではない）。`scenarios`のない古いエクスポートなので現行GISと置換しない |

### 原文を保存したままの照合（Aの調査ヒントのみ）

- HTMLの表ヘッダーは2表とも `番号/名称/住所/電話番号/使用可能階数`。保存版で**111施設行**（1表目102、2表目9）。同名の重複行は検出されなかった。
- `20251211_hinanhokan.csv` は `名称/URL/災害種別記号/コメント/緯度/経度` の**152行**。**`住所`・`所在地`列は存在しない**。従ってD PR #135の住所の同一CSV列からの任意取得は、この元ファイルでは値を増やさない。
- `edogawa.json`は`region.code=13123`、`shelter_location` **152行**。元CSV各行の名称・緯度経度・既存DのSHA256施設IDが**152/152対応**。全152レコードの`address=null`。施設区分は112避難所、40補完施設。あくまで**既存CSV→既存JSONの再現性確認**で、公式水害HTMLとの施設同一性認証ではない。
- 公式HTML **111行 → 56行**：空白・末尾`(注)`だけを取り除いた名前から**1件ずつの一致候補**。
- 残り **52行**：学校名の`第二→二`等の番号略称、`高等学校→高校`等の**限定的な名称略称規則**による1件ずつの候補。これは同一施設を認証していない。
- 残り **3行**：未確定の人手調査対象（`旧下小岩小学校` / `都立 葛西工高等学校` / `私立 関東一高等学校`）。特に旧下小岩小学校には`大規模水害では使用不可`という別個の条件があるため、`下小岩小学校`と`旧下小岩小学校（体育館のみ使用）`を同一視しない。
- `108件`は**名前由来の1対1の提案候補**の数。**C独立検証済みペア=0**、**新規CANDIDATE/EXCLUDED=0**。残る44件の位置レコード（40補完施設を含む）がこの**108件**の名前ヒント一覧に現れないことは、施設自体の不存在・洪水不適合を意味しない。
- HTMLの階数raw分布：`2階以上=62`、`3階以上=40`、`すべての階=7`、`地下を除くすべての階=1`、`大規模水害では使用不可=1`。これらは**水害待避施設ページ原文の属性**で、洪水単独Scenarioでの安全性や現開設を証明しない。

この集計に合わせA補助ツールに**限定的な略称一致ヒント**を追加した（すべて`UNREVIEWED`、複数候補・住所矛盾は`CONFLICT`）。実測台帳はChatGPT作業用ファイルとしてExcel/CSV/JSONで提供したが、保存HTMLやユーザー提出ファイルの原本・生成台帳はGitリポジトリへ無断でcommitしていない。

**今後の完了条件:** 最新原本の版一致確認 → Aの施設行台帳確認 → Cの施設同一性独立検証 → D/Cによる水害待避と洪水単独指定の意味論判断 → 初めてD施設Scenario結果を更新可能。名称のみでの自動確定は引き続き禁止。


## 2026-10-13 Live original source regenerated A proposal (UNAPPROVED)

**Retrieval succeeded** on GitHub-hosted read-only isolated runner via shared Draft PR #139, run https://github.com/1kz-ma1/HINANEX/actions/runs/38330877147 . Original seven official raw responses and SHA256/HTTP manifest are retained outside Git as artifact #11781594957 until 2026-10-20.

Source revision evidence:
- Live municipality water-facility HTML SHA256 **96001e1a22cdc19580f0c4483e01f2f2e1e6d8b2c595ee5d751f24bf836d4deb**
- Live municipality original location CSV SHA256 **64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea**
- Historical 2026-09 D RegionExport SHA256 **f285f9cadb9424a79f0107ddadccd7ba64f2b807f43fea54291d5fc99672da7a** (NOT current Scenario export)
- Regenerated local UNREVIEWED A candidate ledger SHA256 **eac4a9f907901f8931cdf9e8f7de51fb5fa3313934c8200f0cbd4b79910749d4**

The original municipality CSV is byte-identical to the archived original. The live water HTML's full byte SHA differs from the old browser-saved page, but 111/111 official water table rows are semantically the same on number, name, address, phone and usable floor.

Using a local reconstruction of PR #133 A name-hint proposal generation logic (not a new GitHub checkout run), outcome is 111 rows: 56 normalized-name hints, 52 controlled-abbreviation hints, and 3 manual-review cases (旧下小岩小学校 / 都立 葛西工高等学校 / 私立 関東一高等学校). Formal matched physical-location C-approved pairs = 0. Flood CANDIDATE/EXCLUDED added = 0. Old/current Shimo-Koiwa remain distinct facilities despite sharing one website URL.

**Limitations:** A local reconstruction is not evidence of running the exact PR #133 script or full A suite. Independent C locally rechecked original bytes and CSV-to-historical D row/ID/coordinate/URL consistency (152/152), but human C pairing is NOT approved. The old D export cannot replace current Scenario results. D/C must separately decide the semantics of municipality water-disaster standby vs flood-only eligibility before classifying any record. Original bytes and derived JSON are NOT committed to Git.

Next gate: run PR #133 exact generator with the live archived municipal HTML and current CSV/D export, validate identical source SHA256 in C, and submit candidate documents for independent C human physical-site identification.


## 2026-10-13 exact A generator now rerun against CURRENT D (replaces historical D limitation)

GitHub Actions run https://github.com/1kz-ma1/HINANEX/actions/runs/38332536238 **SUCCESS**: on a single isolated runner, seven official HTTPS originals were collected, source-pinned D's actual current RegionExport generated, then **the exact A PR #133 edogawa_review_ledger.py script was run** against that new D JSON and same official water HTML / position CSV. The exact C PR #136 script independently compared A, D and both raw sources and passed.

Source SHA256s: official water HTML 96001e1a22cdc19580f0c4483e01f2f2e1e6d8b2c595ee5d751f24bf836d4deb; position CSV 64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea; **current D RegionExport c09a3913052412566825fbe6df57f165c5a334b4e7d781a6051e8e12bb80ad28**; new source-pinned **A candidate JSON 45bc77823b766d33ce6ffdb9fabfca7afb29458d4ab008fabb9e353be1982c32**. The former locally reconstructed A output SHA eac4... referenced earlier was bound to a historical D export, so must not replace the new audited file.

A output: 111 rows, 56 normalized-name hints, 52 abbreviation hints, 3 individual manual reviews (旧下小岩小学校, 都立 葛西工高等学校, 私立 関東一高等学校). All UNREVIEWED/CONFLICT, A reviewed pairs = 0 and Scenario classifications added = 0. C source consistency succeeded for 111 water rows and 152 current D location rows, **NOT human C approval**. Cross-source physical identity and water-standby vs flood-only meaning remain unresolved. Source bytes, resulting A JSON and D RegionExport were saved only in private GitHub Actions artifacts / user handoff, not committed or deployed.
