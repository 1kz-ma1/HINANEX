"""Offline-only synthetic tests of Nagoya P1 per-facility PDF text-row triage."""
import copy
import hashlib
import unittest

from check_nagoya_official_pdf_updates import WATCH_SOURCES, SAFETY
from triage_nagoya_pdf_facility_changes import (
    ALL_STATES, BY_WARD, FACILITIES, INCONSISTENT, SOURCE_UNCHANGED,
    SOURCE_CHANGED_ROW_CHANGED, SOURCE_CHANGED_ROW_UNCHANGED, UNRESOLVED,
    compare_facility_snapshots, local_output, make_facility_snapshot,
    validate_facility_snapshot,
)


class FacilityRowDiffTests(unittest.TestCase):
    def prepare(self, changed_ward=None, failure_pair=None, revision="original"):
        raw = []
        downloaded = {}
        for ward, url in WATCH_SOURCES:
            pdf = b"%PDF-1.7\n" + ward.encode("utf8") + revision.encode("ascii")
            if ward == changed_ward:
                pdf += b"_VERSION2"
            downloaded[ward] = pdf
            raw.append({
                "ward": ward, "url": url,
                "sha256": hashlib.sha256(pdf).hexdigest(),
                "byte_size": len(pdf)
            })
        snapshot = {
            "schema_id": "hinanex.nagoya-official-pdf-byte-watch.v1",
            "source_list_as_of": "2026-09-01",
            "captured_at_utc": "2026-10-22T08:15:00Z",
            "safety": dict(SAFETY),
            "sources": raw,
        }

        def extractor(_, ward):
            return {
                pair: (None if pair == failure_pair else
                       hashlib.sha256((":".join(pair) + (revision if
                                      (changed_ward == ward and pair == BY_WARD[ward][0])
                                      else "")).encode("utf8")).hexdigest())
                for pair in BY_WARD[ward]
            }

        return make_facility_snapshot(snapshot, downloaded, extractor=extractor,
                                      captured_at="2026-10-22T09:00:00Z")

    def test_all_nine_records_same_source_and_no_approval(self):
        first = self.prepare()
        self.assertEqual(len(first["facilities"]), 9)
        self.assertEqual(len(first["sources"]), 5)
        self.assertEqual(first["safety"], SAFETY)
        self.assertEqual(sum(x["extract_status"] == "MATCHED" for x in first["facilities"]), 9)
        self.assertTrue(all(set(r) == {
            "ward", "name", "address", "extract_status", "row_text_sha256"
        } for r in first["facilities"]))
        self.assertEqual(validate_facility_snapshot(copy.deepcopy(first)), first)
        diff = compare_facility_snapshots(first, copy.deepcopy(first))
        self.assertEqual(diff["human_review_required_count"], 0)
        # Previously, CLI wrongly printed 0/9 because comparison rows lack
        # extract_status. Verify both snapshots report real success counts.
        self.assertEqual(diff["baseline_extract_matched_count"], 9)
        self.assertEqual(diff["current_extract_matched_count"], 9)
        self.assertTrue(all(x["classification"] == SOURCE_UNCHANGED for x in diff["facilities"]))
        self.assertEqual(diff["safety"], SAFETY)

    def test_changed_pdf_only_one_detected_row_but_all_ward_records_remain_review(self):
        before = self.prepare()
        ward = next(w for w, _ in WATCH_SOURCES if len(BY_WARD[w]) > 1)
        after = self.prepare(changed_ward=ward, revision="revised")
        # Revise synthetic extractor to affect ONLY a single row in that ward.
        for source in after["sources"]:
            if source["ward"] != ward:
                old = next(x for x in before["sources"] if x["ward"] == ward)
                # Restore unchanged-source hash for the other four wards.
                original = next(x for x in before["sources"] if x["ward"] == source["ward"])
                source["sha256"] = original["sha256"]
        for rec in after["facilities"]:
            previous = next(x for x in before["facilities"]
                            if x["ward"] == rec["ward"] and x["name"] == rec["name"])
            if rec["ward"] != ward or (rec["name"], rec["address"]) != BY_WARD[ward][0]:
                rec["row_text_sha256"] = previous["row_text_sha256"]
        diff = compare_facility_snapshots(before, after)
        self.assertEqual(diff["source_changed_count"], 1)
        self.assertEqual(diff["row_changed_candidate_count"], 1)
        self.assertEqual(diff["human_review_required_count"], len(BY_WARD[ward]))
        self.assertEqual(sum(x["classification"] == SOURCE_CHANGED_ROW_UNCHANGED
                             for x in diff["facilities"]), len(BY_WARD[ward])-1)
        self.assertEqual(sum(x["classification"] == SOURCE_CHANGED_ROW_CHANGED
                             for x in diff["facilities"]), 1)
        self.assertEqual(diff["safety"]["official_facility_positions_accepted"], 0)

    def test_missing_or_ambiguous_extraction_remains_unresolved_even_if_bytes_same(self):
        first = self.prepare()
        pair = BY_WARD[WATCH_SOURCES[0][0]][0]
        second = self.prepare(failure_pair=pair)
        diff = compare_facility_snapshots(first, second)
        self.assertEqual(diff["unresolved_extraction_count"], 1)
        self.assertTrue(any(x["classification"] == UNRESOLVED for x in diff["facilities"]))
        self.assertEqual(diff["human_review_required_count"], 1)
        self.assertEqual(diff["baseline_extract_matched_count"], 9)
        self.assertEqual(diff["current_extract_matched_count"], 8)

    def test_same_bytes_unstable_text_extraction_not_mistaken_for_official_change(self):
        before = self.prepare()
        after = copy.deepcopy(before)
        after["facilities"][0]["row_text_sha256"] = "f" * 64
        diff = compare_facility_snapshots(before, after)
        self.assertEqual(diff["facilities"][0]["classification"], INCONSISTENT)
        self.assertEqual(diff["source_changed_count"], 0)
        self.assertEqual(diff["human_review_required_count"], 1)
        self.assertEqual(diff["baseline_extract_matched_count"], 9)
        self.assertEqual(diff["current_extract_matched_count"], 9)

    def test_integrity_fail_closed_for_source_sha_or_malformed_records(self):
        first = self.prepare()
        bad = copy.deepcopy(first)
        bad["safety"]["approved_for_map"] = True
        with self.assertRaises(ValueError):
            compare_facility_snapshots(first, bad)
        bad = copy.deepcopy(first)
        bad["facilities"][0]["name"] = "unverified replacement"
        with self.assertRaises(ValueError):
            compare_facility_snapshots(first, bad)
        bad = copy.deepcopy(first)
        bad["facilities"][0]["row_text_sha256"] = None
        with self.assertRaises(ValueError):
            validate_facility_snapshot(bad)
        bad = copy.deepcopy(first)
        bad["sources"][0]["url"] = "https://nonofficial.example/pdf"
        with self.assertRaises(ValueError):
            validate_facility_snapshot(bad)

    def test_external_baseline_sha_mismatch_blocks_first_facility_capture(self):
        from check_nagoya_official_pdf_updates import SCHEMA_ID
        ward, url = WATCH_SOURCES[0]
        fake = {w: b"%PDF-1.7\n" + w.encode("utf-8") for w, _ in WATCH_SOURCES}
        raw = {
            "schema_id": SCHEMA_ID, "source_list_as_of": "2026-09-01",
            "captured_at_utc": "2026-10-22T00:00:00Z",
            "safety": dict(SAFETY),
            "sources": [{
                "ward": w, "url": u, "sha256": hashlib.sha256(fake[w]).hexdigest(),
                "byte_size": len(fake[w])
            } for w, u in WATCH_SOURCES],
        }
        raw["sources"][0]["sha256"] = "a"*64
        with self.assertRaisesRegex(ValueError, "byte baseline mismatch"):
            make_facility_snapshot(raw, fake, extractor=lambda _, ward: {
                pair: "b"*64 for pair in BY_WARD[ward]
            })

    def test_local_files_are_bounded_and_never_overwritten_by_design(self):
        from pathlib import Path
        folder = Path("/tmp/nagoya-local")
        self.assertEqual(local_output(folder, "official_pdf_facility_snapshot_LOCAL.json"),
                         folder / "official_pdf_facility_snapshot_LOCAL.json")
        self.assertEqual(local_output(folder, "official_pdf_facility_comparison_round2_LOCAL.json"),
                         folder / "official_pdf_facility_comparison_round2_LOCAL.json")
        for bad in ("../official_pdf_facility_snapshot_LOCAL.json", "/tmp/another.json",
                    "team_review_p1_LOCAL.json", "official_pdf_facility_comparison.json"):
            with self.subTest(filename=bad), self.assertRaises(ValueError):
                local_output(folder, bad)


    def test_synthetic_change_matrix_fail_closed_before_actual_pdf_acceptance(self):
        """Deterministic source/row result matrix; in-memory real PDF test is
        separately executable with optional PyMuPDF on an operator machine."""
        baseline = self.prepare()
        ward = next(w for w, _ in WATCH_SOURCES if len(BY_WARD[w]) > 1)
        first = next(i for i, row in enumerate(baseline["facilities"])
                     if row["ward"] == ward)
        src_idx = next(i for i, src in enumerate(baseline["sources"])
                       if src["ward"] == ward)
        # All six are changed-PDF scenarios. Only a confirmed same-row text
        # alteration is ROW_TEXT_CHANGED. Deleted/renamed/address edits may
        # cause lookup to become ambiguous, not proven removal or relocation.
        for scenario in ("added", "deleted", "renamed", "address_changed",
                         "row_note_changed", "footnote_changed", "metadata_changed"):
            with self.subTest(scenario=scenario):
                current = copy.deepcopy(baseline)
                current["sources"][src_idx]["sha256"] = "f" * 64
                if scenario in ("deleted", "renamed", "address_changed"):
                    current["facilities"][first]["extract_status"] = "UNRESOLVED"
                    current["facilities"][first]["row_text_sha256"] = None
                if scenario == "row_note_changed":
                    current["facilities"][first]["row_text_sha256"] = "e" * 64
                report = compare_facility_snapshots(baseline, current)
                affected = [r for r in report["facilities"] if r["ward"] == ward]
                other = [r for r in report["facilities"] if r["ward"] != ward]
                self.assertEqual(report["source_changed_count"], 1)
                self.assertEqual(report["human_review_required_count"],
                                 len(BY_WARD[ward]))
                self.assertTrue(all(r["classification"] != SOURCE_UNCHANGED
                                    for r in affected))
                self.assertTrue(all(r["classification"] == SOURCE_UNCHANGED
                                    for r in other))
                self.assertFalse(report["safety"]["approved_for_map"])
                self.assertEqual(report["safety"]["official_facility_positions_accepted"], 0)
                if scenario in ("deleted", "renamed", "address_changed"):
                    self.assertEqual(report["unresolved_extraction_count"], 1)
                    self.assertEqual(report["current_extract_matched_count"], 8)
                    self.assertEqual(report["row_changed_candidate_count"], 0)
                elif scenario == "row_note_changed":
                    self.assertEqual(report["row_changed_candidate_count"], 1)
                    self.assertEqual(report["unresolved_extraction_count"], 0)
                    self.assertEqual(report["current_extract_matched_count"], 9)
                else:
                    # Additions outside the tracked nine, document footnotes
                    # and PDF metadata changes never look like an approved
                    # new site, even though all tracked row text is stable.
                    self.assertEqual(report["row_changed_candidate_count"], 0)
                    self.assertEqual(report["unresolved_extraction_count"], 0)
                    self.assertEqual(report["current_extract_matched_count"], 9)



if __name__ == "__main__":
    unittest.main()
