"""Synthetic regression of numbered 2019 school operational groups and detail rows.

No synthetic row is an official school record. Real PDF SHA and independent
C verification are required in a separate hosted run.
"""
import hashlib
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "extract_edogawa_2019_school_roster.py"
spec = importlib.util.spec_from_file_location("school_roster", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def word(x, y, text):
    return (x, y - 5.5, x + 10, y + 5.5, text, 0, 0, 0)


def sample_words():
    words = []
    for n in range(1, 43):
        y = 112 + (n - 1) * 13.32
        words.extend([word(50 if n < 10 else 47.5, y, str(n)),
                      word(62, y, f"架空小学校{n}"),
                      word(176, y, "1"), word(208, y, "1"),
                      word(234, y, "1"), word(254, y, "100%")])
    for n in range(1, 22):
        if n == 2:
            y = 125.3
            words.extend([word(305, 131.96, "2"), word(316, y, "架空中学校2"),
                          word(431, y, "3"), word(468, y, "1"),
                          word(494, y, "1"), word(509, y, "100%"),
                          word(316, 138.6, "架空中学校2【夜間】"),
                          word(431, 138.6, "1"), word(468, 138.6, "1"),
                          word(494, 138.6, "1"), word(509, 138.6, "100%")])
            continue
        y = 112 if n == 1 else 151.95 + (n - 3) * 13.32
        words.extend([word(305 if n < 10 else 302, y, str(n)),
                      word(316, y, f"架空中学校{n}"), word(431, y, "1"),
                      word(468, y, "1"), word(494, y, "1"), word(509, y, "100%")])
    for n in range(1, 3):
        y = 458.15 + (n - 1) * 13.32
        words.extend([word(305, y, str(n)),word(316, y, f"旧架空小学校{n}"),
                      word(431, y, "1"),word(468, y, "1"),
                      word(494, y, "1"),word(509, y, "100%")])
    return words


class SchoolRosterExtractionTests(unittest.TestCase):
    def test_65_numbered_groups_66_detail_records(self):
        records = m.parse_detail_lines(sample_words())
        self.assertEqual([len(x) for x in records.values()], [42,22,2])
        self.assertEqual([r["source_group_number"] for r in records["junior_high"][:4]],
                         [1,2,2,3])
        self.assertEqual(records["junior_high"][2]["printed_name"],"架空中学校2【夜間】")
        self.assertTrue(all(r["facility_identity_review_state"] == "NOT_REVIEWED"
                            for values in records.values() for r in values))
        self.assertTrue(all(r["normalized_facility_id"] is None
                            for values in records.values() for r in values))

    def test_missing_night_detail_fails_closed(self):
        words = [w for w in sample_words()
                 if not (abs((w[1]+w[3])/2-138.6)<1 and w[0] >= 290)]
        with self.assertRaisesRegex(m.ExtractionError,"detail count"):
            m.parse_detail_lines(words)

    def test_duplicate_group_marker_fails_closed(self):
        words = sample_words()
        words.append(word(305, 151.95, "3"))
        with self.assertRaisesRegex(m.ExtractionError,"numbered operational units inconsistent"):
            m.parse_detail_lines(words)

    def test_missing_numbered_group_fails_closed(self):
        words = [w for w in sample_words() if not (w[4]=="21" and w[0]>=290)]
        with self.assertRaisesRegex(m.ExtractionError,"numbered operational units"):
            m.parse_detail_lines(words)

    def test_unreadable_value_rejected(self):
        words=sample_words()
        words=[word(w[0],(w[1]+w[3])/2,"-") if w[0]==431 and abs((w[1]+w[3])/2-112)<0.1
               else w for w in words]
        with self.assertRaisesRegex(m.ExtractionError,"malformed table numeral"):
            m.parse_detail_lines(words)

    def test_empty_and_wrong_sha_never_extract(self):
        with self.assertRaisesRegex(m.ExtractionError,"SHA256 changed"):
            m.extract_report(b"%PDF-1.4\nsynthetic")
        self.assertEqual(len(m.PINNED_PDF_SHA256),64)

    def test_only_post_event_truth_semantics_exposed(self):
        self.assertEqual(m.REPORT_PAGE_INDEX,2)
        self.assertEqual(m.EXPECTED_GROUPS,{"elementary":42,"junior_high":21,"other":2})
        self.assertEqual(sum(m.EXPECTED_EVACUEES.values()),26761)
        self.assertEqual(sum(m.EXPECTED_STAFF_PRESENT.values()),601)
        self.assertEqual(sum(m.EXPECTED_STAFF_ASSIGNED.values()),789)


if __name__ == "__main__":
    unittest.main()
