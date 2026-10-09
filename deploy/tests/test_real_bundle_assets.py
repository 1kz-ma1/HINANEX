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
            for page in ("index.html", "frontend/index.html", "gis/gis/index.html"):
                html_path = bundle / page
                self.assertTrue(html_path.is_file(), page)
                parser = StaticAssets()
                parser.feed(html_path.read_text(encoding="utf-8"))
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
