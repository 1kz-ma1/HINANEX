"""Guard GSI manual national emergency CSV capture from automatic release."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
WF=ROOT/".github/workflows/gsi-national-csv-manual-evidence.yml"

class CSVManualWorkflowGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=WF.read_text(encoding="utf-8")
    def test_no_automatic_trigger(self):
        self.assertIn("workflow_dispatch:",self.source)
        for forbidden in ("\n  push:","\n  pull_request:","\n  schedule:","\n  workflow_run:"):
            self.assertNotIn(forbidden,self.source)
    def test_no_write_or_bypass(self):
        self.assertIn("permissions:\n  contents: read",self.source)
        self.assertNotIn("contents: write",self.source)
        self.assertNotIn("id-token: write",self.source)
        self.assertIn('if [ "$ACCEPTED" != "true" ]',self.source)
        self.assertIn("exit 1",self.source)
    def test_unreviewed_source_and_short_retention(self):
        self.assertIn("capture_gsi_emergency_csv_original.py",self.source)
        self.assertIn("--acknowledged-gsi-terms",self.source)
        self.assertIn("USAGE_NOTICE_AND_STATUS.txt",self.source)
        self.assertIn("retention-days: 3",self.source)
        self.assertIn("GSI-national-emergency-CSV-UNREVIEWED",self.source)
        self.assertNotIn("github.event.schedule",self.source)
