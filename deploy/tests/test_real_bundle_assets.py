"""Deterministic smoke test for the REAL B/E staging asset tree.

Create only synthetic RegionExport contract stubs in a temporary checkout;
never use or overwrite the user's runtime pipeline outputs or C source evidence.
The real frontend, GIS, and landing source files are packaged unmodified.
"""

import json
import shutil
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from deploy.build_staging import build_bundle


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGIONS = {"edogawa.json": "13123", "niigata.json": "15100", "nagoya.json": "23100"}


class StaticAssets(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []

    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if tag == "script" and "src" in a:
            self.references.append(a["src"])
        if tag == "link" and "stylesheet" in a.get("rel", "").split() and "href" in a:
            self.references.append(a["href"])


class ActualStagingBundleSmokeTests(unittest.TestCase):
    def test_staging_copy_contains_all_local_html_script_and_css_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            root.mkdir()
            for source, destination in [
                (REPOSITORY_ROOT / "frontend", root / "frontend"),
                (REPOSITORY_ROOT / "gis" / "gis", root / "gis" / "gis"),
            ]:
                shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
            # Simulate the F03/P-02 branch before it is merged into main. These
            # synthetic QA filenames must never leak into Render's publish tree.
            # Never read or modify user-owned original F03 ZIP / runtime JSON.
            private_preview_fixture = {
                "prototypes/f03-storage-contract-qa/index.html": "<title>QA only</title>",
                "prototypes/f03-storage-contract-qa/app.js": "const qaOnly = true;",
                "prototypes/f03-storage-contract-qa/styles.css": "body {}",
                "docs/F03_P02_STORAGE_CONTRACT_QA_20261111.md": "QA report",
                "docs/evidence/f03-p02-20261111/real-http-chrome-390.png": "QA evidence",
                "tests/f03-storage-contract.test.js": "QA storage test",
                "tests/f03-storage-http-chrome.test.js": "QA Chrome test",
            }
            for relative, content in private_preview_fixture.items():
                fixture = root / "frontend" / relative
                fixture.parent.mkdir(parents=True, exist_ok=True)
                fixture.write_text(content, encoding="utf-8")
            # Simulate next F02 read-only consumer PR before it enters main.
            # This test proves no F02 UI, JS, local-only server, CLI, QA evidence
            # or tests are published by Render's whole-frontend copy.
            unpublished_f02_fixture = {
                "f02.html": "F02 private preview fixture",
                "f02.css": "F02 private preview fixture",
                "src/f02-page.js": "F02 private preview fixture",
                "src/f02-shelter-reference.js": "F02 private preview fixture",
                "scripts/check-f02-real-export.js": "F02 private preview fixture",
                "scripts/serve-f02-preview.cjs": "F02 private preview fixture",
                "docs/F02_REGION_EXPORT_CONSUMER_20261111.md": "F02 private preview fixture",
                "tests/f02-page-http-browser.test.cjs": "F02 private preview fixture",
                "tests/f02-preview-http.test.cjs": "F02 private preview fixture",
                "tests/f02-real-export-check.test.js": "F02 private preview fixture",
                "tests/f02-shelter-reference.test.js": "F02 private preview fixture",
            }
            for relative, content in unpublished_f02_fixture.items():
                fixture = root / "frontend" / relative
                fixture.parent.mkdir(parents=True, exist_ok=True)
                fixture.write_text(content, encoding="utf-8")
            # F05 local-only journey #371 exists on a separate Draft branch.
            # Seed its known paths and future nested assets to prove all remain
            # private even after source-only integration into main.
            unpublished_f05_fixture = {
                "prototypes/f05-flood-journey/index.html": "<title>F05 private</title>",
                "prototypes/f05-flood-journey/README.md": "F05 local-only guide",
                "prototypes/f05-flood-journey/assets/future.css": "body {}",
                "prototypes/f05-flood-journey/assets/deep/future.js": "const unpublished = true;",
                "src/f05-journey-model.js": "export const privateF05 = true;",
                "tests/f05-journey.test.js": "F05 private tests",
                "docs/F05_MINIMAL_JOURNEY_20261113.md": "F05 private QA",
            }
            for relative, content in unpublished_f05_fixture.items():
                fixture = root / "frontend" / relative
                fixture.parent.mkdir(parents=True, exist_ok=True)
                fixture.write_text(content, encoding="utf-8")
            evidence_file = root / "validation" / "demo" / "2019_edogawa_evidence_cases.json"
            evidence_file.parent.mkdir(parents=True)
            shutil.copyfile(
                REPOSITORY_ROOT / "validation" / "demo" / evidence_file.name,
                evidence_file,
            )
            (root / "deploy").mkdir()
            shutil.copyfile(REPOSITORY_ROOT / "deploy" / "staging-index.html",
                            root / "deploy" / "staging-index.html")

            output = root / "pipeline" / "data" / "output"
            output.mkdir(parents=True)
            for filename, code in REGIONS.items():
                payload = {
                    "region": {"code": code, "name": filename},
                    "datasets": [],
                    "assessments": [],
                    "capabilities": [],
                    "gaps": [],
                    "recommendations": [],
                    "meta": {"schema_version": "0.9"},
                }
                (output / filename).write_text(json.dumps(payload), encoding="utf-8")

            bundle = build_bundle(root, root / "deploy" / "dist", run_pipeline=False)
            for private_path in private_preview_fixture:
                self.assertTrue((root / "frontend" / private_path).is_file())
                self.assertFalse(
                    (bundle / "frontend" / private_path).exists(),
                    f"Unpublished F03 QA asset leaked to staging: {private_path}",
                )
            for private_path in unpublished_f02_fixture:
                self.assertTrue((root / "frontend" / private_path).is_file())
                self.assertFalse(
                    (bundle / "frontend" / private_path).exists(),
                    f"Unapproved F02 facility preview leaked: {private_path}",
                )
            for private_path in unpublished_f05_fixture:
                self.assertTrue((root / "frontend" / private_path).is_file())
                self.assertFalse(
                    (bundle / "frontend" / private_path).exists(),
                    f"Unapproved F05 local prototype leaked: {private_path}",
                )
            self.assertFalse(
                (bundle / "frontend" / "prototypes" / "f05-flood-journey").exists(),
                "F05 prototype directory must never appear in the public bundle",
            )
            self.assertTrue(
                (bundle / "frontend" / "prototypes" / "f02-shelter-explore" / "index.html").is_file(),
                "Approved synthetic F02 prototype must remain public",
            )
            for page in ("index.html", "frontend/index.html", "gis/gis/index.html"):
                html_path = bundle / page
                self.assertTrue(html_path.is_file(), page)
                parser = StaticAssets()
                parser.feed(html_path.read_text(encoding="utf-8"))
                if page == "index.html":
                    # Landing is deliberately standalone: inline CSS, no JS.
                    landing = html_path.read_text(encoding="utf-8")
                    self.assertIn('href="/frontend/"', landing)
                    self.assertIn('href="/gis/gis/"', landing)
                else:
                    self.assertTrue(parser.references, f"{page} must list its real CSS/JS dependencies")
                for ref in parser.references:
                    url = urlsplit(ref)
                    if url.scheme in ("http", "https"):
                        continue  # external Leaflet CDN is an explicit runtime dependency
                    self.assertFalse(url.scheme or url.netloc, f"{page}: unexpected asset origin {ref}")
                    if url.path.startswith("/"):
                        asset = bundle / unquote(url.path.lstrip("/"))
                    else:
                        asset = html_path.parent / unquote(url.path)
                    self.assertTrue(asset.resolve().is_relative_to(bundle.resolve()),
                                    f"{page}: dependency escapes staging bundle: {ref}")
                    self.assertTrue(asset.is_file(), f"{page}: missing packaged asset {ref}")

            for filename, code in REGIONS.items():
                published = json.loads((bundle / "pipeline" / "data" / "output" / filename)
                                       .read_text(encoding="utf-8"))
                self.assertEqual(published["region"]["code"], code)
            self.assertTrue((bundle / "evidence" / "2019_edogawa_evidence_cases.json").is_file())
            manifest = json.loads((bundle / "_staging.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["paths"]["frontend"], "/frontend/")
            self.assertEqual(manifest["paths"]["gis"], "/gis/gis/")

    def test_missing_real_frontend_script_fails_closed_at_smoke_gate(self):
        """Missing runtime JS must not silently produce a publishable bundle."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            root.mkdir()
            shutil.copytree(REPOSITORY_ROOT / "frontend", root / "frontend",
                            ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
            (root / "frontend" / "src" / "app.js").unlink()
            page = root / "frontend" / "index.html"
            parser = StaticAssets()
            parser.feed(page.read_text(encoding="utf-8"))
            missing_local = [
                ref for ref in parser.references
                if not urlsplit(ref).scheme and not urlsplit(ref).netloc
                and not (page.parent / urlsplit(ref).path).is_file()
            ]
            self.assertIn("./src/app.js", missing_local)


if __name__ == "__main__":
    unittest.main()
