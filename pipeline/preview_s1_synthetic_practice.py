"""D-only interactive synthetic S1 walkthrough practice on the local terminal.

Uses only the existing S0/S1-P4 reducer and five hardcoded fictional records.
Not a public B UI, shared D->B contract, hazard feed or real shelter advice.
No networking, persistence, background work or personal inputs are retained.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
import sys
from typing import Callable, TextIO

from preview_s1_synthetic_what_if import T0, sample_state
from src.hinanex.drill_session import Mode
from src.hinanex.s1_synthetic_walkthrough import (
    IntentKind, WalkthroughIntent, WalkthroughState,
    apply_walkthrough_intent, project_walkthrough,
)

NOTICE = "【合成訓練専用】現実の災害・避難施設の安全性や開設状況を示しません。"
COMMANDS = (
    "start: 訓練開始 / show: 架空レコード一覧 / pet: ペット条件 / "
    "step: 段差条件 / both: 両条件 / select a～e: 内容確認 / "
    "clear: 選択解除 / stop: 訓練終了 / advance 1～60: 仮想時間を進める / "
    "help: 操作説明 / quit: 終了"
)
ROW_LABEL = {
    "MATCHED_SYNTHETIC": "合成条件に一致（安全性は未確認）",
    "NOT_MATCHED_SYNTHETIC": "合成条件には不一致",
    "UNKNOWN": "未確認（UNKNOWN）",
}
MAX_INTERACTIONS = 100


class SyntheticPractice:
    def __init__(self, stream: TextIO):
        self.stream = stream
        initial, self.records = sample_state()
        self.fixture = initial.fixture
        self.now = T0 + timedelta(minutes=5)
        self.state = WalkthroughState()
        self.actions_processed = 0
        self.closed = False

    def say(self, message: str) -> None:
        print(message, file=self.stream)

    def _intent(self, kind: IntentKind, *, explicit=False, conditions=(),
                selected=None):
        return WalkthroughIntent(
            kind, self.state.session.generation, self.state.revision,
            explicit_user_action=explicit, conditions=conditions,
            selected_record_id=selected,
            region_code=self.fixture.region_code if kind == IntentKind.START else None,
            fixture=self.fixture if kind == IntentKind.START else None,
        )

    def _apply(self, kind: IntentKind, *, explicit=False, conditions=(),
               selected=None) -> None:
        command = self._intent(kind, explicit=explicit,
                               conditions=conditions, selected=selected)
        transition = apply_walkthrough_intent(
            self.state, command, self.records, self.now,
        )
        self.state = transition.state
        if transition.status == "BLOCKED":
            self.say(f"操作拒否: {transition.reason_code}（古い選択・結果は使用しません）")
        else:
            self.say(f"操作受付: {transition.reason_code}")
        self.show_summary()

    def show_summary(self) -> None:
        projected = project_walkthrough(self.state, self.records, self.now)
        self.say(f"仮想時刻: +{int((self.now-T0).total_seconds()//60)}分 / "
                 f"世代 {projected.generation} / 操作版 {projected.revision}")
        if projected.status != "EVALUATED_SYNTHETIC_ONLY" or projected.result is None:
            self.say("訓練データは非表示です（未開始・停止・期限切れ）。")
            self.say(NOTICE)
            return
        result = projected.result
        self.say("条件: " + ", ".join(result.after_conditions))
        for row in result.rows:
            # These are invented stable IDs, not physical facility names.
            short_id = row.record_id.rsplit(":", 1)[-1]
            self.say(f"  架空{short_id}: {ROW_LABEL[row.after_status]}")
        self.say(f"条件変更による架空一致の追加: "
                 f"{', '.join(result.newly_matching_synthetic_ids) or 'なし'}")
        self.say(f"条件変更による架空一致の解除: "
                 f"{', '.join(result.no_longer_matching_synthetic_ids) or 'なし'}")
        if result.review is not None:
            review = result.review
            self.say(f"レビュー対象: {review.selected_record_id} / "
                     f"{ROW_LABEL[review.comparison_status]} / "
                     f"未確認条件: {', '.join(review.missing) or 'なし'} / "
                     f"不一致条件: {', '.join(review.failed) or 'なし'}")
        else:
            self.say("レビュー対象: 未選択")
        self.say(NOTICE)

    def handle(self, raw: str) -> bool:
        """One operator command; false means a requested exit."""
        if self.closed:
            return False
        if not isinstance(raw, str):
            raise TypeError("command must be text")
        if self.actions_processed >= MAX_INTERACTIONS:
            self.say("操作上限に到達しました。今回の訓練を終了します。")
            self.closed = True
            return False
        self.actions_processed += 1
        fields = raw.strip().lower().split()
        if not fields:
            self.say("操作を入力してください。helpで一覧を確認できます。")
            return True
        if fields == ["quit"]:
            self.say("ローカル合成訓練を終了しました。保存は行いません。")
            self.closed = True
            return False
        if fields == ["help"]:
            self.say(COMMANDS)
            self.say(NOTICE)
            return True
        if fields == ["show"]:
            self.show_summary()
            return True
        if fields == ["start"]:
            if self.state.session.mode == Mode.DRILL:
                self.say("現在の訓練を終了してから、新しく開始してください。")
                self.show_summary()
                return True
            self._apply(IntentKind.START, explicit=True, conditions=("pet_support",))
            return True
        if fields in (["pet"], ["step"], ["both"]):
            values = {
                "pet": ("pet_support",),
                "step": ("step_free",),
                "both": ("pet_support", "step_free"),
            }
            self._apply(IntentKind.SET_CONDITIONS, explicit=True,
                        conditions=values[fields[0]])
            return True
        if len(fields) == 2 and fields[0] == "select" and fields[1] in ("a", "b", "c", "d", "e"):
            self._apply(IntentKind.REVIEW, explicit=True,
                        selected=f"synthetic:{fields[1]}")
            return True
        if fields == ["clear"]:
            self._apply(IntentKind.CLEAR_REVIEW)
            return True
        if fields == ["stop"]:
            self._apply(IntentKind.STOP)
            return True
        if len(fields) == 2 and fields[0] == "advance":
            try:
                minutes = int(fields[1])
            except ValueError:
                minutes = -1
            if (not 1 <= minutes <= 60 or
                    (self.now-T0).total_seconds()/60 + minutes > 65):
                self.say("advanceは1～60分、仮想時刻の合計は65分までです。")
                return True
            self.now += timedelta(minutes=minutes)
            self.say(f"仮想時刻を{minutes}分進めました。実時刻・災害情報は参照しません。")
            self.show_summary()
            return True
        self.say("未対応の操作です。helpで一覧を確認してください。")
        return True


def run_practice(input_fn: Callable[[], str], stream: TextIO) -> int:
    """Terminal input only. Ends on quit, EOF or the bounded command limit."""
    app = SyntheticPractice(stream)
    app.say(NOTICE)
    app.say(COMMANDS)
    while not app.closed:
        try:
            line = input_fn()
        except (EOFError, StopIteration):
            app.say("入力を終了しました。状態は保存されません。")
            break
        if not app.handle(line):
            break
    return 0


DEMO = (
    "start", "show", "step", "select e", "both", "show",
    "stop", "show", "quit",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline terminal practice of fictional S0/S1-P4 operations only",
    )
    parser.add_argument("--demo", action="store_true",
                        help="run the fixed, fictional, noninteractive demonstration")
    args = parser.parse_args(argv)
    if args.demo:
        commands = iter(DEMO)
        return run_practice(lambda: next(commands), sys.stdout)
    return run_practice(lambda: input("hinanex-synthetic> "), sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
