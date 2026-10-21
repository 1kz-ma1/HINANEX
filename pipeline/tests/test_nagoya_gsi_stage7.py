"""Synthetic-only Stage-7 tests, including exact historical replay invariants."""
import copy
import json
import unittest

from compare_nagoya_gsi_offline import PRIVATE_COMPARISON_FIELDS, compare
from create_nagoya_independent_review_queue import safe_csv_cell
from test_nagoya_gsi_stage6 import fixtures as base_fixtures
from triage_nagoya_gsi_stage6 import EXTRA, triage
from refine_nagoya_gsi_stage7 import (
    NEAR_COINCIDENT_METERS, RANKS, STATES, near_coincident_strict_references,
    parse_renovation_notice, refine,
)


def historical_fixture(near=True, recognizable=True):
    queue, queue_summary, _, _, gsi, provenance = base_fixtures()
    # Two official GSI categories whose longitude float differs by a
    # microscopic amount. Old Stage 5 MUST still register raw conflict.
    gsi = copy.deepcopy(gsi)
    if near:
        gsi[1]["point"] = (136.900000000001, 35.1)
    if recognizable:
        queue[1]["facility_name"] = (
            "別名B学園※R8.7.11～R9.3.31までリニューアル改修工事のため、使用不可"
        )
    details, stage5_agg = compare(queue, queue_summary, gsi, provenance)
    stage5_rows = [
        {k: safe_csv_cell(row.get(k)) for k in PRIVATE_COMPARISON_FIELDS}
        for row in details
    ]
    stage6_rows, stage6_agg = triage(
        queue, queue_summary, stage5_rows, stage5_agg, gsi, provenance
    )
    fields = (*PRIVATE_COMPARISON_FIELDS, *EXTRA)
    stage6_private = [
        {k: safe_csv_cell(row.get(k, "")) for k in fields}
        for row in stage6_rows
    ]
    return (queue, queue_summary, stage5_rows, stage5_agg, stage6_private,
            stage6_agg, gsi, provenance)


class Stage7Tests(unittest.TestCase):
    def test_micro_point_delta_does_not_erase_original_conflict(self):
        args = historical_fixture()
        self.assertEqual(args[3]["status_counts"][
            "strict_name_address_conflicting_references"], 1)
        self.assertTrue(near_coincident_strict_references(args[4][0], args[6])
                        if args[4][0]["gsi_cross_reference_status"] ==
                        "strict_name_address_conflicting_references"
                        else near_coincident_strict_references(
                            next(row for row in args[4] if row["gsi_cross_reference_status"]
                                 == "strict_name_address_conflicting_references"), args[6]
                        ))
        rows, agg = refine(*args)
        self.assertEqual(agg["near_coincident_distinct_gsi_reference_cases"], 1)
        self.assertEqual(agg["refined_classifications"][
            "gsi_distinct_references_under_1mm"], 1)
        self.assertEqual(agg["refined_classifications"][
            "source_renovation_notice_name_correspondence"], 1)
        self.assertEqual(agg["refined_priority_counts"][RANKS[0]], 1)
        self.assertEqual(agg["refined_priority_counts"][RANKS[1]], 3)
        self.assertEqual(agg["refined_priority_counts"][RANKS[2]], 2)
        self.assertEqual(agg["historical_stage6_priority_counts"],
                         args[5]["priority_counts"])
        self.assertEqual(agg["review_rows_total"], 6)
        self.assertEqual(agg["near_coincident_threshold_m"], NEAR_COINCIDENT_METERS)
        self.assertFalse(agg["approved_for_map"])
        self.assertFalse(agg["data_promotion_authorized"])
        self.assertEqual(agg["official_facility_positions_accepted"], 0)
        self.assertTrue(agg["source_end_date_does_not_auto_reopen"])
        self.assertEqual({r["stage7_review_status"] for r in rows}, {"NOT_REVIEWED"})
        self.assertEqual({r["independent_site_position_approved"] for r in rows},
                         {"NO"})
        output = json.dumps(agg, ensure_ascii=False)
        for forbidden in ("架空", "別名B", "工事", "136.9", "35.1",
                          '"facility_name":', '"abr_reference_longitude":',
                          '"pilot_record_id":'):
            self.assertNotIn(forbidden, output)

    def test_renovation_dates_and_original_source_notice_are_preserved(self):
        rows, _ = refine(*historical_fixture())
        matched = next(r for r in rows if
                       r["stage7_classification"] ==
                       "source_renovation_notice_name_correspondence")
        self.assertEqual(matched["source_base_facility_name_PRIVATE"], "別名B学園")
        self.assertEqual(matched["source_renovation_start"], "2026-07-11")
        self.assertEqual(matched["source_renovation_end"], "2027-03-31")
        self.assertIn("使用不可", matched["source_notice_verbatim_PRIVATE"])
        self.assertEqual(matched["facility_use_status_verified"], "NO")
        self.assertEqual(matched["facility_reopening_verified"], "NO")
        self.assertEqual(matched["stage7_priority"], RANKS[0])

    def test_notices_are_parsed_only_when_full_pattern_matches(self):
        self.assertIsNotNone(parse_renovation_notice(
            "架空施設※R8.7.11～R9.3.31まで改修工事のため、使用不可"))
        for s in (
            "架空施設※R8.7.11～R9.3.31まで改修工事のため、使用可能",
            "架空施設※R8.2.30～R9.3.31まで改修工事のため、使用不可",
            "架空施設※R9.7.11～R8.3.31まで改修工事のため、使用不可",
            "架空施設※工事中",
            "架空施設※R8.7.11～R9.3.31まで改修工事のため、使用不可・追加",
            "架空施設※R8.7.11～R9.3.31まで検討のため、使用不可",
        ):
            with self.subTest(s=s):
                self.assertIsNone(parse_renovation_notice(s))

    def test_actual_large_point_divergence_keeps_p0(self):
        rows, agg = refine(*historical_fixture(near=False))
        self.assertEqual(agg["near_coincident_distinct_gsi_reference_cases"], 0)
        self.assertEqual(agg["refined_priority_counts"][RANKS[0]], 2)
        self.assertEqual(agg["refined_classifications"][
            "unchanged_unresolved_identity_or_gsi_conflict"], 1)

    def test_unrelated_annotation_not_normalized(self):
        rows, agg = refine(*historical_fixture(recognizable=False))
        self.assertEqual(agg["recognized_source_renovation_notice_name_matches"], 0)
        self.assertEqual(agg["refined_priority_counts"][RANKS[0]], 1)
        self.assertTrue(any(r["stage7_classification"] ==
                            "unchanged_unresolved_identity_or_gsi_conflict"
                            for r in rows))

    def test_stage6_private_and_aggregate_changes_abort(self):
        queue, qs, stage5, agg5, stage6, agg6, gsi, prov = historical_fixture()
        bad6 = copy.deepcopy(stage6)
        bad6[0]["review_status"] = "APPROVED"
        with self.assertRaises(ValueError):
            refine(queue, qs, stage5, agg5, bad6, agg6, gsi, prov)
        bad_aggregate = dict(agg6, approved_for_map=True)
        with self.assertRaises(ValueError):
            refine(queue, qs, stage5, agg5, stage6, bad_aggregate, gsi, prov)
        bad_provenance = copy.deepcopy(prov)
        bad_provenance["shelter"]["sha256"] = "changed"
        with self.assertRaises(ValueError):
            refine(queue, qs, stage5, agg5, stage6, agg6, gsi, bad_provenance)


if __name__ == "__main__":
    unittest.main()
