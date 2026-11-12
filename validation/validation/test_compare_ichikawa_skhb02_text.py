"""Synthetic C-only regressions; no source or municipal row automatically approved."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from compare_ichikawa_skhb02_text import compare_textual_sources, PREFIX, SOURCE_URL, CITY_URL, PDFS


def fixture(city_address="市川2-32-5", source_address=None):
    source_address = (PREFIX + city_address) if source_address is None else source_address
    raw = json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {
            "name": "SYNTHETIC SCHOOL", "address": source_address,
            "disaster2": 1,
        }, "geometry": {"type": "Point", "coordinates": [139.9, 35.7]}}],
    }, ensure_ascii=False).encode("utf-8")
    ref = {
        "status": "AI_TRANSCRIBED_OFFICIAL_TABLE_UNAPPROVED",
        "gsi_source_url": SOURCE_URL, "gsi_sha256": sha256(raw).hexdigest(),
        "expected_total_tile_features": 1,
        "candidate_address_prefix": PREFIX, "city_page_url": CITY_URL,
        "city_page_update_date": "2026-09-08",
        "transcription_method":
            "AI_EXTRACTED_FROM_OFFICIAL_HTML_AND_PDF_RENDER_NOT_HUMAN_APPROVED",
        "municipal_pdf_hazard_column_label": "土砂災害",
        "rows": [{
            "gsi_feature_index": 0, "city_section": "A",
            "city_row_number": 1, "city_name": "SYNTHETIC SCHOOL",
            "city_address": city_address, "city_pdf_url": PDFS["A"],
            "landslide_symbol_transcribed": "○",
        }],
    }
    return raw, ref


class IchikawaTextCheckTests(unittest.TestCase):
    def test_exact_text_agreement_never_proves_identity_or_safety(self):
        raw, ref = fixture()
        out = compare_textual_sources(raw, ref)
        self.assertEqual(out["status"], "C_AI_TRANSCRIBED_TEXT_CROSSCHECK_UNAPPROVED")
        self.assertEqual(out["text_name_and_address_agreement_count"], 1)
        for flag in ("municipal_document_transcription_authenticated",
                     "official_pdf_byte_hash_checked", "municipality_boundary_verified",
                     "independent_human_c_approved", "facility_identity_approved",
                     "disaster_use_approved", "current_shelter_opening_verified"):
            self.assertFalse(out[flag])
        self.assertEqual(out["safe_destination_count_approved"], 0)

    def test_name_only_address_variation_is_review_not_same_facility(self):
        raw, ref = fixture(city_address="市川南3・4丁目地先",
                           source_address="千葉県市川市市川南3")
        out = compare_textual_sources(raw, ref)
        self.assertEqual(out["text_name_only_address_review_count"], 1)
        self.assertEqual(out["text_name_and_address_agreement_count"], 0)
        self.assertFalse(out["rows"][0]["facility_identity_approved"])

    def test_tamper_source_or_claimed_sha_blocks(self):
        raw, ref = fixture()
        with self.assertRaisesRegex(ValueError, "DIGEST"):
            compare_textual_sources(raw + b" ", ref)
        with self.assertRaisesRegex(ValueError, "DIGEST"):
            compare_textual_sources(raw, {**ref, "gsi_sha256": "0" * 64})

    def test_missing_or_duplicate_candidate_blocks(self):
        raw, ref = fixture()
        with self.assertRaisesRegex(ValueError, "CANDIDATE_COVERAGE"):
            compare_textual_sources(raw, {**ref, "rows": []})
        with self.assertRaisesRegex(ValueError, "DUPLICATE_GSI_INDEX"):
            compare_textual_sources(raw, {**ref, "rows": ref["rows"] * 2})

    def test_forged_city_url_pdf_or_verdict_blocks(self):
        raw, ref = fixture()
        for key, value in (("status", "APPROVED"),
                           ("gsi_source_url", "http://evil.example"),
                           ("city_page_url", "https://evil.example"),
                           ("transcription_method", "HUMAN_APPROVED")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                compare_textual_sources(raw, {**ref, key: value})
        for key, value in (("city_pdf_url", "https://evil.example"),
                           ("landslide_symbol_transcribed", "×")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                fake = deepcopy(ref)
                fake["rows"][0][key] = value
                compare_textual_sources(raw, fake)

    def test_source_marker_and_source_count_cannot_be_upgraded(self):
        raw, ref = fixture()
        with self.assertRaisesRegex(ValueError, "COUNT"):
            compare_textual_sources(raw, {**ref, "expected_total_tile_features": 0})
        doc = json.loads(raw)
        doc["features"][0]["properties"]["disaster2"] = 0
        modified = json.dumps(doc, ensure_ascii=False).encode()
        with self.assertRaisesRegex(ValueError, "MARKER"):
            compare_textual_sources(modified, {**ref, "gsi_sha256": sha256(modified).hexdigest()})

    def test_row_name_mismatch_is_pending_not_approved(self):
        raw, ref = fixture()
        fake = deepcopy(ref)
        fake["rows"][0]["city_name"] = "SYNTHETIC DIFFERENT"
        out = compare_textual_sources(raw, fake)
        self.assertEqual(out["other_difference_count"], 1)
        self.assertFalse(out["disaster_use_approved"])


if __name__ == "__main__":
    unittest.main()
