# S1-P2 — 合成比較結果の明示的レビュー選択（D内部・非公開）

**2026-11-16 / SYNTHETIC-ONLY / NOT APPROVED FOR REAL-WORLD SHELTER SELECTION**

## 目的と対象

Issue #305で目指す「抽出 → 比較 → 本人選択」のうち、画面を伴わない**明示的な閲覧対象選択**だけを実装する。S1-P0条件抽出（main PR #391）、S1-P1理由付き比較（main PR #394）、S0訓練モード（main PR #376）を再利用し、**同一メモリ内の有効な架空レコード**を選んだという事実だけを返す。

**実際の避難先の最終選択・施設の推薦・安全性・公式災害情報は扱わない。** S0→UI連携のDraft #386/#387、koutaのF05 Draft #371、F02公開ゲート #366、RegionExport v0.9、GIS Eなどには変更を加えない。

## 実装と安全なライフサイクル

- `src/hinanex/s1_synthetic_review_choice.py` に固定`dataclass(frozen=True)`の `ExplicitReviewChoice`、`ReviewChoiceResult`、純粋関数 `choose_synthetic_for_review()` を追加。
- 呼出しごとに現在の`Session`と明示時刻`now`からS1-P1の`compare_synthetic_conditions()`を**再実行**する。過去の比較結果や選択結果、localStorage、ファイル、外部通信、クロスページセッションを受け付けない。
- `ExplicitReviewChoice`は`selected_record_id`・`expected_generation`・厳密なboolean`explicit_user_action`を持つ。`False`なら選択結果は`BLOCKED`。古いgeneration・未知IDは`BLOCKED`。
- 対象と同一の`fixture`・地域・災害・有効期間に属さない行（`NOT_EVALUATED`）は**レビュー選択さえ拒否**する。期限切れ、模擬終了、地域切替、取得失敗、リセットでは`BLOCKED`かつ選択ID/条件/以前の結果を一切返さない。
- **`UNKNOWN`や`NOT_MATCHED_SYNTHETIC`の架空レコードも閲覧対象としての明示選択は可能**。これは未確認事項を理解するためであり、`MATCHED_SYNTHETIC`や災害適合性への昇格ではない。元の分類・理由・`missing`/`failed`・各条件をそのまま残す。
- 成功時statusは`REVIEW_SELECTED_SYNTHETIC_ONLY`、reason_codeは`EXPLICIT_FICTIONAL_REVIEW_SELECTION`。`review_only=true`、`synthetic_only=true`、`official_acceptance=false`、`live_data_verified=false`、`facility_safety_verified=false`、`route_safety_verified=false`、`release_approved=false`を固定する。

## 制約

- 選択結果は**一時的な計算結果**であり、現在の有効性を保証し続けるものではない。将来のUI表示時にはその時点のセッションを再検査する必要がある。
- S0の`generation`は同一メモリ状態内の世代であって、端末やタブを跨ぐグローバルなセッションIDではない。
- `pet_support`・`step_free`は架空の合成bool属性であり、実施設のペット受入・バリアフリーの根拠ではない。個人の配慮事項や位置情報を取得・保存するものでもない。
- 独立Cによる公式出典・施設同一性・避難適合・現在開設・通行可能性の証明は**別工程**。B向け共有Contract/APIも別承認。
- Device QA: `NOT_REQUIRED`（端末依存性のないPython内部の合成処理のみ）。将来のUI/B実機QAは#372で別管理。

## テストと受入

`pipeline/tests/test_s1_synthetic_review_choice.py` で23件：
- 本人の明示操作による架空レビュー選択、`UNKNOWN`/非一致の意味保持、未確認・不一致理由の区別
- 不明ID、別地域、別ハザード、別fixture、失効/未来データ
- S0通常・停止・元データ失敗・地域切替・リセット、旧世代
- 誤った型、重複/実施設ID拒否、入力不変性、セッション更新後に過去の選択を復元しない
- 施設・経路の安全、LIVE、公式受入、一般公開を偽装しない

実行（`pipeline/`から）：

~~~sh
python -m unittest discover -s tests -p "test_s1_synthetic_review_choice.py" -v
python -m unittest discover -s tests -v
~~~

必須CIの`test`成功は**合成実装の自動検証**のみを意味する。実施設・原本・人間の出典承認・実機表示・デプロイ・公開は`NOT_RUN/NO-GO`として扱う。
