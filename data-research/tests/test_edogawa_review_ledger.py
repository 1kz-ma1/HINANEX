"""A-only tests: source matching produces suggestions, never flood verdicts."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "edogawa_review_ledger.py"
spec = importlib.util.spec_from_file_location("edogawa_review_ledger", TOOL)
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def page(rows):
    header = "<tr><th>番号</th><th>名称</th><th>住所</th><th>電話番号</th><th>使用可能階数</th></tr>"
    return ('<!doctype html><html><body><table><tr><th>無関係</th></tr></table>'
            '<table>' + header + rows + '</table></body></html>').encode("utf-8")


def row(number, name, address, floor):
    return ("<tr><td>" + number + "</td><td>" + name +
            "</td><td>" + address + "</td><td>-</td><td>" + floor +
            "</td></tr>")


def output(records, code="13123"):
    return json.dumps({
        "region": {"code": code},
        "datasets": [{"requirement_code": "shelter_location", "records": records}],
    }, ensure_ascii=False).encode("utf-8")


def location_csv(extra=""):
    return ("名称,URL,災害種別記号,コメント,緯度,経度" + extra +
            "\n架空避難所,https://test.invalid,icon,,35.7,139.8\n").encode("cp932")


class EdogawaLedgerTests(unittest.TestCase):
    def test_explicit_review_required_even_after_exact_name_and_address(self):
        water = page(row("1", "架空避難所(注)", "平井4丁目1番23号", "3階以上"))
        loc = output([{
            "id": "id-d-real-format", "name": "架空避難所",
            "address": "平井4丁目1番23号", "latitude": 35.7,
            "longitude": 139.8
        }])
        result = audit.proposal(water, loc, location_csv(",住所"))
        self.assertEqual(result["official_water_rows_found"], 1)
        self.assertEqual(result["only_name_hint_proposals"], 1)
        self.assertTrue(result["location_csv_has_address_field"])
        self.assertEqual(result["all_reviewed_pairs"], 0)
        self.assertEqual(result["all_scenario_classifications_added"], 0)
        entry = result["rows"][0]
        self.assertEqual(entry["review_status"], "UNREVIEWED")
        self.assertEqual(entry["flood_scenario_status"], "UNCHANGED_UNKNOWN")
        self.assertEqual(entry["usable_floor_raw"], "3階以上")
        self.assertEqual(entry["source_record_trace"], "table=2;row=2")
        self.assertTrue(entry["candidate_location_rows"][0]["address_raw_exact_match"])
        self.assertEqual(entry["candidate_location_rows"][0]["matching_basis"],
                         "NAME_HINT_ONLY_NOT_VERIFIED")
        self.assertEqual(len(result["source_documents"]), 3)
        for doc in result["source_documents"]:
            self.assertEqual(len(doc["sha256"]), 64)

    def test_abbreviated_school_name_still_only_yields_unreviewed_hint(self):
        water = page(row("2", "小松川二小学校", "小松川3丁目6番4号", "3階以上"))
        loc = output([{"id": "e-2", "name": "小松川第二小学校", "address": None}])
        result = audit.proposal(water, loc, location_csv())
        self.assertEqual(result["exact_name_hint_rows"], 0)
        self.assertEqual(result["abbreviation_hint_rows"], 1)
        entry = result["rows"][0]
        self.assertEqual(entry["review_status"], "UNREVIEWED")
        self.assertEqual(entry["candidate_location_rows"][0]["location_facility_id"], "e-2")
        self.assertEqual(entry["candidate_location_rows"][0]["matching_basis"],
                         "ABBREVIATION_HINT_ONLY_NOT_VERIFIED")
        self.assertEqual(result["all_reviewed_pairs"], 0)
        self.assertEqual(result["all_scenario_classifications_added"], 0)

    def test_renamed_school_is_not_automatically_joined(self):
        water = page(row("-", "旧下小岩小学校", "南小岩7丁目8番1号",
                         "大規模水害では使用不可"))
        loc = output([
            {"id": "old", "name": "旧下小岩小学校（体育館のみ使用）"},
            {"id": "new", "name": "下小岩小学校"},
        ])
        result = audit.proposal(water, loc, location_csv())
        self.assertEqual(result["only_name_hint_proposals"], 0)
        self.assertEqual(result["rows"][0]["review_status"], "UNREVIEWED")
        self.assertEqual(result["rows"][0]["candidate_location_rows"], [])
        self.assertEqual(result["rows"][0]["flood_scenario_status"], "UNCHANGED_UNKNOWN")

    def test_missing_address_never_becomes_confirmed(self):
        water = page(row("1", "施設A", "公式住所1", "2階以上"))
        loc = output([{"id": "a", "name": "施設A", "address": None}])
        result = audit.proposal(water, loc, location_csv())
        self.assertFalse(result["location_csv_has_address_field"])
        candidate = result["rows"][0]["candidate_location_rows"][0]
        self.assertIsNone(candidate["address_raw_exact_match"])
        self.assertEqual(result["rows"][0]["review_status"], "UNREVIEWED")

    def test_duplicate_name_and_conflicting_address_remain_conflict(self):
        water = page(row("5", "同名施設", "川沿い1", "大規模水害では使用不可"))
        loc = output([
            {"id": "site1", "name": "同名施設", "address": "別住所"},
            {"id": "site2", "name": "同名施設", "address": "川沿い1"},
        ])
        result = audit.proposal(water, loc, location_csv())
        self.assertEqual(result["rows"][0]["review_status"], "CONFLICT")
        self.assertEqual(len(result["rows"][0]["candidate_location_rows"]), 2)
        self.assertEqual(result["all_reviewed_pairs"], 0)

    def test_unmatched_source_is_not_excluded(self):
        result = audit.proposal(page(row("-", "旧施設", "住所", "未確認")),
                                output([{"id": "new", "name": "現在の施設"}]),
                                location_csv())
        self.assertEqual(result["only_name_hint_proposals"], 0)
        self.assertEqual(result["rows"][0]["review_status"], "UNREVIEWED")
        self.assertEqual(result["all_scenario_classifications_added"], 0)

    def test_fail_closed_on_wrong_input(self):
        valid = page(row("1", "学校", "住所", "3階以上"))
        loc = output([{"id": "only", "name": "学校"}])
        with self.assertRaises(ValueError):
            audit.proposal(valid, output([{"id": "x", "name": "学校"}], "15100"),
                           location_csv())
        with self.assertRaises(ValueError):
            audit.proposal(valid, output([{"id": "x", "name": "学校"}] * 2),
                           location_csv())
        with self.assertRaises(ValueError):
            audit.proposal(b"<table><tr><td>no official headers</td></tr></table>",
                           loc, location_csv())
        with self.assertRaises(ValueError):
            audit.proposal(valid, loc, "名称,座標\n学校,1".encode("cp932"))


if __name__ == "__main__":
    unittest.main()
