# 避難行動の共通入力・未評価モデル / Phase 0（2026-10-23）

- 状態: **DRAFT IMPLEMENTATION — SYNTHETIC ONLY / NO SAFETY DECISION**
- 対象: Issue #305 / #301。既存の施設洪水Scenarioとは独立するD内部ライブラリ。
- 重要: このPRは **避難判断AIではなく、行動の検討に必要な入力と不足確認項目の型**。
  結果の全 `ActionReviewItem.status` は `UNKNOWN` 固定。
- 本フェーズではB/E/GISへの出力・UI接続・公式データ・個人情報の保存・GPS取得・
  正式な避難勧告・候補選定・経路計算は一切行わない。

## 目的と設計境界

施設選択より上位に次の *検討カテゴリー* を用意する。
1. `VERIFY_OFFICIAL_INFORMATION` — 公式情報・時点・範囲を確認する
2. `LEAVE_HAZARD_AREA` — 立退き行動の成立条件を調べる
3. `INDOOR_SAFETY` — 屋内安全確保に必要な条件を調べる
4. `EMERGENCY_SAFETY` — 緊急安全確保に必要な状況・条件を調べる

ここでの「順番」は安全性の優先順位ではない。自宅待機、移動、上階への移動のいずれも
本モジュールは**推奨・承認・除外しない**。カテゴリー定義と不足証拠のキーは、
公的な防災指針との照合作業に備える**非網羅的な内部メモ**であり、
公式の判断基準へ転用するには別の安全レビューを要する。

### データの形

- `PreEventContext`: 平時の任意入力。`region_code`, `occupied_floor`,
  `upper_floor_access`, `revision`。入力値は常に `SELF-REPORTED` 相当の
  未検証情報であり安全性の根拠としない。
- `ActionSession(mode=NORMAL)`: 実イベントを受信しない通常状態。
- `ActionSession(mode=DRILL, drill=DrillFixture(...))`: synthetic fixtureの存在・
  地域・災害・タイムゾーン付き模擬時刻が必須。公開APIには `LIVE` モードが
  そもそも存在しない。
- `ActionReview`: UI統合前の内部出力で、各行動 `UNKNOWN`、
  `official_event_verified=false`, `published_for_disaster_use=false`,
  `reason_codes`, `evidence_to_check` を返す。居室階数そのものは出力しない。
- `start_drill`, `stop_drill`, `replace_preparation` を明示的な状態遷移として
  用意。別地域に建物情報を黙って引き継がず、設定変更時はDRILLを破棄。

### 安全・個人情報の制限

- **保存機構を実装しない**。後続のUIは明示的同意、端末内保存の明示、
  保存範囲、削除、再確認、必要な場合の暗号化等のプライバシー仕様を別途レビューする。
- 住所、正確な緯度経度、名前、健康状態、連絡先、身体事情などは型に含めず、
  任意の追加フィールドも拒否。健康・支援条件を扱う場合は別設計・最小化審査。
- 取得した災害原本、D `RegionExport.scenarios`、GSI `skhb01`/ `skhb02`
  との自動joinは行わない。
- 未取得・未評価は「安全」「施設が存在しない」「自宅でよい」を意味しない。
  必要証拠キーが列挙されても**安全性や行動の実行可能性は証明されない**。
- `model_copy(update=...)` はPydanticの入力バリデーションを迂回するため、
  untrustedなJSONを受け入れる際は必ず `model_validate` を使用する。
  状態変更は上記関数で行い、更新時に古いDRILLを無効化する。

## 小さな例（合成のみ）

```python
from datetime import datetime, timezone
from src.hinanex.action_context import (
    ActionSession, PreEventContext, DrillFixture, HazardKind,
    start_drill, review_action_context,
)

profile = PreEventContext(region_code="13123", occupied_floor=2)
session = start_drill(
    profile,
    DrillFixture(
        fixture_id="exercise_1", hazard=HazardKind.FLOOD, region_code="13123",
        simulated_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
    ),
)
review = review_action_context(session)
assert review.synthetic is True
assert all(option.status == "UNKNOWN" for option in review.options)
```

## 次の実装フェーズ（NOT IMPLEMENTED）

- **P1**: 事前入力のプライバシー・保存と削除・同意仕様、画面契約、
  DRILL→NORMAL時の画面状態クリア（別領域のレビュー）。
- **P2**: 公式の `EventContext` と公表時点、対象範囲、複合災害、
  相互矛盾、オフライン/通信失敗、独立A/C根拠ゲートの型をAdd。
  公式の避難情報を独自の安全判断へ再解釈しない。
- **P3**: 経路・避難施設・屋内安全性などについて条件単位の
  Evidence付き評価ルールを専門家レビューと合成/実データ独立検証後に追加。
  `UNKNOWN`→候補昇格は禁止のまま、正式契約変更は別PR。
- **P4**: ユーザーの理解のためのUIと合成DRILL E2Eを接続。
  現行 #303の施設比較は下位の参考実装として維持。

## テスト範囲

`python -m unittest tests.test_action_context -v` または
`python -m unittest discover -s tests -v` (pipeline/から実行)。

ハザードごとのUNKNOWN維持、模擬/通常切替、タイムゾーン、
不正なLIVE/公式偽装、無断の個人情報フィールド、地域移動時の
古い建物情報、DRILL停止、状態更新時クリア、結果出力への
生の階数混入を合成ケースで検証する。
