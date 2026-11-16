# S0 — 平時/訓練モードの純粋状態モデル（D内部、合成のみ）

**日付:** 2026-11-13 JST
**種別:** 開発用実装仕様 / Issue #305のStream S・S0 / 2027-02-09 MVPに向けた先行基盤
**責務:** オーナー側の基盤トラック（Issue #360）。koutaが実装中のF01→F02→F05（PR #371）と分離。
**状態:** 内部プロトタイプ。B/Eや共有Contractへの採用、保存方法、出荷・災害安全性は**未承認**。

## 1. 成果と境界

`src/hinanex/drill_session.py` に標準ライブラリだけの決定論的な**純粋セッション状態遷移**を追加。
- `Mode.NORMAL`: 通常の入力状態。実際の気象警報・速報を取得した／現在の開設状況を確認したという意味ではない。
- `Mode.DRILL`: 明示的に開始された **SYNTHETIC_TEST_ONLY** の期限内模擬セッション。常に訓練表示文が付き、`live_data_verified=false`。
- 地域の変更、訓練の停止、元データ取得失敗、明示リセットで古い模擬fixtureへの参照を廃棄する。
- 観測時刻（`observed_at`）・期限（`expires_at`）はタイムゾーン付き。開始前／期限満了／不正値は訓練開始拒否。呼び出し側がtickを忘れても `safe_view(state, now)` は期限切れfixture情報を出さない。
- セッション`generation`をインクリメントし、古い非同期応答の`expected_generation`が現値と異なる場合は`StaleSessionError`。前地域・前訓練を復活させない。
- 希望地域の事前設定は、明示的な`explicit_consent=True`の操作でのみセッションの**メモリ**に保持し、明示削除可能。ブラウザ/DB/ファイルへの保存、GPS・住所・氏名・要配慮者情報の収集は**実装しない**。

### 互換性
- **RegionExport v0.9 / ScenarioResult / shared Schema に変更なし**。B/Eへ公開する共有APIではない。UIや他のモジュールからのimport/接続は、共同レビュー後の別Issue/PR。
- `SyntheticFixture`は施設一覧や災害公式ソースを取り込まない。任意の文字列を公式災害情報として解釈しない。
- `Mode.NORMAL`はライブ運用を保証しない。現状は実災害イベント・端末の実在位置・避難所開設状況・ルート計算を**提供しない**。
- データ構造は`frozen dataclass`で、遷移は引数から新しいオブジェクトを返す。ネットワークアクセス、clock読み取り、永続化は無し。呼び出し側が`now`を明示的に渡す。
- `synthetic fixture`の`source_authorization=SYNTHETIC_TEST_ONLY`は「正式な出典利用承認」ではなく、合成専用の内部定数。

## 2. 入力と操作

- `Session()`: 既定値はNORMAL・地域未選択・希望地域未設定・fixture未設定。
- `SyntheticFixture(fixture_id, region_code, hazard, observed_at, expires_at, source_authorization)`: 原本ではなく合成モードであることと期限を検査。地域コード5桁、単純な合成識別子のみ。
- `Event(action, expected_generation, region_code=None, fixture=None, explicit_consent=False)`: 状態変更イベント。actionは`START_DRILL / STOP_DRILL / SELECT_REGION / SOURCE_FAILED / SET_PREFERRED_REGION / CLEAR_PREFERRED_REGION / RESET`。
- `reduce_session(state, event, now)`: バージョンを確認してイベント実行。各操作で世代を更新。無効なDRILL開始は古いfixtureも残さずNORMALへ戻す。
- `safe_view(state, now)`: 期限内ならDRILLと模擬注意文、期限外ならNORMAL（模擬fixture/id/hazardを隠す）。常に`live_data_verified=False`。

### 実装利用の一例（合成fixture）

```python
from datetime import datetime, timedelta, timezone
from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY,
    reduce_session, safe_view,
)
now = datetime(2026, 11, 13, tzinfo=timezone.utc)
fixture = SyntheticFixture(
    fixture_id="synthetic:demo-001", region_code="13123", hazard="flood",
    observed_at=now, expires_at=now + timedelta(minutes=30),
    source_authorization=SYNTHETIC_ONLY,
)
state = Session()
state = reduce_session(state, Event(
    action=Action.START_DRILL, expected_generation=state.generation,
    region_code="13123", fixture=fixture,
), now)
assert safe_view(state, now).mode.value == "DRILL"
assert not safe_view(state, now).live_data_verified
```

## 3. 合成テストと判定

```bash
cd pipeline
python -m unittest discover -s tests -p "test_drill_session.py" -v
python -m unittest discover -s tests -v
python verify_d_mvp.py  # ローカルのD生成物がない場合はNOT_RUN (not green)
```

独立合成テストで、明示開始、未同意の事前設定拒否、再入力・削除、地域切替/同じ地域の選択、停止、模擬資料期限切れ/未来日付、取得失敗、旧世代の非同期応答、time zone欠落、LIVE誤認防止を検証。CI成功は実データ安全・iPhone/Android実機・一般公開の受入ではない。

## 4. 将来の接続判断（今回は実装しない）

- B/EのDRILLラベルとモード切替UI、F03の端末保存キー/同意/有効期限、F05の条件抽出に接続する前に共有状態の契約/ライフサイクルを双方で承認する。
- `Session`は暫定のPythonモデルであり、JavaScript側へコピーしたり、端末保存したり、LIVEデータを取り込む仕様を自動確定しない。
- 現時点の`source_authorization`は合成専用。公式Sourceの確認や利用条件（Issue #366）、施設同一性/安全（C）を代行しない。
- Issue #372の実装先行・定期実機QA運用に沿い、純粋Pythonモデルの実機QAは`NOT_REQUIRED`。将来のUI接続では新たに実機QAを起票する。
- 未承認元データの一般配信、模擬状態をLIVE/現在の開設状態と偽る表示は不可。
