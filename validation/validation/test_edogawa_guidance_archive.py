"""Synthetic offline checks for separately archived municipal evacuation guidance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from archive_edogawa_guidance import (
    GUIDANCE, GuidanceFailure, capture, verify,
)


def pages():
    return {
        "municipal_water_evacuation_guidance": (
            "<html><body>水害時の避難方法　待避施設。"
            "避難する時間がない場合に緊急避難。低層階は浸水。</body></html>"
        ).encode(),
        "municipal_weather_evacuation_operations": (
            "<html><body>風水害第二次態勢は待避施設へ、"
            "災害対策本部の判断により開設。</body></html>"
        ).encode(),
    }


def make(root, replace=None):
    raws = pages()
    if replace:
        raws.update(replace)
    def fetch(url):
        k = next(k for k, (_, u, _) in GUIDANCE.items() if u == url)
        return raws[k], url, {"content_type": "text/html"}
    folder = Path(root) / "guidance"
    capture(folder, fetch=fetch, now=datetime(2026, 10, 13, tzinfo=timezone.utc))
    return folder


class GuidanceArchiveTests(unittest.TestCase):
    def test_correct_original_contents_remain_review_only(self):
        with TemporaryDirectory() as root:
            folder = make(root)
            result = verify(folder)
            self.assertEqual(result["source_count"], 2)
            self.assertFalse(result["official_scope_and_flood_only_semantics_accepted"])
            self.assertFalse(result["human_c_reviewer_signed_off"])
            self.assertEqual(result["approved_cross_source_pairs"], 0)
            self.assertEqual(result["flood_classifications_added"], 0)

    def test_status_200_error_page_rejected_before_archive_write(self):
        with TemporaryDirectory() as root:
            folder = Path(root) / "guidance"
            raws = pages()
            raws["municipal_weather_evacuation_operations"] = (
                b"<html><body>Temporarily unavailable</body></html>"
            )
            def fetch(url):
                k = next(k for k, (_, u, _) in GUIDANCE.items() if u == url)
                return raws[k], url, {"content_type": "text/html"}
            with self.assertRaisesRegex(GuidanceFailure, "missing official context marker"):
                capture(folder, fetch=fetch)
            self.assertFalse(folder.exists())

    def test_missing_or_modified_original_fails_closed(self):
        with TemporaryDirectory() as root:
            folder = make(root)
            f = folder / GUIDANCE["municipal_water_evacuation_guidance"][0]
            f.write_bytes(f.read_bytes() + b" ")
            with self.assertRaisesRegex(GuidanceFailure, "SHA256 mismatch"):
                verify(folder)

    def test_manifest_claiming_flood_approval_is_rejected(self):
        with TemporaryDirectory() as root:
            folder = make(root)
            mf = folder / "guidance_manifest.json"
            obj = json.loads(mf.read_text(encoding="utf-8"))
            obj["official_scope_and_flood_only_semantics_accepted"] = True
            mf.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(GuidanceFailure, "pretends approval"):
                verify(folder)

    def test_redirect_to_another_source_host_fails(self):
        with TemporaryDirectory() as root:
            folder = Path(root) / "guidance"
            def fetch(url):
                k = next(k for k, (_, u, _) in GUIDANCE.items() if u == url)
                return pages()[k], "https://www.metro.ed.jp/not-municipal", {}
            with self.assertRaisesRegex(GuidanceFailure, "another publisher"):
                capture(folder, fetch=fetch)
            self.assertFalse(folder.exists())

    def test_source_set_and_date_must_be_exact(self):
        with TemporaryDirectory() as root:
            folder = make(root)
            mf = folder / "guidance_manifest.json"
            obj = json.loads(mf.read_text(encoding="utf-8"))
            obj["source_items"].pop()
            mf.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(GuidanceFailure, "set malformed"):
                verify(folder)

    def test_refuses_existing_data_overwrite(self):
        with TemporaryDirectory() as root:
            folder = make(root)
            def fetch(url):
                k = next(k for k, (_, u, _) in GUIDANCE.items() if u == url)
                return pages()[k], url, {}
            with self.assertRaisesRegex(GuidanceFailure, "new or empty"):
                capture(folder, fetch=fetch)


if __name__ == "__main__":
    unittest.main()
