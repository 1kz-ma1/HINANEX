"""Static safety contract of the human-triggered GSI capture workflow.

Checks prevent accidental background collection or scope/approval escalation.
These are structural guardrails, not a substitute for a workflow run.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/gsi-skhb02-manual-evidence.yml"


class ManualCaptureWorkflowContract(unittest.TestCase):
    def setUp(self):
        self.raw = WORKFLOW.read_text(encoding="utf-8")

    def test_only_manual_dispatch_not_automatic(self):
        self.assertIn("workflow_dispatch:", self.raw)
        for trigger in ("\n  push:", "\n  pull_request:",
                        "\n  schedule:", "\n  workflow_run:"):
            self.assertNotIn(trigger, self.raw)
        self.assertIn("acknowledged_gsi_terms == true", self.raw)

    def test_no_write_permissions_or_self_approval(self):
        self.assertIn("permissions:\n  contents: read", self.raw)
        self.assertNotIn("contents: write", self.raw)
        self.assertNotIn("id-token: write", self.raw)
        self.assertNotIn("publishable: true", self.raw)
        self.assertNotIn("independent_c_approved: true", self.raw)
        self.assertIn("published_for_disaster_use') is not False", self.raw)

    def test_explicit_fixed_official_url_and_unreviewed_outputs(self):
        self.assertIn("cyberjapandata.gsi.go.jp/xyz/skhb02/10/", self.raw)
        self.assertIn("capture_gsi_skhb02_original.py", self.raw)
        self.assertIn("verify_gsi_skhb02_capture_chain.py", self.raw)
        self.assertIn("capture_manifest_UNREVIEWED.json", self.raw)
        self.assertIn("c_capture_chain_UNAPPROVED.json", self.raw)
        self.assertIn("USAGE_NOTICE_AND_STATUS.txt", self.raw)
        self.assertIn("retention-days: 3", self.raw)


if __name__ == "__main__":
    unittest.main()
