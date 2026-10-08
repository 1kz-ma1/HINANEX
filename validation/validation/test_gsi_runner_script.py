"""Verify that the opt-in local GSI PowerShell runner is parseable in CI.

This test does not run the script or contact official data servers.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "validation" / "scripts" / "Run-GsiFloodLocalAcceptance.ps1"
SEEDER = ROOT / "validation" / "scripts" / "Prepare-GsiDemoTiles.ps1"


class GsiRunnerSyntaxTests(unittest.TestCase):
    def test_script_exists_and_keeps_explicit_publish_flag(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[switch]$PublishPreview", text)
        self.assertIn("[Parameter(Mandatory = $true)]", text)
        self.assertIn("ExpectedSha256", text)
        self.assertIn("gsi_verified_tiles", text)
        self.assertIn("RegionCode", text)
        self.assertIn("10-", text)
        self.assertIn("will not replace it", text)
        self.assertIn("verify_gsi_catalog_acceptance.py", text)

    def test_explicit_demo_tile_seeding(self):
        text = SEEDER.read_text(encoding="utf-8")
        self.assertIn("[switch]$IncludeNeighbors", text)
        self.assertIn("[switch]$PublishPreview", text)
        self.assertIn("Run-GsiFloodLocalAcceptance.ps1", text)
        self.assertIn("Invoke-WebRequest", text)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell Core not installed in this test environment")
    def test_powershell_syntax_parse_only(self):
        path = str(SCRIPT).replace("'", "''")
        command = (
            "$ErrorActionPreference='Stop'; "
            "$null = [scriptblock]::Create("
            f"(Get-Content -Raw -Encoding UTF8 -LiteralPath '{path}'))"
        )
        result = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-NonInteractive", "-Command", command],
            text=True, capture_output=True, check=False, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
        # The seeder must be parseable, without initiating any real network calls.
        seed = str(SEEDER).replace("'", "''")
        seed_command = (
            "$ErrorActionPreference='Stop'; "
            "$null = [scriptblock]::Create("
            f"(Get-Content -Raw -Encoding UTF8 -LiteralPath '{seed}'))"
        )
        seed_result = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-NonInteractive", "-Command", seed_command],
            text=True, capture_output=True, check=False, timeout=20,
        )
        self.assertEqual(seed_result.returncode, 0, seed_result.stdout + "\n" + seed_result.stderr)


if __name__ == "__main__":
    unittest.main()
