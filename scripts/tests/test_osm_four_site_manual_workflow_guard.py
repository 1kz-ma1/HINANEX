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

    def test_fixed_gsi_artifact_reused_not_reacquired(self):
        self.assertIn("actions/download-artifact@v4",self.raw)
        self.assertIn("run-id: 40258746945",self.raw)
        self.assertIn("GSI-skhb02-UNREVIEWED-z10-909-403",self.raw)
        self.assertIn("capture_osm_four_site_candidates.py",self.raw)
        self.assertNotIn("capture_gsi_skhb02_original.py",self.raw)
        self.assertNotIn("github.event.schedule",self.raw)

    def test_read_only_no_recommendations(self):
        self.assertIn("permissions:\n  contents: read\n  actions: read",self.raw)
        self.assertNotIn("contents: write",self.raw)
        self.assertNotIn("id-token: write",self.raw)
        self.assertIn("'navigation_allowed',",self.raw)
        self.assertIn("safe_destination_count_approved",self.raw)
        self.assertIn("retention-days: 3",self.raw)
        self.assertIn("ODbL-1.0",self.raw)
