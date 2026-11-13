# A / F02 江戸川区「避難所・避難所補完施設」利用条件・出典スコープ事前調査

- 作成日: 2026-11-13 (JST)
- 対象: 江戸川区の避難所・避難所補完施設 CSV → D RegionExport v0.9 → B F02 read-only consumer
- 関連: A Issue #366、B Issue #355 / Draft PR #357、C Issue #364 / Draft PR #365
- **状態: AIによる一次資料の机上確認済み／人間の個別レビュー未実施／データ再配信・一般公開の承認なし**
- 判断対象は利用条件、出典、資料の範囲の追跡。防災データの採点、施設指定、物理的同一性や災害安全性の評価は行わない。

## 一次資料の観測台帳

| Source key | 発行元・媒体 | 公式URL | ページ記載の時点 | 確認事項 | 認定できない事項 |
| --- | --- | --- | --- | --- | --- |
| municipal_map_list | 江戸川区／HTML地図データ一覧 | https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html | ページおよび表の更新日 2025-12-11 | 防災欄に「避難所・避難所補完施設（CSV）」を掲載。地図データ全体にCC-BY（表示）を掲示 | CSV個別行の指定有効日、避難所の開設状態、実際の入口・敷地安全 |
| municipal_locations_csv | 江戸川区／地図データCSV（CP932） | https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv | ファイル名に20251211。公式一覧の更新日は上記。CSV自体の初回公開日・法的適用日は未確認 | 利用者Macで独立取得したCSVとD raw CSVのSHA-256同一（下記）。Cが全152行のSource→D変換整合を報告 | ファイル名の日付が全施設の法的指定日であること、元URL・名称による施設の敷地同一性 |
| opendata_terms_page | 江戸川区／HTMLオープンデータ利用条件 | https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/index.html | ページ上に明示された更新日なし | 個別に定めるものを除きCC BY 2.1 JP、改変・二次著作物作成可能、区データ利用を表示、内容は予告なく変更・削除され得る | CSVの個別例外・第三者権利が存在しないこと |
| opendata_terms_pdf | 江戸川区／PDF利用規約（3ページ） | https://www.city.edogawa.tokyo.jp/documents/10685/20150914_kiyaku.pdf | 文書日付 2015-09-14（公式利用条件ページの現行リンクから確認） | 商用利用、出典URL、加工した事実の別表示、区が作成したような誤認の禁止、第三者権利確認、利用者責任 | 第三者権利の個別クリアランス、自治体によるHINANEX公認 |
| cc_by_2_1_jp | Creative Commons／ライセンス告知 | https://creativecommons.org/licenses/by/2.1/jp/ | このライセンスは2.1日本版（更新時点を推定しない） | 帰属表示・リンク・変更表示、権利者の支持を示唆しないこと | データセットごとの著作権・自治体の個別許諾 |
| municipal_disaster_portal_guidance | 江戸川区／防災アプリ・ポータル案内HTML | https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/oshirase/bousaiapuri.html | ページ更新日 2026-04-15 | 災害時の避難所開設・混雑情報等をリアルタイムに配信する案内 | 地図CSVの静的施設属性を「開設中」「安全」と扱う根拠 |

※取得日（閲覧日）は上記作成日。Webページの検索/閲覧結果をAIが確認したもので、署名済みの自治体原本アーカイブではない。HTTP ETag/Last-Modifiedは正式公開日・効力発生日として採用しない。

## 原データ・変換の技術証拠（Aによる独立法務承認とは区別）

- 利用者Macで2026-11-13に取得した `edogawa-official.csv` とD raw `20251211_hinanhokan.csv` のSHA-256はともに `64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea`。
- C独立ツール（Issue #364）の利用者Macログ: `C_SOURCE_TO_EXPORT_CONSISTENT`、Source/Normalized/Exportが152件、不一致0。
- `source_origin=LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED`。CSVの発行者・版・有効期限・権利を暗号学的に証明したものではない。Rawと生成JSONはGit/Renderへ格納しない。
- `facility_type` はDが元名称の「（補完施設）」文字列に基づいて付与した内部分類。公式な指定区分の証明ではない。`supported_disasters` や現在の開設・入口/容量などは未承認／未評価。
- 江戸川区一覧には別の「避難場所」データもある。避難所・避難場所・水害時待避施設・GSIの指定緊急避難場所を同一視しない。

## 利用条件とUIの事前照合

- 区のオープンデータ**一般条件**は個別例外を除くCC BY 2.1 JP。具体的なCSVに例外がないことや第三者権利処理は**未確認**であり、無条件で「公開許可」へ昇格させない。
- 区の規約では**出典情報（元資料のURL）**と**HINANEXが加工した事実**は区別して表示する。区による作成・保証・共同運営を示唆しない。
- B Draft #357のDataset単位クレジット、条件付きライセンスリンク、非公式表示は事前実装済み。正式な製品・法務審査としてのチェックは別。
- 静的な施設一覧は江戸川区の防災アプリ・ポータルにある**現在の開設・混雑情報の代用ではない**。

## 人間に残る最終判断（未署名）

| Gate | 承認が必要な内容 | 現在の扱い |
| --- | --- | --- |
| A-L01 | **当該CSVそのもの**の個別ライセンス指定/例外と第三者権利を資料ごとに再確認。元URL、版/取得時刻、適用範囲を記録 | PENDING |
| A-L02 | 出典URL、利用日、編集加工の明示、CC条項リンク、非公式/非公認表記のUI完成版を法務・責任者が確認 | PENDING |
| A-L03 | 個々の施設種別と名称、公式資料の用語差と適用時点を確認。法定指定・安全性へ拡張する場合はCに別の一次資料を渡す | PENDING |
| B-U01 | 小画面、キーボード、VoiceOver等の読み上げ、リンク・フォーカス移動、未確認/誤誘導防止を実機検証 | PENDING |
| Owner-R01 | 配信対象、公開時の注意・更新/停止手順、誤った避難誘導を防ぐ運用と最終GO/NO-GOを署名付きで記録 | PENDING |

人間レビューは、レビュー担当者・UTC時刻・具体的に確認した資料版とURL・対象範囲・承認/保留理由を認証可能な方法で記録する。AIの事前調査やソースコードのテスト成功のみでこれらをチェック済みにしない。

**運用判定: F02は開発環境内の非公開read-only参考画面に限定。一般公開・GISの目的地・ルート案内・避難先推薦をNO-GO。**
