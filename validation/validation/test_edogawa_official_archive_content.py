"""Network-free checks: 200-OK wrong content must never be evidence accepted."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from archive_edogawa_official_sources import SOURCES, capture
from validate_edogawa_official_archive import (
    ContentPreflightFailure, validate,
)
from verify_edogawa_water_join import WATER_URL


def water_page():
    body = [
        ("60", "下小岩小学校", "南小岩5丁目5番1号", "03-3650-1714", "2階以上"),
        ("-", "旧下小岩小学校", "南小岩7丁目8番1号", "-", "大規模水害では使用不可"),
        ("108", "都立 葛西工高等学校", "一之江7丁目68番1号", "03-3653-4111", "2階以上"),
        ("109", "私立 関東一高等学校", "松島2丁目10番11号", "03-3653-1541", "3階以上"),
    ]
    table = "<table><tr><th>番号</th><th>名称</th><th>住所</th><th>電話番号</th><th>使用可能階数</th></tr>"
    table += "".join("<tr>" + "".join("<td>" + str(v) + "</td>" for v in x) + "</tr>"
                     for x in body) + "</table>"
    return ("<html><body>" + WATER_URL + table + "</body></html>").encode("utf-8")


def location_csv():
    return (
        "名称,URL,災害種別記号,コメント,緯度,経度\r\n"
        "都立葛西工科高校,https://www.metro.ed.jp/kasaikoka-h/,icon,,35.7,139.8\r\n"
        "関東第一高校,http://www.kanto-ichiko.ac.jp/,icon,,35.8,139.9\r\n"
    ).encode("cp932")


def raw_sources():
    return {
        "water_facilities": water_page(),
        "municipal_locations": location_csv(),
        "municipal_school_list": b"<html><body>" + "都立葛西工科高校 関東第一高校".encode() + b"</body></html>",
        "municipal_primary_school_list": b"<html><body>" + "下小岩小学校".encode() + b"</body></html>",
        "municipal_2025_school_relocation": b"<html><body>" + "下小岩小学校".encode() + b"</body></html>",
        "tokyo_kasaikoka_school_access": b"<html><body>" + "葛西工科".encode() + b"</body></html>",
        "kanto_ichiko_school_overview": b"<html><body>" + "関東第一".encode() + b"</body></html>",
    }


def archive(temp, mutate=None, content_type=None):
    content = raw_sources()
    if mutate is not None:
        mutate(content)

    def fetch(url):
        key = next(k for k, (_, item_url) in SOURCES.items() if item_url == url)
        mime = ("text/csv" if key == "municipal_locations" else "text/html")
        if content_type and key in content_type:
            mime = content_type[key]
        return content[key], url, {"content_type": mime}

    destination = Path(temp) / "snapshot"
    capture(destination, fetch=fetch,
            now=datetime(2026, 10, 13, 0, 0, tzinfo=timezone.utc))
    return destination


class OfficialContentPreflightTests(unittest.TestCase):
    def test_structured_sources_are_review_only(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp)
            r = validate(dest)
            self.assertEqual(r["official_water_rows"], 4)
            self.assertEqual(r["location_csv_rows"], 2)
            self.assertEqual(r["source_count"], 7)
            self.assertEqual(r["status"],
                             "ORIGINAL_CONTENT_STRUCTURE_CHECKED_HUMAN_REVIEW_REQUIRED")
            self.assertEqual(r["approved_cross_source_pairs"], 0)
            self.assertEqual(r["flood_classifications_added"], 0)
            self.assertFalse(r["independent_human_c_review_signed_off"])
            self.assertTrue(r["former_current_school_addresses_distinct"])
            self.assertTrue(all(
                entry["flood_only_eligibility"] == "UNKNOWN"
                for entry in r["priority_institution_rows"]
            ))

    def test_http200_html_error_page_disguised_as_csv_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp, lambda content: content.update(
                municipal_locations=b"<html><body>403 Access denied</body></html>"
            ), content_type={"municipal_locations": "text/html"})
            with self.assertRaisesRegex(ContentPreflightFailure, "Content-Type"):
                validate(dest)

    def test_http200_csv_mime_but_html_payload_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp, lambda content: content.update(
                municipal_locations=b"<html><body>Error</body></html>"
            ))
            with self.assertRaisesRegex(ContentPreflightFailure, "header differs"):
                validate(dest)

    def test_http200_html_error_page_as_school_page_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp, lambda content: content.update(
                kanto_ichiko_school_overview=b"<html><body>Temporary error</body></html>"
            ))
            with self.assertRaisesRegex(ContentPreflightFailure, "marker absent"):
                validate(dest)

    def test_missing_water_table_rejected_despite_html_200(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp, lambda content: content.update(
                water_facilities=b"<html><body>Temporary Error</body></html>"
            ))
            with self.assertRaisesRegex(ContentPreflightFailure, "missing expected"):
                validate(dest)

    def test_changed_water_source_priority_row_must_be_reviewed(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp, lambda content: content.update(
                water_facilities=water_page().replace(
                    b"<td>109</td>", b"<td>999</td>"
                )
            ))
            with self.assertRaisesRegex(ContentPreflightFailure, "priority source row"):
                validate(dest)

    def test_old_current_school_collapse_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp, lambda content: content.update(
                water_facilities=water_page().replace(
                    "南小岩7丁目8番1号".encode(), "南小岩5丁目5番1号".encode()
                )
            ))
            with self.assertRaisesRegex(ContentPreflightFailure, "collapse"):
                validate(dest)

    def test_corrupt_csv_coordinate_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp, lambda content: content.update(
                municipal_locations=location_csv().replace(b"35.7", b"NaN")
            ))
            with self.assertRaisesRegex(ContentPreflightFailure, "non-finite"):
                validate(dest)

    def test_original_byte_tamper_rejected_before_semantic_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = archive(temp)
            f = dest / SOURCES["municipal_locations"][0]
            f.write_bytes(f.read_bytes() + b"\x00")
            with self.assertRaisesRegex(ContentPreflightFailure, "byte integrity"):
                validate(dest)


if __name__ == "__main__":
    unittest.main()
