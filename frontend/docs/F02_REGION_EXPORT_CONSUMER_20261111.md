# F02 S-03 — RegionExport v0.9 read-only Consumer（実装仕様 / Draft）
2026-11-11 / Issue #355 / owner P0

## Decision
- **1地域のみ**：江戸川区 region.code=13123。既存D出力 pipeline/data/output/edogawa.json を frontend/src/region-export-loader.js から読む。配信パスは frontend/f02.html を基準として既存の ../pipeline/data/output/edogawa.json を解決する。
- 合成F02 Prototype (frontend/prototypes/f02-shelter-explore) は改変しない。新画面 frontend/f02.html は読み取り専用で、既存本番ナビにはまだ接続しない。
- Source of truth: RegionExport.meta.schema_version=0.9 / datasets[requirement_code=shelter_location]。既存GISやFrontendの評価ロジックを流用せず、表示専用の独立モデルに限定する。
- Dのrecordsの ID/name/address/facility_type/supported_disastersを保持する。supported_disasters は**D正規化レコードの値**であり、本人の避難先として適合・安全・開設中とは表示しない。D ScenarioやGSIとの名前照合・結合は**しない**。
- Dataset.evidence[] の source_name / publisher / published_at / fetched_at / HTTPS source_url を **Dataset全体の根拠**として表示する。個々のレコードと出典行の1対1照合を本UIが保証することはできない。公開日と取得日時、承認時点は混同しない。
- 施設座標は**有無のみ**を表示。数値があっても公式の範囲・入口・位置承認とはみなさず、地図/経路の目的地には渡さない。
- 見つからないDataset、取得/Parse/Contract失敗、Datasetのレコード0、検索一致0を分離し、合成fixtureにfallbackしない。
- 一覧の初期表示は最大50件。名称検索は全レコードに適用する。件数はこのDatasetの記録数であり自治体内の全避難施設数ではない。
- 新データにはネットワーク送信、ブラウザlocalStorage、個人入力、位置取得、外部API呼出なし（既存D JSONのsame-origin fetchのみ）。

## Implementation paths
- frontend/f02.html, frontend/f02.css
- frontend/src/f02-page.js: DOM textContent only, remote/unsafe URL notリンク化
- frontend/src/f02-shelter-reference.js: D v0.9のfail-closed表示モデル
- frontend/tests/f02-shelter-reference.test.js: 合成の契約テスト

## Data and safety gates
- DのDataset records配列はJSON Schema上additionalProperties=trueだが、Consumerは実際に利用するフィールドの型を確認する。ID重複・region不一致・schema変更・不正座標は表示停止。
- 災害に対応する正式指定、開設現況、敷地/入口、収容可能人数、ペット/配慮事項、災害時通行可能性を**導出・表示しない**。
- Dataset.evidenceの存在は、施設別のA/C独立検証や公開権限の代替ではない。
- 公式資料の更新時点が不明なら「未確認」。未確認を「なし」「安全」「非公開」に読み替えない。
- 統合候補になるには、生成済み実D JSONでのHTTP読込、Chrome実操作、独立C検証・再配信条件、最新mainでのCI、Merge Captainによるスコープ審査が必要。Draft PRの通過だけでは公開許可なし。

## Verification status
- Source/contract review: root/frontend AGENTS、pipeline/contracts/region_export.schema.json、pipeline/docs/HANDOFF_B.md、既存B loader、GIS D adapterを確認。
- Locally run: **NOT RUN**（GitHub専用実装環境。ローカルcheckoutなし）。
- Browser HTTP: **NOT RUN**（今回の提出時。後続検証が必要）。
- Real D JSON read: **NOT RUN**（pipeline/data/output/*.json は生成成果物でrepository未収録）。
- Official row-level evidence/C acceptance: **NOT RUN**。
- CI: Draft PR作成後に確認。成功してもC/公式意味の承認とは区別。

## Next decision
このPRでは安全なB読み取り専用ページが成立するかを検証する。次のF05でのF01地域文脈引継ぎ、F07の終点承認、地図/GISへの統合を含めない。仕様の拡張は本IssueとDraft PRで人間のレビューを受ける。
