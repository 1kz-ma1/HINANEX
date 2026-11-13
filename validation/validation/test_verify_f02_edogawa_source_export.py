"""Deterministic synthetic negative tests for F02's independent C row audit."""
import copy
import csv
import hashlib
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_f02_edogawa_source_export import (  # noqa: E402
    SOURCE_PAGE, SourceExportAuditFailure, audit,
)


def fake_source(name="架空テスト会館", address=False):
    headers = ["名称", "URL", "災害種別記号", "コメント", "緯度", "経度"]
    values = [name, "https://example.invalid/fake", "icon.png", "合成", "35.7001", "139.8701"]
    if address:
        headers.append("住所")
        values.append("架空住所1丁目")
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(values)
    return output.getvalue().encode("cp932")


def fixture(address=False):
    raw = fake_source(address=address)
    name = "架空テスト会館"
    key = f"13123|{name}|35.7001000|139.8701000"
    record = {
        "id": "edogawa-" + hashlib.sha256(key.encode()).hexdigest()[:16],
        "name": name,
        "latitude": 35.7001,
        "longitude": 139.8701,
        "address": "架空住所1丁目" if address else None,
        "facility_type": "shelter",
        "detail_url": "https://example.invalid/fake",
        "notes": "合成",
        "supported_disasters": None,
        "accessibility": None,
        "capacity": None,
    }
    dataset = {
        "region_code": "13123",
        "requirement_code": "shelter_location",
        "records": [record],
        "evidence": [{"source_url": SOURCE_PAGE, "published_at": None}],
    }
    normalized = copy.deepcopy(dataset)
    exported = {
        "region": {"code": "13123"},
        "meta": {"schema_version": "0.9", "dataset_count": 1},
        "datasets": [copy.deepcopy(dataset)],
        "assessments": [{"region_code": "13123", "requirement_code": "shelter_location", "record_count": 1}],
    }
    return raw, raw, normalized, exported


class F02EdogawaSourceAuditTests(unittest.TestCase):
    def test_valid_synthetic_mapping_is_consistent_but_unapproved(self):
        inputs = fixture()
        result = audit(*inputs, expected_sha256=hashlib.sha256(inputs[0]).hexdigest())
        self.assertEqual(result["status"], "C_SOURCE_TO_EXPORT_CONSISTENT")
        self.assertEqual(result["source_rows"], 1)
        self.assertEqual(result["publication_approval"], "NOT_GRANTED")
        self.assertEqual(result["physical_site_identity"], "NOT_APPROVED")

    def test_optional_source_address_is_passthrough(self):
        self.assertEqual(audit(*fixture(address=True))["row_mismatches"], 0)

    def test_independent_source_and_d_raw_byte_mismatch(self):
        raw, _, norm, export = fixture()
        with self.assertRaisesRegex(SourceExportAuditFailure, "CSV.*differ"):
            audit(raw, raw + b" ", norm, export)

    def test_expected_hash_mismatch_is_rejected(self):
        with self.assertRaisesRegex(SourceExportAuditFailure, "SHA-256"):
            audit(*fixture(), expected_sha256="0" * 64)

    def test_original_name_mismatch_is_rejected(self):
        inputs = list(fixture())
        inputs[3]["datasets"][0]["records"][0]["name"] = "別の施設"
        with self.assertRaisesRegex(SourceExportAuditFailure, "name differs"):
            audit(*inputs)

    def test_original_coordinate_mismatch_is_rejected(self):
        inputs = list(fixture())
        inputs[3]["datasets"][0]["records"][0]["longitude"] = 139.97
        with self.assertRaisesRegex(SourceExportAuditFailure, "longitude differs"):
            audit(*inputs)

    def test_stable_id_mismatch_is_rejected(self):
        inputs = list(fixture())
        inputs[2]["records"][0]["id"] = "false"
        with self.assertRaisesRegex(SourceExportAuditFailure, "id differs"):
            audit(*inputs)

    def test_disaster_suitability_is_never_inferred_from_icon(self):
        inputs = list(fixture())
        inputs[3]["datasets"][0]["records"][0]["supported_disasters"] = ["flood"]
        with self.assertRaisesRegex(SourceExportAuditFailure, "supported_disasters differs"):
            audit(*inputs)

    def test_source_update_date_not_translated_to_publication(self):
        inputs = list(fixture())
        inputs[3]["datasets"][0]["evidence"][0]["published_at"] = "2025-12-11"
        with self.assertRaisesRegex(SourceExportAuditFailure, "published_at"):
            audit(*inputs)

    def test_missing_assessment_rejected(self):
        inputs = list(fixture())
        inputs[3]["assessments"] = []
        with self.assertRaisesRegex(SourceExportAuditFailure, "DatasetAssessment"):
            audit(*inputs)

    def test_wrong_region_rejected(self):
        inputs = list(fixture())
        inputs[3]["region"]["code"] = "15100"
        with self.assertRaisesRegex(SourceExportAuditFailure, "region mismatch"):
            audit(*inputs)

    def test_no_external_dataset_is_implicitly_approved(self):
        inputs = list(fixture())
        inputs[3]["datasets"][0]["evidence"] = []
        with self.assertRaisesRegex(SourceExportAuditFailure, "Evidence missing"):
            audit(*inputs)


if __name__ == "__main__":
    unittest.main()
