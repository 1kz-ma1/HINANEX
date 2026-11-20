# 共通設計：属性ごとの出典・検証状態・表示許可

**PROPOSED / 非実行仕様。** 2026-10-30。対象はF01〜F05のすべて。既存の正式なenum、Schema、値の意味は変更しない。

## 目的

「公式資料に載っている」「機械で読み込んだ」「人が原本と照合した」「地図に参考表示できる」「避難先・経路として案内できる」は異なる命題である。単一の「信頼度80%」等に集約せず、**対象属性・原本版・観測時点・確認者・表示可能範囲を別に記録**する。

## 表示判断の観点（設計項目・新しいenumではない）

| 観点 | 記録する内容 | ダメな解釈 |
| --- | --- | --- |
| 原本の出典 | source ID / 発行者 / URL / 公式サイト上の資料・ページ | 出典URLがある=内容を独立検証済み |
| 原本同一性 | raw SHA256、取得時点、資料の発行/適用基準日、確認方法 | 取得日=資料の適用日 |
| 対象範囲 | 対象災害・行政範囲・計算シナリオ・施設属性 | 全国地図が表示される=全国データを網羅 |
| 意味の検証 | 公式記号・列の意味、資料版、Cの属性単位独立照合 | 公式rawの `○` を無条件安全へ翻訳 |
| 位置の根拠 | 座標欠損、公式参照点、観測された地物、正式指定区域の区別 | 地図ピン=敷地/入口/避難先認定 |
| 時点・更新 | 取得・元資料版・対象条件・再審査理由 | 最新の開設状況や道路通行可能性を証明 |
| 画面公開 | 何の参考情報をどこまで公開できるかを独立判断 | 公開=避難・経路の安全性認定 |

## 現行Schemaの意味を維持

- Dの`DiscoveryStatus: AVAILABLE/PARTIAL/NOT_MACHINE_READABLE/ACCESS_RESTRICTED/NOT_FOUND/UNKNOWN/NOT_APPLICABLE`、`CapabilityStatus: FULL/DEGRADED/BLOCKED/UNKNOWN/NOT_APPLICABLE`、`Gap: CONFIRMED_IMPROVEMENT/INVESTIGATION`を変更しない。
- `score=0`は評価済み・要件未達、`score=null`は未評価/判断不能。ゼロ件、元ソース未取得、通信障害、対象外も別。
- Flood Scenarioの`CANDIDATE/EXCLUDED/UNKNOWN`はD出力の既存分類。現行の公式raw記号からUIで生成しない。UNKNOWNを除外/危険/安全と読み替えない。
- **Cの命題ごとの承認**と**運営の情報公開判断**は別工程。CI成功・班員報告・AI照合・単なるURL一致を承認の代わりにしない。
- `HOLD` と `UNKNOWN` は文脈が異なるため、Contractへ新たに混入させない。F系UI向けの状態名が必要な場合はD/共通契約のレビュー後に追加する。

## 最低限のユーザー向け区別（表示文言例）

- 「公式資料の参考情報」：出典付き参考表示。施設安全性や運用中を意味しない。
- 「位置未確認／地図上では表示しません」：座標が無い、または公開許可された点がない場合。施設が存在しない意味ではない。
- 「災害時の利用可否は未確認」：公式指定/入口/開設/通行可否を勝手に補わない。
- 「この地域のデータは未確認／取得できませんでした」：空白地図を低リスク・非浸水と誤表示しない。
- 「表示の時点・出典」：予測基準年、行政資料の基準日、API取得日時等を混ぜずに分ける。

## 範囲限定の属性命題（非機械契約の例）

`{ source_id, source_version_or_asof, facility_source_key, assertion_scope, original_claim, independent_review_scope, unknowns, display_permission, recheck_trigger }`

これは**設計用の概念例**であり実際のRegionExportやAPI payloadと互換性があるとは主張しない。実装にはD/sharedの契約変更の要否、Cの必要証跡、Aの原本/ライセンスを別PRで審査。

## 否定テスト

同名別施設、異なる資料版/災害種別、未確認座標、他県の津波条件、公式タイル未取得、原本の後日変更、関連設備と避難施設の混同、手動選択をアプリによる安全推薦に変換する事例でfail-closed。端末内の事前入力が施設の属性や災害時の開設状態を上書きしない。

関連：[C再利用レビュー](../../../validation/docs/REUSABLE_REVIEW_EVIDENCE_LEARNING_LOOP_20261027.md)、[未来の募集 #342](https://github.com/1kz-ma1/HINANEX/issues/342)、[広域化 #343](https://github.com/1kz-ma1/HINANEX/issues/343)。
