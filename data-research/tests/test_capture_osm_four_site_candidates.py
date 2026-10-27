"""Synthetic original-only OSM four-site capture tests. No network calls."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "capture_osm_four_site_candidates.py"
spec = importlib.util.spec_from_file_location("osm_four_capture_tests", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def source():
    features = [{"type": "Feature", "properties": {"name": "NOT A TARGET"},
                 "geometry": {"type": "Point", "coordinates": [139.91, 35.73]}}
                for _ in range(800)]
    sample = {
        571: [139.899193, 35.725904],
        639: [139.912857, 35.739064],
        682: [139.910732, 35.718787],
        707: [139.902054, 35.744282],
    }
    for idx, xy in sample.items():
        features[idx] = {"type": "Feature", "properties": {
            "name": mod.TARGETS[idx], "address": "千葉県市川市合成地区", "disaster2": 1},
            "geometry": {"type": "Point", "coordinates": xy}}
    return json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False).encode("utf-8")


def response():
    return json.dumps({
        "version": 0.6, "generator": "Overpass API",
        "osm3s": {"timestamp_osm_base": "2026-10-26T00:00:00Z"},
        "elements": [{"type": "node", "id": 12, "lat": 35.725, "lon": 139.899,
                      "tags": {"entrance": "main"}}],
    }).encode()


def fake(q):
    return response(), {"status_observed": 200, "url_observed": mod.OSM_ENDPOINT,
                        "content_type_observed": "application/json"}


class CaptureTests(unittest.TestCase):
    def test_four_points_one_bounded_query(self):
        raw = source()
        rows = mod.inspect_gsi_original(raw, expected_sha=sha256(raw).hexdigest())
        self.assertEqual([r["feature_index"] for r in rows], [571, 639, 682, 707])
        query = mod.build_query(rows)
        self.assertEqual(query.count('["entrance"]'), 4)
        self.assertEqual(query.count("around:300"), 24)
        self.assertTrue(query.endswith("out body geom;\n"))
        self.assertIn("35.725904,139.899193", query)
        self.assertIn("[timeout:35]", query)

    def test_no_automatic_approval_on_success(self):
        raw = source()
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "four"
            record = mod.capture_osm_candidates(
                raw, target, acknowledged_osm=True, acknowledged_gsi=True,
                expected_gsi_sha=sha256(raw).hexdigest(), fetcher=fake,
                observed_at=datetime(2026, 10, 27, tzinfo=timezone.utc),
            )
            self.assertEqual(record["response_element_count"], 1)
            self.assertEqual(record["osm_element_type_counts"]["node"], 1)
            self.assertFalse(record["candidate_to_official_facility_identity_verified"])
            self.assertFalse(record["entrance_position_verified"])
            self.assertFalse(record["navigation_allowed"])
            self.assertTrue((target / "osm-overpass-original.json").exists())
            self.assertTrue((target / "gsi-skhb02-original.geojson").exists())
            self.assertEqual(record["response_sha256"], sha256(response()).hexdigest())
            with self.assertRaisesRegex(mod.EvidenceBlocked, "OUTPUT_ALREADY"):
                mod.capture_osm_candidates(raw, target, acknowledged_osm=True,
                    acknowledged_gsi=True, expected_gsi_sha=sha256(raw).hexdigest(),
                    fetcher=fake)

    def test_notice_and_original_sha_are_required(self):
        raw = source()
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "sample"
            with self.assertRaisesRegex(mod.EvidenceBlocked, "ACKNOWLEDGMENTS"):
                mod.capture_osm_candidates(raw, dest, acknowledged_osm=False,
                    acknowledged_gsi=True, fetcher=fake)
            with self.assertRaisesRegex(mod.EvidenceBlocked, "SHA256"):
                mod.inspect_gsi_original(raw)

    def test_source_identity_wrong_name_or_hazard_is_blocked(self):
        raw = source()
        doc = json.loads(raw)
        doc["features"][571]["properties"]["name"] = "INJECTED"
        altered = json.dumps(doc, ensure_ascii=False).encode()
        with self.assertRaisesRegex(mod.EvidenceBlocked, "IDENTITY"):
            mod.inspect_gsi_original(altered, expected_sha=sha256(altered).hexdigest())
        doc = json.loads(raw)
        doc["features"][707]["properties"]["disaster2"] = 0
        altered = json.dumps(doc, ensure_ascii=False).encode()
        with self.assertRaisesRegex(mod.EvidenceBlocked, "IDENTITY"):
            mod.inspect_gsi_original(altered, expected_sha=sha256(altered).hexdigest())

    def test_fail_closed_for_bad_response_and_no_artifact(self):
        raw = source()
        for reply in (b"<html>Bad Gateway</html>", b"{}", json.dumps({
            "elements": [], "remark": "runtime error"}).encode()):
            with TemporaryDirectory() as tmp:
                def bad(_):
                    return reply, {"status_observed": 200, "url_observed": mod.OSM_ENDPOINT}
                target = Path(tmp) / "four"
                with self.assertRaises(mod.EvidenceBlocked):
                    mod.capture_osm_candidates(raw, target, acknowledged_osm=True,
                        acknowledged_gsi=True, expected_gsi_sha=sha256(raw).hexdigest(),
                        fetcher=bad)
                self.assertFalse(target.exists())

    def test_empty_query_response_is_unknown_not_absence(self):
        v = mod.inspect_osm_response(b'{"elements":[]}')
        self.assertEqual(v["element_count"], 0)
        self.assertEqual(v["element_type_counts"], {"node":0,"way":0,"relation":0})

    def test_no_tls_bypass_or_retries(self):
        import inspect
        text = inspect.getsource(mod.fetch_once)
        self.assertIn("ssl.create_default_context()", text)
        self.assertIn("NoRedirect()", text)
        self.assertNotIn("CERT_NONE", text)
        self.assertNotIn("sleep(", text)

    def test_private_git_directory_blocked(self):
        with self.assertRaisesRegex(mod.EvidenceBlocked, "CANNOT_BE_WRITTEN_TO_GIT"):
            mod.capture_osm_candidates(source(), mod.REPO_ROOT / "data-research"
                / "raw_capture", acknowledged_osm=True, acknowledged_gsi=True,
                fetcher=fake, expected_gsi_sha=sha256(source()).hexdigest())
