# C / S0→UI候補Contractの独立検証 v0.1

**状態:** C合成のみ / DESIGN-PREFLIGHT / NOT ADOPTED（2026-11-16）。
**依存:** [shared docs Proposal Draft PR #386](https://github.com/1kz-ma1/HINANEX/pull/386)、S0実装 #376、C S0リプレイ #384。Dのproduction Adapter、B/E UI、Render配信には接続しない。

## Purpose

Issue #305のS0→B/E新共有Contractを人間レビュー前に正式採用しないため、`docs/strategy/S0_UI_DISPLAY_PROJECTION_DRAFT_V01.schema.json`の候補形式に、S0の本物の`reduce_session()/safe_view()`を呼ぶC側の**参照投影**を重ね、実出力と禁止事項を検査する。

- `validation/validation/verify_s0_ui_projection_draft.py` はC内だけの参照投影／独立検査。**Dでの実装または公開Adapterの実装ではない**。
- `validation/fixtures/s0_ui_display_draft_preflight_v01.json` は25ケース（合成のみ）。公式情報、緯度経度、施設実データ、位置入力/本人識別情報なし。
- `validation/validation/test_verify_s0_ui_projection_draft.py` は15テスト。回帰テストで検査結果と判定の区別を維持する。

## 検査観点

1. S0の`NORMAL_NOTICE`/`DRILL_NOTICE`と表示文言の完全一致。モードによる不可逆な意味変換を禁止。
2. `review_only=true` / `synthetic_only=true` / `live_data_verified=false` を厳密一致。公式データ確認済みのような偽装を拒否。
3. `fixture_id/hazard/source_authorization/observed_at/expires_at` はNORMALならすべて`null`。DRILLならS0の実fixtureに一致する合成値だけ。
4. `observed_at <= issued_at <= render_at < expires_at`。期限終端は排他的。期限超過なら内部Stateの更新イベントがなくても表示拒否。 **Cが保持する投影時刻（trusted_issued_at）とpayload内issued_atの一致も必須**。期限内でも発行時刻のすり替えをFAILとする。
5. `active_generation` は同一インメモリの現在世代と完全一致。世代番号の単独運用・他タブ/画面共有は採用しない。
6. 未知の公開キー（`facility_open`など）や欠損必須キー、タイムゾーンなし日時を拒否。元のS0で持つ希望地域`preferred_region`は候補投影へ含めない。
7. 期待FAIL/BLOCKED/NOT_RUNを「回帰の不一致」と混同しない。自動検証PASSは公式情報受理・UI実機・公表許可ではない。

## 実行（docs proposalを含むブランチに限る）

~~~sh
python validation/validation/verify_s0_ui_projection_draft.py --json
python -m unittest discover -s validation/validation -p 'test_verify_s0_ui_projection_draft.py' -v
~~~

schema案は正式なproduction JSON Schemaではない。C参照テストはスキーマの主要キー・固定フラグ・条件分岐を照合するが、**一般的なJSON Schemaエンジンの適合証明ではない**。

## 検証後の決裁ゲート

- **Draft / Depends on #386**。提案ドキュメントの採用レビューが未完了ならmainへの取り込み・公開利用・B/E統合を自動許可しない。
- 合成のPythonテストは`Device QA: NOT_REQUIRED`（端末依存性なし）。将来Bブラウザ/デモUIの新規実装は#372で`DEFERRED/BLOCKING`を別判断。
- #366の公式CSV利用条件、Render非公開ゲート、F05 Draft #371、F03保存の同意は不変。
- 正式採用の際にはD側の出力生成方式、browser側の検証、ページ遷移時の世代nonce、許可されたローカル搬送手段、UI E2E/アクシビリティをそれぞれ別PR・明示した関係者レビューで決める。
