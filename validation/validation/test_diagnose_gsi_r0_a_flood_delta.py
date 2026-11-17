"""Synthetic-only A-flood replay delta investigation; all HTTPS is mocked."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from diagnose_gsi_r0_a_flood_delta import (
    A_FLOOD_SOURCE, CBlocked, _diff_summary, diagnose_a_flood,
)
from test_verify_gsi_r0_four_cell_replay import (
    NOW, TILES, raw_for, cell, receipt_for, r0_report,
)

PRIOR_C_HASH = "1a18246c95386b24bada1a063b1cf8e51f8f1fe7b7f546de6032adc3e589cc35"


class TestAFloodMismatchDiagnostic(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hinanex-c-a-flood-delta-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        rows = []
        self.raws = {}
        for slot in ("A", "B"):
            for hazard in ("flood", "landslide"):
                raw = raw_for(hazard, TILES[slot])
                record = cell(slot, hazard, raw=raw)
                tile = TILES[slot]
                path = self.folder / (
                    f"r0-{slot}-{hazard}-10-{tile['x']}-{tile['y']}.geojson"
                )
                path.write_bytes(raw)
                path.with_suffix(".receipt.json").write_text(
                    json.dumps(receipt_for(record, raw)), encoding="utf-8",
                )
                rows.append(record)
                self.raws[record["source_url"]] = raw
                if slot == "A" and hazard == "flood":
                    self.a_raw_path = path
                    self.a_receipt_path = path.with_suffix(".receipt.json")
        self.report = r0_report(rows)
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        self.assertEqual(url, A_FLOOD_SOURCE)
        return self.raws[url], 200, url

    def check(self, *, report=None, transport=None, clock=lambda: NOW,
              prior=PRIOR_C_HASH, evidence_dir=None):
        return diagnose_a_flood(
            self.report if report is None else report,
            evidence_dir=self.folder if evidence_dir is None else evidence_dir,
            transport=self.fetch if transport is None else transport,
            clock=clock,
            prior_c_sha256=prior,
        )

    def test_same_bytes_currently_is_not_retroactive_approval(self):
        outcome = self.check()
        self.assertEqual(outcome["status"], "C_A_FLOOD_CURRENT_BYTE_MATCH_UNAPPROVED")
        self.assertEqual(outcome["checked_at_utc"], NOW.isoformat(timespec="seconds"))
        self.assertEqual(outcome["source_url"], A_FLOOD_SOURCE)
        self.assertEqual(outcome["tile"], TILES["A"])
        self.assertEqual(outcome["d_archived_tile_feature_count"], 1)
        self.assertEqual(outcome["c_new_https_tile_feature_count"], 1)
        self.assertTrue(outcome["same_bytes"])
        self.assertTrue(outcome["parsed_json_typed_equal"])
        self.assertFalse(outcome["current_c_equals_previous_c_sha256"])
        self.assertFalse(outcome["publication_approved"])
        self.assertFalse(outcome["c_independent_approved"])
        self.assertEqual(outcome["cause_of_prior_mismatch"], "UNDETERMINED")
        self.assertEqual(self.calls, [A_FLOOD_SOURCE])

    def test_report_has_no_name_coordinates_or_raw_features(self):
        result = self.check()
        forbidden = ("features", "coordinates", "address", "site_name",
                     "name_raw", "source_feature_ref", "raw_bytes_b64")
        for word in forbidden:
            with self.subTest(word=word):
                self.assertNotIn(word, result)
        self.assertEqual(result["first_differing_feature_index"], None)
        self.assertEqual(result["feature_indices_differing_count"], 0)

    def test_reformatted_json_changes_bytes_but_not_typed_values(self):
        data = json.loads(self.raws[A_FLOOD_SOURCE])
        altered = json.dumps(data, indent=2, ensure_ascii=False).encode()
        self.assertNotEqual(altered, self.raws[A_FLOOD_SOURCE])
        out = self.check(transport=lambda url: (altered, 200, url))
        self.assertEqual(out["status"], "C_A_FLOOD_CURRENT_BYTE_MISMATCH_HOLD")
        self.assertFalse(out["same_bytes"])
        self.assertTrue(out["parsed_json_typed_equal"])
        self.assertFalse(out["non_feature_root_changed"])
        self.assertEqual(out["feature_indices_differing_count"], 0)
        self.assertIsNone(out["first_differing_feature_index"])
        self.assertFalse(out["publication_approved"])

    def test_changed_synthetic_feature_is_not_assumed_official_revision(self):
        raw = raw_for("flood", TILES["A"], label="CHANGED SYNTHETIC ROW")
        out = self.check(transport=lambda url: (raw, 200, url))
        self.assertEqual(out["status"], "C_A_FLOOD_CURRENT_BYTE_MISMATCH_HOLD")
        self.assertFalse(out["parsed_json_typed_equal"])
        self.assertEqual(out["feature_indices_differing_count"], 1)
        self.assertEqual(out["first_differing_feature_index"], 0)
        self.assertEqual(out["feature_count_delta_c_minus_d"], 0)
        self.assertEqual(out["cause_of_prior_mismatch"], "UNDETERMINED")

    def test_feature_count_change_is_reported_without_rows(self):
        payload = json.loads(self.raws[A_FLOOD_SOURCE])
        payload["features"].append(payload["features"][0])
        raw = json.dumps(payload).encode()
        out = self.check(transport=lambda url: (raw, 200, url))
        self.assertEqual(out["d_archived_tile_feature_count"], 1)
        self.assertEqual(out["c_new_https_tile_feature_count"], 2)
        self.assertEqual(out["feature_count_delta_c_minus_d"], 1)
        self.assertEqual(out["first_differing_feature_index"], 1)
        self.assertEqual(out["feature_indices_differing_count"], 1)
        self.assertNotIn("features", out)

    def test_non_feature_metadata_difference_only(self):
        payload = json.loads(self.raws[A_FLOOD_SOURCE])
        payload["synthetic_metadata"] = "CHANGED"
        raw = json.dumps(payload).encode()
        out = self.check(transport=lambda url: (raw, 200, url))
        self.assertTrue(out["non_feature_root_changed"])
        self.assertEqual(out["feature_indices_differing_count"], 0)
        self.assertIsNone(out["first_differing_feature_index"])

    def test_digest_comparison_with_prior_c_hash_is_only_hint(self):
        out = self.check(prior=sha256(self.raws[A_FLOOD_SOURCE]).hexdigest())
        self.assertTrue(out["current_c_equals_previous_c_sha256"])
        self.assertFalse(out["official_source_signed"])
        self.assertEqual(out["cause_of_prior_mismatch"], "UNDETERMINED")

    def test_prior_sha_invalid_rejected_before_http(self):
        for invalid in ("ABC", "A"*64, "0"*63, "", 3):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(
                CBlocked, "PRIOR_SHA256"
            ):
                self.check(prior=invalid)
        self.assertEqual(self.calls, [])

    def test_false_http_200_or_redirect_does_not_inspect_response(self):
        for code, url in (
            (404, A_FLOOD_SOURCE), (201, A_FLOOD_SOURCE),
            (True, A_FLOOD_SOURCE),
            (200, "https://different.invalid/other.geojson"),
        ):
            with self.subTest(code=code,url=url), self.assertRaises(CBlocked):
                self.check(transport=lambda ignored: (b"{}", code, url))

    def test_corrupt_json_and_wrong_hazard_marker_rejected(self):
        wrong = raw_for("landslide", TILES["A"])
        for raw in (b"", b"<html>not found</html>", wrong):
            with self.subTest(raw=raw), self.assertRaises(CBlocked):
                self.check(transport=lambda url: (raw, 200, url))

    def test_spatially_outside_tile_is_rejected(self):
        other = raw_for("flood", TILES["B"])
        with self.assertRaisesRegex(CBlocked, "POINT_OUTSIDE"):
            self.check(transport=lambda url: (other, 200, url))

    def test_modified_d_raw_rejected_before_http(self):
        self.a_raw_path.write_bytes(b"replaced raw")
        with self.assertRaises(CBlocked):
            self.check()
        self.assertEqual(self.calls, [])

    def test_modified_d_receipt_rejected_before_http(self):
        record = json.loads(self.a_receipt_path.read_text())
        record["publication_approval"] = "GRANTED"
        self.a_receipt_path.write_text(json.dumps(record))
        with self.assertRaisesRegex(CBlocked, "D_RECEIPT_MISMATCH"):
            self.check()
        self.assertEqual(self.calls, [])

    def test_source_mismatch_in_matrix_rejected_before_http(self):
        self.report["cells"][0]["source_url"] = (
            "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
        )
        with self.assertRaises(CBlocked):
            self.check()
        self.assertEqual(self.calls, [])

    def test_wrong_slot_a_tile_rejected(self):
        for row in self.report["cells"]:
            if row["slot"] == "A":
                row["tile"] = TILES["B"].copy()
                row["source_url"] = row["source_url"].replace("/909/403", "/910/404")
        with self.assertRaises(CBlocked):
            self.check()
        self.assertEqual(self.calls, [])

    def test_naive_clock_does_not_allow_network(self):
        with self.assertRaisesRegex(CBlocked, "CHECK_CLOCK"):
            self.check(clock=lambda: datetime(2026, 11, 16, 4, 52, 27))
        self.assertEqual(self.calls, [])

    def test_evidence_directory_must_be_absolute(self):
        with self.assertRaisesRegex(CBlocked, "EVIDENCE_DIR"):
            self.check(evidence_dir=Path("relative"))
        self.assertEqual(self.calls, [])

    def test_original_d_source_unchanged_by_diagnostic(self):
        before = self.a_raw_path.read_bytes()
        before_receipt = self.a_receipt_path.read_bytes()
        self.check(transport=lambda url: (raw_for("flood",TILES["A"],
                                                  label="DIFF"),200,url))
        self.assertEqual(self.a_raw_path.read_bytes(), before)
        self.assertEqual(self.a_receipt_path.read_bytes(), before_receipt)

    def test_typed_equality_distinguishes_boolean_and_int(self):
        a = b'{"type":"FeatureCollection","features":[],"a":true}'
        b = b'{"type":"FeatureCollection","features":[],"a":1}'
        self.assertFalse(_diff_summary(a, b)["parsed_json_typed_equal"])

    def test_structural_difference_not_assumed_to_identify_facility(self):
        out = self.check(transport=lambda url: (
            raw_for("flood", TILES["A"], label="SYNTHETIC DIFFERENT"),
            200, url))
        self.assertEqual(out["comparison_scope"],
                         "SAME_FEATURE_ARRAY_INDEX_NO_IDENTITY_JOIN")
        self.assertFalse(out["facility_identity_approved"])
        self.assertFalse(out["hazard_safety_verified"])
        self.assertEqual(out["human_review"],"DEFERRED_TO_HUMAN_BATCH_REVIEW")


    def test_changed_name_category_only_never_returns_name_value(self):
        raw = raw_for("flood", TILES["A"], label="PRIVATE_NAME_EXAMPLE_9832")
        result = self.check(transport=lambda url: (raw, 200, url))
        self.assertEqual(result["changed_attribute_category_counts"],
                         {"properties.name": 1})
        self.assertEqual(result["feature_indices_differing_count"], 1)
        self.assertNotIn("PRIVATE_NAME_EXAMPLE_9832", json.dumps(result))
        self.assertEqual(result["changed_attribute_category_scope"],
                         "FIXED_ALLOWLIST_PER_ARRAY_INDEX_UNKNOWN_KEYS_REDACTED")

    def test_multiple_allowlisted_properties_report_once_each_per_index(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        props = source["features"][0]["properties"]
        props["name"] = "PRIVATE_TEST_NAME_111"
        props["address"] = "PRIVATE_ADDRESS_EXAMPLE_333"
        props["remarks"] = "PRIVATE_REMARKS_EXAMPLE_777"
        new_raw = json.dumps(source).encode()
        result = self.check(transport=lambda url: (new_raw, 200, url))
        self.assertEqual(result["changed_attribute_category_counts"], {
            "properties.address": 1,
            "properties.name": 1,
            "properties.remarks": 1,
        })
        self.assertEqual(result["feature_indices_differing_count"], 1)
        self.assertNotIn("PRIVATE_ADDRESS_EXAMPLE_333", json.dumps(result))
        self.assertNotIn("PRIVATE_REMARKS_EXAMPLE_777", json.dumps(result))

    def test_geometry_coordinate_change_reports_category_not_coordinates(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        coords = source["features"][0]["geometry"]["coordinates"]
        coords[0] += 0.0001
        result = self.check(transport=lambda url: (
            json.dumps(source).encode(), 200, url
        ))
        self.assertEqual(result["changed_attribute_category_counts"],
                         {"geometry.coordinates": 1})
        self.assertNotIn("geometry", result)
        self.assertFalse(result["facility_identity_approved"])

    def test_unknown_source_property_key_is_redacted_even_if_secret_named(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        source["features"][0]["properties"]["SECRET_PERSON_12999_PHONE"] = "VALUE_PRIVATE"
        result = self.check(transport=lambda url: (
            json.dumps(source).encode(), 200, url
        ))
        self.assertEqual(result["changed_attribute_category_counts"],
                         {"properties.other": 1})
        report = json.dumps(result)
        self.assertNotIn("SECRET_PERSON_12999_PHONE", report)
        self.assertNotIn("VALUE_PRIVATE", report)

    def test_unknown_geometry_and_feature_keys_collapse_to_other(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        feat = source["features"][0]
        feat["PRIVATE_FEATURE_METADATA_123"] = "SECRET"
        feat["geometry"]["HIDDEN_FIELD_456"] = "SECRET"
        result = self.check(transport=lambda url: (
            json.dumps(source).encode(), 200, url
        ))
        self.assertEqual(result["changed_attribute_category_counts"],
                         {"feature.other": 1, "geometry.other": 1})
        self.assertNotIn("PRIVATE_FEATURE_METADATA_123", json.dumps(result))
        self.assertNotIn("HIDDEN_FIELD_456", json.dumps(result))

    def test_key_absence_is_a_field_difference_even_when_value_is_null(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        del source["features"][0]["properties"]["address"]
        result = self.check(transport=lambda url: (
            json.dumps(source).encode(), 200, url
        ))
        self.assertEqual(result["changed_attribute_category_counts"],
                         {"properties.address": 1})
        self.assertFalse(result["parsed_json_typed_equal"])

    def test_same_allowlisted_category_changed_at_two_indices_counts_two(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        source["features"].append(json.loads(json.dumps(source["features"][0])))
        archived = self.raws[A_FLOOD_SOURCE]
        original = json.loads(archived)
        original["features"].append(json.loads(json.dumps(original["features"][0])))
        old_bytes = json.dumps(original).encode()
        new_features = source["features"]
        new_features[0]["properties"]["name"] = "PRIVATE_ALPHA"
        new_features[1]["properties"]["name"] = "PRIVATE_BETA"
        new_bytes = json.dumps(source).encode()
        diff = _diff_summary(old_bytes, new_bytes)
        self.assertEqual(diff["feature_indices_differing_count"], 2)
        self.assertEqual(diff["changed_attribute_category_counts"],
                         {"properties.name": 2})
        self.assertNotIn("PRIVATE_ALPHA", json.dumps(diff))

    def test_feature_append_reports_added_or_removed_not_a_new_facility(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        source["features"].append(source["features"][0])
        result = self.check(transport=lambda url: (
            json.dumps(source).encode(), 200, url
        ))
        self.assertEqual(result["changed_attribute_category_counts"],
                         {"feature.added_or_removed": 1})
        self.assertEqual(result["feature_count_delta_c_minus_d"], 1)
        self.assertEqual(result["feature_indices_differing_count"], 1)
        self.assertEqual(result["comparison_scope"],
                         "SAME_FEATURE_ARRAY_INDEX_NO_IDENTITY_JOIN")

    def test_root_only_change_does_not_appear_as_changed_feature_field(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        source["secret_root_field_543"] = "PRIVATE_ROOT_VALUE"
        result = self.check(transport=lambda url: (
            json.dumps(source).encode(), 200, url
        ))
        self.assertTrue(result["non_feature_root_changed"])
        self.assertEqual(result["changed_attribute_category_counts"], {})
        self.assertEqual(result["feature_indices_differing_count"], 0)
        self.assertNotIn("PRIVATE_ROOT_VALUE", json.dumps(result))

    def test_reformatting_only_has_no_attribute_changes(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        reformatted = json.dumps(source, indent=4).encode()
        result = self.check(transport=lambda url: (reformatted, 200, url))
        self.assertFalse(result["same_bytes"])
        self.assertTrue(result["parsed_json_typed_equal"])
        self.assertEqual(result["changed_attribute_category_counts"], {})
        self.assertEqual(result["feature_indices_differing_count"], 0)

    def test_existing_mismatch_semantics_are_not_weakened_by_category_summary(self):
        source = json.loads(self.raws[A_FLOOD_SOURCE])
        source["features"][0]["properties"]["name"] = "SYNTHETIC_CHANGE"
        result = self.check(transport=lambda url: (
            json.dumps(source).encode(), 200, url
        ))
        self.assertEqual(result["status"], "C_A_FLOOD_CURRENT_BYTE_MISMATCH_HOLD")
        self.assertEqual(result["cause_of_prior_mismatch"], "UNDETERMINED")
        self.assertFalse(result["c_independent_approved"])
        self.assertFalse(result["publication_approved"])


    def test_feature_order_swap_is_not_mistaken_for_changed_raw_membership(self):
        original = json.loads(self.raws[A_FLOOD_SOURCE])
        feat2 = json.loads(json.dumps(original["features"][0]))
        feat2["properties"]["name"] = "HIDDEN_SYNTHETIC_B"
        feat2["geometry"]["coordinates"][0] += 0.0002
        original["features"].append(feat2)
        old = json.dumps(original).encode()
        original["features"].reverse()
        newer = json.dumps(original).encode()
        summary = _diff_summary(old, newer)
        self.assertFalse(summary["parsed_json_typed_equal"])
        self.assertEqual(summary["feature_indices_differing_count"], 2)
        self.assertTrue(summary["feature_multiset_canonical_json_equal"])
        self.assertEqual(summary["feature_multiset_d_only_occurrences"], 0)
        self.assertEqual(summary["feature_multiset_c_only_occurrences"], 0)
        self.assertTrue(summary["same_features_in_different_array_order"])
        self.assertNotIn("HIDDEN_SYNTHETIC_B", json.dumps(summary))

    def test_same_count_but_changed_feature_content_has_multiset_difference(self):
        original = json.loads(self.raws[A_FLOOD_SOURCE])
        changed = json.loads(self.raws[A_FLOOD_SOURCE])
        changed["features"][0]["properties"]["remarks"] = "PRIVATE_SYNTHETIC_DIFF"
        summary = _diff_summary(json.dumps(original).encode(), json.dumps(changed).encode())
        self.assertFalse(summary["feature_multiset_canonical_json_equal"])
        self.assertEqual(summary["feature_multiset_d_only_occurrences"], 1)
        self.assertEqual(summary["feature_multiset_c_only_occurrences"], 1)
        self.assertFalse(summary["same_features_in_different_array_order"])
        self.assertNotIn("PRIVATE_SYNTHETIC_DIFF", json.dumps(summary))

    def test_duplicate_feature_multiplicity_must_not_be_dropped(self):
        original = json.loads(self.raws[A_FLOOD_SOURCE])
        old = json.loads(json.dumps(original))
        old["features"].append(old["features"][0])
        new = json.loads(json.dumps(original))
        new["features"][0]["properties"]["name"] = "PRIVATE_REPLACEMENT"
        new["features"].append(original["features"][0])
        s = _diff_summary(json.dumps(old).encode(), json.dumps(new).encode())
        self.assertFalse(s["feature_multiset_canonical_json_equal"])
        self.assertEqual(s["feature_multiset_d_only_occurrences"], 1)
        self.assertEqual(s["feature_multiset_c_only_occurrences"], 1)

    def test_serialization_only_changes_preserve_feature_multiset(self):
        original = self.raws[A_FLOOD_SOURCE]
        pretty = json.dumps(json.loads(original), indent=4, sort_keys=True).encode()
        s = _diff_summary(original, pretty)
        self.assertTrue(s["parsed_json_typed_equal"])
        self.assertTrue(s["feature_multiset_canonical_json_equal"])
        self.assertFalse(s["same_features_in_different_array_order"])
        self.assertEqual(s["feature_multiset_d_only_occurrences"], 0)
        self.assertEqual(s["feature_multiset_c_only_occurrences"], 0)

    def test_feature_added_or_removed_preserves_unmatched_counts(self):
        original = json.loads(self.raws[A_FLOOD_SOURCE])
        extra = json.loads(json.dumps(original))
        extra["features"].append(extra["features"][0])
        s = _diff_summary(json.dumps(original).encode(), json.dumps(extra).encode())
        self.assertFalse(s["feature_multiset_canonical_json_equal"])
        self.assertEqual(s["feature_multiset_d_only_occurrences"], 0)
        self.assertEqual(s["feature_multiset_c_only_occurrences"], 1)
        self.assertFalse(s["same_features_in_different_array_order"])

    def test_unrecognized_dynamic_source_keys_not_emitted_even_with_multiset(self):
        original = json.loads(self.raws[A_FLOOD_SOURCE])
        changed = json.loads(json.dumps(original))
        changed["features"][0]["properties"]["PRIVATE_UNRECOGNIZED_KEY_812"] = "PRIVATE_VALUE_812"
        s = _diff_summary(json.dumps(original).encode(), json.dumps(changed).encode())
        out = json.dumps(s)
        self.assertEqual(s["changed_attribute_category_counts"], {"properties.other": 1})
        self.assertNotIn("PRIVATE_UNRECOGNIZED_KEY_812", out)
        self.assertNotIn("PRIVATE_VALUE_812", out)
        self.assertNotIn("sha256", out)
        self.assertFalse(s["feature_multiset_canonical_json_equal"])

    def test_current_mismatch_still_holds_with_feature_multiset_diagnostic(self):
        original = json.loads(self.raws[A_FLOOD_SOURCE])
        original["features"][0]["properties"]["remarks"] = "PRIVATE_DIAGNOSTIC_ONLY"
        raw = json.dumps(original).encode()
        result = self.check(transport=lambda url: (raw, 200, url))
        self.assertEqual(result["status"], "C_A_FLOOD_CURRENT_BYTE_MISMATCH_HOLD")
        self.assertFalse(result["feature_multiset_canonical_json_equal"])
        self.assertFalse(result["c_independent_approved"])
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["cause_of_prior_mismatch"], "UNDETERMINED")


if __name__ == "__main__":
    unittest.main()
