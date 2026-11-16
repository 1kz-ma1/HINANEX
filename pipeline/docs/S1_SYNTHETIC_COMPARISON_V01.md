# S1-P1 — 合成条件比較レポート（D内部・非公開）

**2026-11-16 / IMPLEMENTATION CANDIDATE / NOT ADOPTED FOR REAL-WORLD SHELTER USE**

## 目的
S1-P0の `NarrowReport`（[PR #391](https://github.com/1kz-ma1/HINANEX/pull/391)）が返す合成結果を、複数の架空レコードで**何の条件が一致・不一致・不明か**まで順に比較できる内部レポートへ整理する。Issue #305の「抽出 → 比較 → 本人選択」の基礎に位置付けるが、今回は**実際の避難先選定・UI/経路・公式Sourceは含めない**。

S0はPR #376、S0独立リプレイはPR #384がmain統合済み。S0→UI表示Contract提案PR #386/#387はDraft・未承認であり、この実装には不要。koutaのF05 Draft #371の `frontend/**`、E GIS、RegionExport v0.9、既存の `flood_scenario.py` / `ScenarioResult` の意味は変更しない。

## 最小機能・出力

実装は `pipeline/src/hinanex/s1_synthetic_comparison.py`。`compare_synthetic_conditions(state, request, records, now)` が**必ずその時点の**S0 `Session`を使ってS1-P0 `narrow_synthetic_references()`を再実行する。過去の `NarrowReport` を引数として受け取るAPIは持たない。

- `SyntheticComparison` は `schema_id=hinanex.d.s1.synthetic_comparison.internal.v0.1` を持つ**内部専用**のdataclass。正式な共有API/Schemaではない。
- `rows[]` は架空の `synthetic:` IDごとに、P0の `MATCHED_SYNTHETIC / NOT_MATCHED_SYNTHETIC / UNKNOWN`、reason_code、要求された条件ごとの `EXPLICIT_SYNTHETIC_TRUE / EXPLICIT_SYNTHETIC_FALSE / UNVERIFIED / NOT_EVALUATED`、 `missing`/`failed` を保持する。
- `NOT_EVALUATED` は別fixture・地域/災害範囲外、未観測・期限切れの合成レコード。**元条件の真偽を比較面へ漏らさない**。
- `UNKNOWN` は、同一対象でも要求された条件が未取得/`None`であるケース。別の条件が `False` でもP0に従い不明を優先。**UNKNOWNを自動的に「不適合／利用不能／安全」へ変換しない**。
- `totals` は `matched_synthetic / not_matched_synthetic / unknown` の3値。並びは入力順、**安全順、距離順、評価点、避難施設ランキングではない**。
- `evaluated_at` と`expires_at` は合成セッションの時点と失効時刻。途中で地域変更、STOP/SOURCE_FAILED/RESET、旧generation、期限切れに至れば、**BLOCKED + 空rows + 条件空 + totals全0**。期限終端は排他的。
- 報告には `synthetic_only=true` / `official_acceptance=false` / `live_data_verified=false` / `facility_safety_verified=false` / `route_safety_verified=false` / `release_approved=false` を固定する。
- `comparison_as_dict()`と`comparison_as_json()`は**固定合成のローカル観察用**。B/E向け正式Serializer、API、保存/配信Contractではない。メモリ上の古いレポートを有効とみなす仕組みは導入しない。

## 実行

`pipeline/` から:

~~~sh
python -m unittest discover -s tests -p "test_s1_synthetic_comparison.py" -v
python -m unittest discover -s tests -v
python preview_s1_synthetic_comparison.py --json
~~~

CLIは固定の日時・架空IDのみを使用する。`pet_support` と `step_free` は**合成テスト用の架空のTrue/False/Unknownラベル**で、実施設のペット受入やアクセシビリティを判断するものではない。例示結果は `MATCHED=1 / NOT_MATCHED=1 / UNKNOWN=2` の比較を表示するための固定サンプル。

**QA区分:** `NOT_REQUIRED`（純粋Python・合成CLI）。公式Rawの再取得、実地調査、実ブラウザや端末での表示、安全性・開設/位置/経路・一般配信はすべてNOT_RUN/NO-GOで、独立した承認を必要とする。

## PR分離・依存
- P0 PR #391がmain未統合の場合は、**P1をP0ブランチをbaseとしたDraft PR**で提出する。
- P0がmainに入ったらP1を最新mainに追従させ、required `test` とD/C/B/E/Deploy scopeの全検証を実行する。mainの直接push/自動mergeは禁止。
- **正式な比較対象としての実施設採用**にはA原本・C施設単位追跡・Dの災害適合/同一性/時点・公式資料利用条件、人間承認が別途必要。F05画面実装とS0→UI Transport/Contractの採否は後回しのまま維持する。

本スライスのPASSは、合成レコードの評価理由が追跡可能な形になったことだけを示す。避難先の候補推薦、実災害利用や公開の安全性は証明しない。
