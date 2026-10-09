"""Verify that the opt-in local GSI PowerShell runner is parseable in CI.

This test does not run the script or contact official data servers.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "validation" / "scripts" / "Run-GsiFloodLocalAcceptance.ps1"
SEEDER = ROOT / "validation" / "scripts" / "Prepare-GsiDemoTiles.ps1"
RECOVERY = ROOT / "validation" / "scripts" / "Publish-VerifiedGsiEvidence.ps1"


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
        self.assertIn("[switch]$NeighborsOnly", text)
        self.assertIn("Publish-VerifiedGsiEvidence.ps1", text)
        self.assertIn("verify_gsi_catalog_acceptance.py", RECOVERY.read_text(encoding="utf-8"))
        self.assertIn("Get-FileHash -LiteralPath $originOutput", text)
        self.assertIn("$tiles = @($tiles | Where-Object { -not $_.Origin })", text)


    def test_detached_checkout_probe_is_safe_in_source(self):
        runner = SCRIPT.read_text(encoding="utf-8")
        recovery = RECOVERY.read_text(encoding="utf-8")
        self.assertNotIn("git branch --show-current", runner.split("if ($PublishPreview) {", 1)[1])
        self.assertIn("git -C $repo rev-parse --abbrev-ref HEAD", runner)
        self.assertIn("IsNullOrWhiteSpace", runner)
        self.assertIn("git -C $repo rev-parse --abbrev-ref HEAD", recovery)
        self.assertIn("verify_gsi_catalog_acceptance.py", recovery)
        self.assertIn("if (-not $PublishPreview)", recovery)
        self.assertIn("refusing overwrite", recovery)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell Core required for explicit safety flags")
    def test_neighbors_only_requires_both_opt_in_flags(self):
        result = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-NonInteractive",
             "-File", str(SEEDER), "-Latitude", "35.7", "-Longitude", "139.9",
             "-NeighborsOnly"],
            text=True, capture_output=True, check=False, timeout=20,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NeighborsOnly requires -IncludeNeighbors and -PublishPreview",
                      result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell Core required for missing-origin test")
    def test_neighbors_only_refuses_unpublished_origin_before_download(self):
        result = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-NonInteractive",
             "-File", str(SEEDER), "-Latitude", "0.0", "-Longitude", "0.0",
             "-IncludeNeighbors", "-PublishPreview", "-NeighborsOnly"],
            text=True, capture_output=True, check=False, timeout=20,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Origin tile must already be published", result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("pwsh") and shutil.which("git"),
                         "PowerShell and Git required for detached worktree test")
    def test_git_detached_head_returns_literal_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", "-b", "main", tmp], check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "-C", tmp, "-c", "user.name=CI",
                            "-c", "user.email=ci@example.test", "commit",
                            "--allow-empty", "-q", "-m", "initial"], check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "-C", tmp, "checkout", "--detach", "-q"],
                           check=True, capture_output=True, text=True)
            quoted = tmp.replace("'", "''")
            code = (
                f"$repo = '{quoted}'; "
                "$refs = @(& git -C $repo rev-parse --abbrev-ref HEAD); "
                "if ($LASTEXITCODE -ne 0 -or $refs.Count -ne 1 -or "
                "[string]::IsNullOrWhiteSpace([string]$refs[0])) "
                "{ throw 'Ref probe failed'; }; "
                "if (([string]$refs[0]).Trim() -ne 'HEAD') { throw 'Not detached'; }"
            )
            result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive",
                                     "-Command", code], capture_output=True,
                                    text=True, check=False, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell Core not installed in this test environment")
    def test_powershell_syntax_parse_only(self):
        for script in (SCRIPT, SEEDER, RECOVERY):
            with self.subTest(script=script.name):
                path = str(script).replace("'", "''")
                command = (
                    "$ErrorActionPreference='Stop'; "
                    "$null = [scriptblock]::Create("
                    f"(Get-Content -Raw -Encoding UTF8 -LiteralPath '{path}'))"
                )
                result = subprocess.run(
                    [shutil.which("pwsh"), "-NoProfile", "-NonInteractive",
                     "-Command", command],
                    text=True, capture_output=True, check=False, timeout=20,
                )
                self.assertEqual(result.returncode, 0,
                                 result.stdout + "\n" + result.stderr)


if __name__ == "__main__":
    unittest.main()
