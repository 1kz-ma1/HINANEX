# 複合災害の確認事項・期限切れ・条件競合 Phase 1（2026-10-23）

**DRAFT / SYNTHETIC-ONLY / UNKNOWN-ONLY — NO DISASTER SAFETY CLAIM**

## 目的

Phase 0 (#306) の行動カテゴリーを変えずに、**同じ地域の異なる災害を同時に扱うための入力整合性**と、公式の原本・区域・経路の確認が足りない場合の状態を区別する。
施設を選ぶことと、移動すべきかを判断することを分離する。資料の欠落から「危険がない」「安全な高台」「安全な自宅」「避難先なし」を推論しない。

## 実装済み範囲（このPR内、main未統合）

- `MultiHazardFixture`: 単一地域、1～5種類の重複しない災害、タイムゾーン付き模擬時刻、識別子、synthetic固定。
- `SyntheticCue`: ハザードと Phase 0 の確認事項IDを完全一致させた訓練用チェックポイント。 `SYNTHETIC_PRESENT` / `SOURCE_UNAVAILABLE` / `EXPLICITLY_MISSING`。Presentには時点・期限必須。範囲外のカテゴリ、未来時点、重複・混入を拒否。
- `CueReviewState`: `NOT_PROVIDED`、`SOURCE_UNAVAILABLE_IN_FIXTURE`、`MISSING_IN_FIXTURE`、`EXPIRED_SYNTHETIC`、`SYNTHETIC_ONLY_UNVERIFIED`。**すべて `UNKNOWN`** の付帯状況にすぎない。
- `ConflictReview`: 災害をまたぐ独立確認を促す **可能性のチェック項目**。複数災害の共存時、洪水/津波+土砂（高台だけで安全を断定しない）、洪水+高潮（別情報源・範囲を混ぜない）。現実の区域の重なりや、危険地点の発生を検出したわけではない。
- `MultiHazardActionReview`: Phase 0の `ActionReview` を災害別に並列出力。どの `ActionReviewItem` も `UNKNOWN`。公的イベント承認・災害時公開許可は `False` 固定。名前・住所・階数・精密GPSを出力しない。
- `replace_multi_hazard_fixture` / `stop_multi_hazard_drill`: モードやシナリオ切替時に全ての旧cueを捨てる。事前情報の地域が異なり建物情報が残る場合は fail closed。

## 注意事項

- **synthetic fixtureの`SYNTHETIC_PRESENT`は「存在することにした訓練情報」であり、現実の出典・検証・最新性を確立しない**。期限内でも `SYNTHETIC_ONLY_UNVERIFIED`。期限切れは `EXPIRED_SYNTHETIC`。
- `ConflictReview` は地図による区域の交差、危険の判定、施設の認定、屋内/屋外行動の推奨順位ではない。複数災害と確認事項の **条件衝突を今後評価するための検討マーカー**。実際に危険な区域であると主張しない。
- 公的警報・自治体指示・GSI災害別タイル・D自治体資料・道路の通行状態・施設の最新開設状況は本モジュールへ入らない。 `LIVE` 文字列は受け付けない。
- `model_copy(update=...)` は検証を迂回する。外部入力に対しては `model_validate`。プロファイルは保存せず、スマートフォンUIに接続しない。
- 複数地域の同時災害、ハザード区域、GSIの実データ統合、実災害行動の判断、優先順位付け、経路およびB/E公開Contract化は今後の独立レビューを要する。
- Phase 0 (#306) の`DrillFixture`、`ActionSession`、`RegionExport`、`ScenarioResult`、既存 `UNKNOWN`、正式なsource provenanceには変更を加えない。

## 独立テスト

合成のみで、次を検証する：洪水+土砂、津波+土砂、洪水+高潮、重複・異種cue注入、区域/情報欠落、供給不能、時点の期限切れ、未知ハザード、旧データの持越し、地域・個人情報境界、順序不変、公式偽装/LIVE偽装の拒否。

```bash
cd pipeline
python -m unittest tests.test_action_context_multi -v
python -m unittest discover -s tests -v
python verify_d_mvp.py
```

## 次の段階

1. 公式ソース・情報時点・空間適用範囲・施設資料・道路・建物の情報をソース単位で承認する契約を **A/C/Dレビュー付きの別PR** として設計する。
2. hazard間の**実際の空間的な競合検出**は、それぞれの出典・同一座標系・範囲・バージョンが独立受入された場合に限る。今はどの候補も昇格しない。
3. プレイベント任意入力の保存・削除・同意・端末のみ保存について、プライバシー契約の承認を別で実施する。
