"""S1-P3 local what-if CLI: fixture-only execution and blocked lifecycle."""
import json
import unittest

from preview_s1_synthetic_what_if import preview, main


class S1WhatIfCliTests(unittest.TestCase):
    def test_default_fictional_example_is_stable(self):
        a = json.loads(preview())
        b = json.loads(preview())
        self.assertEqual(a, b)
        self.assertEqual(a["newly_matching_synthetic_ids"], ["synthetic:c", "synthetic:d"])
        self.assertEqual(a["no_longer_matching_synthetic_ids"], ["synthetic:b"])
        self.assertEqual(a["unknown_after_synthetic_ids"], ["synthetic:e"])

    def test_explicit_unknown_review_does_not_approve_it(self):
        out = json.loads(preview(select="synthetic:e"))
        self.assertEqual(out["review"]["comparison_status"], "UNKNOWN")
        self.assertEqual(out["review"]["missing"], ["step_free"])
        self.assertEqual(out["review"]["selected_record_id"], "synthetic:e")
        self.assertFalse(out["facility_safety_verified"])

    def test_expiry_and_stop_discard_all_previous_rows(self):
        for kwargs in ({"minutes": 30}, {"minutes": 5, "stop": True}):
            with self.subTest(kwargs=kwargs):
                out = json.loads(preview(select="synthetic:a", **kwargs))
                self.assertEqual(out["status"], "BLOCKED")
                self.assertEqual(out["rows"], [])
                self.assertIsNone(out["review"])
                self.assertEqual(out["newly_matching_synthetic_ids"], [])

    def test_changed_conditions_can_tighten_without_fake_safety(self):
        out = json.loads(preview(
            before=("pet_support",), after=("pet_support", "step_free"),
        ))
        self.assertEqual(out["no_longer_matching_synthetic_ids"], ["synthetic:b"])
        self.assertFalse(out["release_approved"])

    def test_invalid_input_rejected_not_silently_defaulted(self):
        with self.assertRaises(ValueError):
            preview(minutes=-1)
        with self.assertRaises(ValueError):
            preview(minutes=1441)
        with self.assertRaises(ValueError):
            preview(minutes=True)

    def test_main_option_parser_rejects_unsupported_condition(self):
        with self.assertRaises(SystemExit) as caught:
            main(["--after", "capacity"])
        self.assertEqual(caught.exception.code, 2)

    def test_main_rejects_unlisted_real_facility_id(self):
        with self.assertRaises(SystemExit) as caught:
            main(["--select", "facility:actual"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
