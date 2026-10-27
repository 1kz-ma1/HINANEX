"""Synthetic-only offline archive audit regression. No real OSM or network."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import importlib.util

MODULE = Path(__file__).resolve().parents[1] / "tools" / "inspect_osm_four_site_evidence.py"
spec = importlib.util.spec_from_file_location("osm_archive_audit_test_target", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
inspect_evidence_dir = mod.inspect_evidence_dir
EvidenceBlocked = mod.EvidenceBlocked
TARGETS, GSI_URL, OSM_URL = mod.TARGETS, mod.GSI_URL, mod.OSM_URL
_expected_query = mod._expected_query


def fixture(directory: Path, *, elements=None):
    if elements is None:
        elements = [{"type": "node", "id": 12, "lat": 35.725,
                     "lon": 139.899, "tags": {"entrance": "main"}}]
    features = [{"type": "Feature", "properties": {},
                 "geometry": {"type": "Point", "coordinates": [139.9, 35.7]}}
                for _ in range(800)]
    targets = []
    for idx, (name, coordinates) in TARGETS.items():
        features[idx] = {"type": "Feature", "properties": {
            "name": name, "address": "千葉県市川市合成地区", "disaster2": 1},
            "geometry": {"type": "Point", "coordinates": coordinates}}
        targets.append({"feature_index": idx, "gsi_name_raw": name,
                        "gsi_address_raw": "千葉県市川市合成地区",
                        "reference_coordinates_lon_lat_raw": coordinates,
                        "source_feature_key": GSI_URL + "#feature_index=" + str(idx),
                        "reference_point_is_navigation_endpoint": False})
    gsi = json.dumps({"type": "FeatureCollection", "features": features},
                     ensure_ascii=False).encode()
    osm = json.dumps({"version": 0.6, "elements": elements,
                      "osm3s": {"timestamp_osm_base": "2026-10-26T00:00:00Z"}}).encode()
    query = _expected_query()
    raw = {"gsi-skhb02-original.geojson": gsi,
           "osm-overpass-original.json": osm,
           "osm-query.overpassql": query}
    for name, blob in raw.items():
        (directory / name).write_bytes(blob)
    counts = {"node": 0, "way": 0, "relation": 0}
    for e in elements:
        if e.get("type") in counts:
            counts[e["type"]] += 1
    manifest = {
        "status": "OSM_FOUR_SITES_SOURCE_CANDIDATES_UNREVIEWED",
        "gsi_source_url": GSI_URL, "gsi_sha256": sha256(gsi).hexdigest(),
        "overpass_api_url": OSM_URL, "query_sha256": sha256(query).hexdigest(),
        "response_sha256": sha256(osm).hexdigest(),
        "response_bytes": len(osm), "response_element_count": len(elements),
        "osm_element_type_counts": counts,
        "osm_snapshot_time_claim_unverified": "2026-10-26T00:00:00Z",
        "capture_time_utc": "2026-10-27T00:00:00+00:00",
        "source_http_observation": {
            "status_observed": 200, "url_observed": OSM_URL,
            "content_type_observed": "application/json"},
        "radius_meters_per_site": 300, "four_target_points_unverified": targets,
        "osm_license": "ODbL-1.0",
        "osm_attribution": "© OpenStreetMap contributors",
        "osm_license_url": "https://www.openstreetmap.org/copyright",
        "gsi_usage_notice_url": "https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html",
        "candidate_to_official_facility_identity_verified": False,
        "candidate_geometry_officially_verified": False,
        "entrance_position_verified": False, "current_open_access_verified": False,
        "hazard_safety_verified": False, "human_c_approved": False,
        "navigation_allowed": False, "safe_destination_count_approved": 0,
        "no_elements_does_not_mean_no_facility": True,
    }
    (directory / "a_candidate_capture_manifest_UNREVIEWED.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (directory / "USAGE_NOTICE_AND_STATUS.txt").write_text(
        "© OpenStreetMap contributors ODbL 1.0; no approved navigation")
    return sha256(gsi).hexdigest()


class OSMArchiveAuditTests(unittest.TestCase):
    def update_manifest(self, folder, change):
        p = folder / "a_candidate_capture_manifest_UNREVIEWED.json"
        data = json.loads(p.read_text())
        change(data)
        p.write_text(json.dumps(data, ensure_ascii=False))

    def test_original_integrity_and_nonassociation(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = fixture(folder)
            result = inspect_evidence_dir(folder, expected_gsi_sha=digest)
            self.assertEqual(result["unassigned_candidate_count"], 1)
            self.assertIsNone(result["unassigned_candidates"][0]["associated_gsi_feature_index"])
            self.assertIsNone(result["unassigned_candidates"][0]["navigation_endpoint"])
            self.assertFalse(result["human_c_approved"])
            self.assertFalse(result["navigation_allowed"])
            self.assertFalse(result["may_publish_or_route"])

    def test_zero_evidence_is_not_no_facility(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = fixture(folder, elements=[])
            result = inspect_evidence_dir(folder, expected_gsi_sha=digest)
            self.assertEqual(result["unassigned_candidate_count"], 0)
            self.assertFalse(result["zero_elements_is_no_facility_evidence"])

    def test_locked_original_sha_not_assumed(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder)
            with self.assertRaisesRegex(EvidenceBlocked, "GSI_LOCKED_SHA"):
                inspect_evidence_dir(folder)

    def test_tampered_originals_block(self):
        for name in ("gsi-skhb02-original.geojson",
                     "osm-overpass-original.json", "osm-query.overpassql"):
            with self.subTest(name=name), TemporaryDirectory() as tmp:
                folder = Path(tmp)
                digest = fixture(folder)
                target = folder / name
                target.write_bytes(target.read_bytes() + b"X")
                with self.assertRaisesRegex(EvidenceBlocked, "MANIFEST_SHA"):
                    inspect_evidence_dir(folder, expected_gsi_sha=digest)

    def test_rehashed_widened_query_still_blocks(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = fixture(folder)
            target = folder / "osm-query.overpassql"
            target.write_bytes(target.read_bytes().replace(b"around:300", b"around:900"))
            self.update_manifest(folder, lambda m: m.__setitem__(
                "query_sha256", sha256(target.read_bytes()).hexdigest()))
            with self.assertRaisesRegex(EvidenceBlocked, "UNEXPECTED_OVERPASS"):
                inspect_evidence_dir(folder, expected_gsi_sha=digest)

    def test_approval_promotion_blocks(self):
        for key in ("navigation_allowed", "human_c_approved",
                    "candidate_to_official_facility_identity_verified"):
            with self.subTest(key=key), TemporaryDirectory() as tmp:
                folder = Path(tmp)
                digest = fixture(folder)
                self.update_manifest(folder, lambda m: m.__setitem__(key, True))
                with self.assertRaisesRegex(EvidenceBlocked, "ARCHIVE_APPROVAL"):
                    inspect_evidence_dir(folder, expected_gsi_sha=digest)

    def test_duplicate_osm_id_blocks(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = fixture(folder, elements=[{"type": "node", "id": 2},
                                               {"type": "node", "id": 2}])
            with self.assertRaisesRegex(EvidenceBlocked, "DUPLICATE"):
                inspect_evidence_dir(folder, expected_gsi_sha=digest)

    def test_false_http_observation_blocks(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = fixture(folder)
            self.update_manifest(folder, lambda m: m[
                "source_http_observation"].__setitem__("url_observed",
                                                       "https://example.invalid/"))
            with self.assertRaisesRegex(EvidenceBlocked, "SOURCE_HTTP"):
                inspect_evidence_dir(folder, expected_gsi_sha=digest)

    def test_extra_file_blocks(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = fixture(folder)
            (folder / "extra.txt").write_text("untrusted")
            with self.assertRaisesRegex(EvidenceBlocked, "UNEXPECTED_FILES"):
                inspect_evidence_dir(folder, expected_gsi_sha=digest)


if __name__ == "__main__":
    unittest.main()
