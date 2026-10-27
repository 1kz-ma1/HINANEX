"""Prohibit background source collection, consent bypass and unsafe approval."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
WORKFLOW=ROOT/".github"/"workflows"/"osm-ichikawa-four-site-manual-evidence.yml"


class ManualOSMCaptureGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=WORKFLOW.read_text(encoding="utf-8")

    def test_human_trigger_only(self):
        self.assertIn("workflow_dispatch:",self.raw)
        for name in ("\n  push:","\n  schedule:","\n  pull_request:","\n  workflow_run:"):
            self.assertNotIn(name,self.raw)
        self.assertIn("OSM_OK",self.raw)
        self.assertIn("GSI_OK",self.raw)
        self.assertIn('if [ "$OSM_OK" != "true" ] || [ "$GSI_OK" != "true" ]',self.raw)

    def test_default_branch_only_for_manual_source_capture(self):
        self.assertIn('if [ "$DISPATCH_REF" != "refs/heads/main" ]', self.raw)
        self.assertIn("DISPATCH_REF: ${{ github.ref }}", self.raw)

    def test_fixed_source_sha_and_four_indices_checked_independently(self):
        self.assertIn("assert info['gsi_sha256'] == 'cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84'", self.raw)
        self.assertIn("== [571, 639, 682, 707]", self.raw)

    def test_fixed_gsi_artifact_reused_not_reacquired(self):
        self.assertIn("actions/download-artifact@v4",self.raw)
        self.assertIn("run-id: 40258746945",self.raw)
        self.assertIn("GSI-skhb02-UNREVIEWED-z10-909-403",self.raw)
        self.assertIn("capture_osm_four_site_candidates.py",self.raw)
        self.assertNotIn("capture_gsi_skhb02_original.py",self.raw)
        self.assertNotIn("github.event.schedule",self.raw)

    def test_independent_archive_audit_precedes_any_upload(self):
        self.assertIn("inspect_osm_four_site_evidence.py", self.raw)
        self.assertIn("a_source_audit_UNREVIEWED.json", self.raw)
        self.assertLess(
            self.raw.index("Independently audit the five captured originals"),
            self.raw.index("Upload short-lived GSI/OSM research original bytes"))
        self.assertLess(
            self.raw.index("Independently audit the five captured originals"),
            self.raw.index("Upload independent UNREVIEWED source audit"))
        self.assertIn("INDEPENDENT_AUDIT_PASSED", self.raw)
        self.assertIn("candidate['associated_gsi_feature_index'] is None", self.raw)
        self.assertIn("report['may_publish_or_route'] is False", self.raw)

    def test_audit_is_outside_original_directory_and_manual_only(self):
        self.assertIn('mkdir -p "$AUDIT"', self.raw)
        self.assertIn('--evidence-dir "$OUT" > "$AUDIT/a_source_audit_UNREVIEWED.json"', self.raw)
        self.assertIn("OSM-Ichikawa-4-sites-UNREVIEWED-AUDIT", self.raw)
        self.assertEqual(self.raw.count("retention-days: 3"), 2)
        self.assertIn("run-id: 40258746945", self.raw)
        self.assertIn("workflow_dispatch:", self.raw)
        self.assertNotIn("\\n  schedule:", self.raw)

    def test_read_only_no_recommendations(self):
        self.assertIn("permissions:\n  contents: read\n  actions: read",self.raw)
        self.assertNotIn("contents: write",self.raw)
        self.assertNotIn("id-token: write",self.raw)
        self.assertIn("'navigation_allowed',",self.raw)
        self.assertIn("safe_destination_count_approved",self.raw)
        self.assertIn("retention-days: 3",self.raw)
        self.assertIn("ODbL-1.0",self.raw)
