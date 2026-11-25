"""No-network synthetic tests for A source capture, immutability, provenance."""
import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

CAPTURE = Path(__file__).resolve().parents[1] / "tools" / "capture_gsi_skhb02_original.py"
spec = importlib.util.spec_from_file_location("a_skhb02_capture", CAPTURE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
X, Y = 909, 403
SOURCE = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
AT = datetime(2026, 10, 26, tzinfo=timezone.utc)


def raw_doc(coords=None, marker=1):
    return json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "SYNTHETIC ONLY", "address": None, "disaster2": marker},
            "geometry": {"type": "Point", "coordinates": coords or [139.9, 35.7]},
        }],
    }, ensure_ascii=False).encode("utf-8")


def fake_fetch(raw=None, final=SOURCE, status=200):
    def fetch(url):
        if url != SOURCE:
            raise AssertionError("unexpected network request")
        return (raw if raw is not None else raw_doc()), {
            "http_status": status, "response_final_url": final,
            "etag_observed": '"sample"', "last_modified_observed": "Mon, 26 Oct 2026 00:00:00 GMT",
            "content_type_observed": "application/geo+json",
        }
    return fetch


class CaptureTests(unittest.TestCase):
    def test_capture_requires_explicit_outside_repo_and_preserves_exact_bytes(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp) / "first"
            doc = raw_doc()
            manifest = mod.capture_one(X, Y, folder, fetcher=fake_fetch(doc), now=AT)
            self.assertTrue(folder.is_dir())
            self.assertEqual((folder / f"skhb02-10-{X}-{Y}.geojson").read_bytes(), doc)
            self.assertEqual(manifest["official_tile_url_requested"], SOURCE)
            self.assertEqual(manifest["feature_count_tile_only"], 1)
            self.assertFalse(manifest["independent_c_approved"])
            self.assertFalse(manifest["publishable"])
            observed = json.loads((folder / "capture_manifest_UNREVIEWED.json").read_text())
            self.assertTrue(observed["response_headers_are_not_publication_dates"])
            self.assertIsNone(observed["official_dataset_update_date_verified"])
            a = json.loads((folder / "a_inspection_UNREVIEWED.json").read_text())
            self.assertEqual(a["source_sha256"], manifest["raw_sha256"])
            self.assertFalse(a["independent_c_approved"])

    def test_no_existing_folder_can_be_overwritten(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp) / "once"
            mod.capture_one(X, Y, folder, fetcher=fake_fetch(), now=AT)
            prior = (folder / f"skhb02-10-{X}-{Y}.geojson").read_bytes()
            with self.assertRaisesRegex(mod.CaptureError, "already exists"):
                mod.capture_one(X, Y, folder, fetcher=fake_fetch(raw_doc(marker=0)))
            self.assertEqual((folder / f"skhb02-10-{X}-{Y}.geojson").read_bytes(), prior)

    def test_invalid_source_and_unknown_tile_never_fetch(self):
        for args in ((-1, Y), (1024, Y), (X, 1024), (True, Y), (X, 1.0)):
            with self.subTest(args=args), self.assertRaises(mod.CaptureError):
                mod.official_tile_url(*args)

    def test_invalid_http_metadata_and_wrong_redirect_leave_no_archive(self):
        with TemporaryDirectory() as temp:
            for name, fetcher in [
                ("redirect", fake_fetch(final="https://evil.invalid/other")),
                ("notfound", fake_fetch(status=404)),
                ("malformed", fake_fetch(raw=b"{}")),
                ("wrong_hazard", fake_fetch(raw=raw_doc(marker=0))),
                ("off_tile", fake_fetch(raw=raw_doc(coords=[140.1, 35.7]))),
            ]:
                folder = Path(temp) / name
                with self.subTest(name=name), self.assertRaises(mod.CaptureError):
                    mod.capture_one(X, Y, folder, fetcher=fetcher, now=AT)
                self.assertFalse(folder.exists())

    def test_no_capture_inside_repo_or_without_parent(self):
        with self.assertRaisesRegex(mod.CaptureError, "OUTSIDE"):
            mod.capture_one(
                X, Y, mod.REPO_ROOT / "data-research" / "capture",
                fetcher=fake_fetch(), now=AT,
            )
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(mod.CaptureError, "parent"):
                mod.capture_one(
                    X, Y, Path(temp) / "no-parent" / "new",
                    fetcher=fake_fetch(), now=AT,
                )

    def test_timezone_and_no_approval_by_zero_feature(self):
        with TemporaryDirectory() as temp:
            out = Path(temp) / "evidence"
            with self.assertRaisesRegex(mod.CaptureError, "timezone"):
                mod.capture_one(X, Y, out, fetcher=fake_fetch(),
                                now=datetime(2026, 10, 26))
            empty = b'{"type":"FeatureCollection","features":[]}'
            report = mod.capture_one(X, Y, out, fetcher=fake_fetch(empty), now=AT)
            self.assertEqual(report["feature_count_tile_only"], 0)
            self.assertFalse(report["publishable"])

    def test_no_untrusted_ssl_or_autoredirect_flag(self):
        import inspect
        s = inspect.getsource(mod.fetch_direct_https)
        self.assertIn("ssl.create_default_context()", s)
        self.assertIn("NoRedirect()", s)
        self.assertNotIn("CERT_NONE", s)


if __name__ == "__main__":
    unittest.main()
