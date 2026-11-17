"""D synthetic local interactive practice: real S1-P4 behavior, no real shelters."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import timedelta
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from preview_s1_synthetic_practice import (
    COMMANDS, DEMO, MAX_INTERACTIONS, NOTICE, SyntheticPractice, main,
    run_practice,
)
from preview_s1_synthetic_what_if import T0
from src.hinanex.drill_session import Mode
from src.hinanex.s1_synthetic_walkthrough import project_walkthrough


def practice():
    stream = StringIO()
    return SyntheticPractice(stream), stream


def projection(app):
    return project_walkthrough(app.state, app.records, app.now)


class S1SyntheticPracticeTests(unittest.TestCase):
    def test_initial_state_does_not_claim_live_data(self):
        app, out = practice()
        self.assertEqual(app.state.session.mode, Mode.NORMAL)
        self.assertIsNone(projection(app).result)
        app.handle("show")
        self.assertIn("未開始・停止・期限切れ", out.getvalue())
        self.assertIn(NOTICE, out.getvalue())

    def test_start_shows_all_five_invented_records_with_unknown(self):
        app, out = practice()
        self.assertTrue(app.handle("start"))
        self.assertEqual((app.state.session.generation, app.state.revision), (1, 1))
        self.assertEqual(app.state.conditions, ("pet_support",))
        rows = projection(app).result.rows
        self.assertEqual(len(rows), 5)
        self.assertEqual(
            [r.status for r in rows],
            ["MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC",
             "NOT_MATCHED_SYNTHETIC", "UNKNOWN",
             "NOT_MATCHED_SYNTHETIC"],
        )
        for label in ("架空a", "架空b", "架空c", "架空d", "架空e"):
            self.assertIn(label, out.getvalue())

    def test_step_change_displays_diffs_and_clears_old_choice(self):
        app, out = practice()
        app.handle("start")
        app.handle("select a")
        self.assertEqual(app.state.selected_record_id, "synthetic:a")
        app.handle("step")
        self.assertIsNone(app.state.selected_record_id)
        self.assertEqual(app.state.previous_conditions, ("pet_support",))
        self.assertEqual(app.state.conditions, ("step_free",))
        p = projection(app).result
        self.assertEqual(p.newly_matching_synthetic_ids, ("synthetic:c", "synthetic:d"))
        self.assertEqual(p.no_longer_matching_synthetic_ids, ("synthetic:b",))
        self.assertIn("synthetic:c, synthetic:d", out.getvalue())
        self.assertIn("レビュー対象: 未選択", out.getvalue())

    def test_unknown_review_can_be_inspected_but_not_promoted(self):
        app, out = practice()
        for line in ("start", "step", "select e"):
            app.handle(line)
        result = projection(app).result
        self.assertEqual(result.review.comparison_status, "UNKNOWN")
        self.assertEqual(result.review.missing, ("step_free",))
        self.assertFalse(result.review.facility_safety_verified)
        self.assertIn("未確認（UNKNOWN）", out.getvalue())
        self.assertIn("未確認条件: step_free", out.getvalue())
        self.assertIn(NOTICE, out.getvalue())

    def test_both_conditions_clears_review_and_retains_unknown(self):
        app, _ = practice()
        for line in ("start", "step", "select e", "both"):
            app.handle(line)
        self.assertIsNone(app.state.selected_record_id)
        p = projection(app).result
        self.assertIsNone(p.review)
        self.assertEqual(p.after_conditions, ("pet_support", "step_free"))
        self.assertEqual([r.status for r in p.rows], [
            "MATCHED_SYNTHETIC", "NOT_MATCHED_SYNTHETIC",
            "NOT_MATCHED_SYNTHETIC", "UNKNOWN", "UNKNOWN",
        ])

    def test_clear_review_preserves_filter_and_version(self):
        app, _ = practice()
        for line in ("start", "select a", "clear"):
            app.handle(line)
        self.assertEqual(app.state.conditions, ("pet_support",))
        self.assertIsNone(app.state.selected_record_id)
        self.assertEqual(app.state.revision, 3)
        self.assertIsNone(projection(app).result.review)

    def test_stop_blocks_all_rows_and_clears_selection(self):
        app, out = practice()
        for line in ("start", "select a", "stop"):
            app.handle(line)
        self.assertEqual(app.state.session.mode, Mode.NORMAL)
        self.assertEqual(app.state.conditions, ())
        self.assertEqual(app.state.previous_conditions, ())
        self.assertIsNone(app.state.selected_record_id)
        self.assertIsNone(projection(app).result)
        self.assertIn("訓練データは非表示", out.getvalue())

    def test_stop_restart_does_not_restore_old_selection(self):
        app, _ = practice()
        for line in ("start", "step", "select e", "stop", "start"):
            app.handle(line)
        self.assertEqual(app.state.session.mode, Mode.DRILL)
        self.assertEqual(app.state.session.generation, 3)
        self.assertEqual(app.state.conditions, ("pet_support",))
        self.assertIsNone(app.state.selected_record_id)
        self.assertIsNone(projection(app).result.review)

    def test_start_during_drill_does_not_overwrite_selection(self):
        app, out = practice()
        for line in ("start", "select a"):
            app.handle(line)
        old = app.state
        app.handle("start")
        self.assertIs(app.state, old)
        self.assertIn("現在の訓練を終了してから", out.getvalue())

    def test_advance_to_expiry_hides_all_facts_before_next_command(self):
        app, out = practice()
        for line in ("start", "step", "select e", "advance 25"):
            app.handle(line)
        self.assertEqual(app.now, T0+timedelta(minutes=30))
        self.assertIsNone(projection(app).result)
        self.assertIn("期限切れ", out.getvalue())
        app.handle("show")
        self.assertTrue(out.getvalue().endswith(NOTICE + "\n"))

    def test_action_after_expiry_invalidates_generation_and_selection(self):
        app, out = practice()
        for line in ("start", "step", "select e", "advance 25"):
            app.handle(line)
        old_generation = app.state.session.generation
        app.handle("pet")
        self.assertEqual(app.state.session.generation, old_generation + 1)
        self.assertEqual(app.state.session.mode, Mode.NORMAL)
        self.assertIsNone(app.state.selected_record_id)
        self.assertIsNone(projection(app).result)
        self.assertIn("STALE_WALKTHROUGH_ACTION", out.getvalue())

    def test_cannot_start_old_fixture_after_expiration(self):
        app, out = practice()
        for line in ("advance 25", "start"):
            app.handle(line)
        self.assertEqual(app.state.session.mode, Mode.NORMAL)
        self.assertEqual(app.state.conditions, ())
        self.assertIsNone(projection(app).result)
        self.assertIn("DRILL_INPUT_INVALID_OR_EXPIRED", out.getvalue())

    def test_unknown_or_compound_select_argument_rejected(self):
        app, out = practice()
        app.handle("start")
        before = app.state
        for line in ("select ab", "select real:facility", "select f", "select",
                     "SELECT AE", "teleport", "select a b"):
            app.handle(line)
        self.assertIs(app.state, before)
        self.assertIn("未対応の操作", out.getvalue())

    def test_change_before_start_does_not_create_drill(self):
        app, out = practice()
        app.handle("step")
        self.assertEqual(app.state.session.mode, Mode.NORMAL)
        self.assertIsNone(projection(app).result)
        self.assertIn("ACTIVE_SYNTHETIC_DRILL_REQUIRED", out.getvalue())

    def test_reject_invalid_advance_without_time_change(self):
        app, out = practice()
        before = app.now
        for line in ("advance 0", "advance -1", "advance xyz",
                     "advance 61", "advance 1.5"):
            app.handle(line)
            self.assertEqual(app.now, before)
        self.assertEqual(out.getvalue().count("advanceは1～60分"), 5)

    def test_finite_virtual_clock_cannot_be_rolled_back(self):
        app, out = practice()
        app.handle("advance 60")
        self.assertEqual(app.now, T0+timedelta(minutes=65))
        app.handle("advance 1")
        self.assertEqual(app.now, T0+timedelta(minutes=65))
        self.assertIn("仮想時刻の合計は65分", out.getvalue())

    def test_input_whitespace_and_case_are_normalized(self):
        app, out = practice()
        app.handle("  START ")
        app.handle("  SELECT   A ")
        self.assertEqual(app.state.selected_record_id, "synthetic:a")
        app.handle(" STOP ")
        self.assertEqual(app.state.session.mode, Mode.NORMAL)
        self.assertNotIn("未対応の操作", out.getvalue())

    def test_empty_and_help_commands_do_not_change_state(self):
        app, out = practice()
        old = app.state
        app.handle("")
        app.handle("help")
        self.assertIs(app.state, old)
        self.assertIn(COMMANDS, out.getvalue())
        self.assertIn(NOTICE, out.getvalue())

    def test_quit_is_final_and_no_follow_up_state_change(self):
        app, out = practice()
        app.handle("start")
        before = app.state
        self.assertFalse(app.handle("quit"))
        self.assertFalse(app.handle("step"))
        self.assertIs(app.state, before)
        self.assertIn("保存は行いません", out.getvalue())

    def test_command_limit_is_bounded_and_cleanly_exits(self):
        app, out = practice()
        for _ in range(MAX_INTERACTIONS):
            self.assertTrue(app.handle("help"))
        self.assertFalse(app.handle("start"))
        self.assertTrue(app.closed)
        self.assertEqual(app.state.session.mode, Mode.NORMAL)
        self.assertIn("操作上限", out.getvalue())

    def test_input_loop_handles_eof_without_saving_state(self):
        out = StringIO()
        it = iter(["start", "step", "show"])
        self.assertEqual(run_practice(lambda: next(it), out), 0)
        self.assertIn("入力を終了しました。状態は保存されません", out.getvalue())
        self.assertIn("synthetic:c", out.getvalue())

    def test_demo_is_reproducible_and_live_claims_absent(self):
        def execute():
            out = StringIO()
            it = iter(DEMO)
            self.assertEqual(run_practice(lambda: next(it), out), 0)
            return out.getvalue()
        self.assertEqual(execute(), execute())
        text = execute()
        self.assertIn("UNKNOWN", text)
        self.assertIn("訓練データは非表示", text)
        self.assertIn("現実の災害", text)
        for forbidden in ("緯度", "経度", "安全な避難先が決まりました",
                          "開設中です", "公式指定済み"):
            self.assertNotIn(forbidden, text)

    def test_cli_demo_runs_without_input_prompt(self):
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--demo"]), 0)
        self.assertIn("仮想時刻: +5分", out.getvalue())
        self.assertIn("合成訓練専用", out.getvalue())

    def test_no_files_written_by_local_demo(self):
        # No cwd-dependent writes are possible; a sentinel is preserved.
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder)/"sentinel.txt"
            sentinel.write_text("untouched", encoding="utf-8")
            out = StringIO()
            it = iter(DEMO)
            self.assertEqual(run_practice(lambda: next(it), out), 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "untouched")
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["sentinel.txt"])


if __name__ == "__main__":
    unittest.main()
