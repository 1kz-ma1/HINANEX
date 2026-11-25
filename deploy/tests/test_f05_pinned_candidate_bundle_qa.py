"""QA ONLY: actual pinned candidate bytes, offline synthetic export bundle.
Never merge this test branch; no production deployment or official data fetch.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from deploy import build_staging as staging

ROOT = Path(__file__).resolve().parents[2]
GUARD = "fe6575b0d1528f6994c483b71b06f17e140b764c"
B1_REF = "469224f341669453293ff6d3f1de216f5806b828"
MJ_REF = "03d8f92a1c776664765dc898acdefa94730cc040"
B2_REF = "56c340f98578ab5ee4ccffee5fd81c057593e4d1"
B1 = {
    "docs/F05_MINIMAL_JOURNEY_20261113.md": "13da247b199f709f8d872c5e6d390a3fa9684fda",
    "prototypes/f05-flood-journey/README.md": "7269f01766b35d1b44155015e02c31e93e709125",
    "prototypes/f05-flood-journey/index.html": "fb32b71d5ce457ccbdb34d8281c2babdbcab677d",
    "src/f05-journey-model.js": "4673c0491b580a71a43cbebc13b5b146fd702256",
    "tests/f05-journey-http-browser.test.cjs": "690e1580b64fad4da17afa8b8fe42f08cef3e7de",
    "tests/f05-journey.test.js": "b4cd8095804c4d2338cd63e7d0ac4cdaf19fbfa6",
}
MJ = {"prototypes/f05-flood-journey/mj01-shell/" + name: sha for name, sha in {
    "README.md": "5bfa27408f5b2a7057a3e3327b15a92f9ded2c08",
    "app.js": "93349878da6d79baca5d03d4fad2a1dcea5b52cd",
    "browser-http.test.cjs": "43057c10e0575788e9997653d8f52bae91020eee",
    "fixtures.js": "e09cc380a74aa5b6eb949644e31e5ad683a2d7d1",
    "index.html": "e398d37719b751b276aea16aa8ba5377acef60ec",
    "model.js": "28439299b975774fdc706a4615c14bf0c118e737",
    "model.test.js": "189bfba04e7d677d81c62fd51bbe91e28c3e7e6c",
}.items()}
B2 = {"prototypes/f05-flood-journey/b2-compare/" + name: sha for name, sha in {
    "README.md": "cad2475db63be2df320a8cced7f5432870b72e65",
    "browser-http.test.cjs": "d31bf060bdb3cdb82499636c0799166961b72077",
    "fixtures.js": "ba2c04b0d747637522c8be75af8fc7402176d9c8",
    "index.html": "79913c52355b394bf6df93c7dc23d04b54075195",
    "model.js": "0c2187f7e855d6c346055531005d4675215883fe",
    "model.test.js": "2f944acfb074409a906e61a1fa813b478e9b499d",
}.items()}
LEAK = "tests/f05-journey-http-browser.test.cjs"
REGIONS = {"edogawa.json": "13123", "niigata.json": "15100", "nagoya.json": "23100"}


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class PinnedRealCandidateBundleQA(unittest.TestCase):
    def pinned(self, ref, paths):
        result = {}
        for relative, expected in paths.items():
            # checkout fetch-depth:0 includes source branches. Missing object fails,
            # no network or synthetic replacement.
            data = subprocess.run(
                ["git", "show", ref + ":frontend/" + relative],
                cwd=ROOT, check=True, capture_output=True, timeout=15
            ).stdout
            self.assertEqual(blob_sha(data), expected, relative)
            result[relative] = data
        return result

    def require_sources(self, root, expected):
        for relative, data in expected.items():
            path = root / "frontend" / relative
            self.assertTrue(path.is_file(), "missing candidate: " + relative)
            self.assertEqual(path.read_bytes(), data, relative)

    def require_excluded(self, bundle, expected):
        for relative in expected:
            self.assertFalse((bundle / "frontend" / relative).exists(), relative)
        self.assertFalse((bundle / "frontend/prototypes/f05-flood-journey").exists())

    def build(self, root, output):
        return staging.build_bundle(root, output, run_pipeline=False, publish_official_gsi=False)

    def test_actual_candidate_bundle_and_negative_controls(self):
        self.assertEqual(blob_sha((ROOT / "deploy/build_staging.py").read_bytes()), GUARD)
        self.assertEqual((len(B1), len(MJ), len(B2)), (6, 7, 6))
        b1, mj, b2 = self.pinned(B1_REF, B1), self.pinned(MJ_REF, MJ), self.pinned(B2_REF, B2)
        with TemporaryDirectory() as scratch:
            tmp = Path(scratch)
            root = tmp / "checkout"
            root.mkdir()
            for path in ("frontend", "gis/gis"):
                shutil.copytree(ROOT / path, root / path,
                                ignore=shutil.ignore_patterns("node_modules", "__pycache__", ".git"))
            for path in ("deploy/staging-index.html", "validation/demo/2019_edogawa_evidence_cases.json"):
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / path, destination)
            output = root / "pipeline/data/output"
            output.mkdir(parents=True)
            for name, region in REGIONS.items():
                (output / name).write_text(json.dumps({
                    "region": {"code": region, "name": name}, "datasets": [],
                    "assessments": [], "capabilities": [], "gaps": [],
                    "recommendations": [], "meta": {"schema_version": "0.9"}
                }), encoding="utf-8")
            self.require_sources(root, b2)
            self.assertTrue(all(not (root / "frontend" / p).exists() for p in b1 | mj))
            baseline = self.build(root, tmp / "baseline")
            self.require_excluded(baseline, b2)
            public = inventory(baseline)
            for path in ("index.html", "frontend/index.html", "frontend/src/app.js",
                         "frontend/styles.css", "frontend/prototypes/f02-shelter-explore/index.html",
                         "gis/gis/index.html"):
                self.assertIn(path, public)
            for label, candidate in (("B1", b1), ("MJ01", mj), ("B1+MJ01", b1 | mj)):
                with self.subTest(candidate=label):
                    for relative, data in candidate.items():
                        path = root / "frontend" / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(data)
                    expected = b2 | candidate
                    self.require_sources(root, expected)
                    bundle = self.build(root, tmp / "candidate")
                    self.require_excluded(bundle, expected)
                    self.assertEqual(inventory(bundle), public)
                    print(f"F05_REAL_CANDIDATE_BUNDLE {label} private={len(expected)} public={len(public)} PASS")
                    if LEAK in candidate:
                        path = root / "frontend" / LEAK
                        path.unlink()
                        with self.assertRaisesRegex(AssertionError, "missing candidate"):
                            self.require_sources(root, expected)
                        path.write_bytes(candidate[LEAK])
                        with patch.object(staging, "UNPUBLISHED_PREVIEW_PATHS",
                                          staging.UNPUBLISHED_PREVIEW_PATHS - {LEAK}):
                            negative = self.build(root, tmp / "negative")
                        self.assertEqual((negative / "frontend" / LEAK).read_bytes(), candidate[LEAK])
                        with self.assertRaisesRegex(AssertionError, LEAK.replace(".", r"\.")):
                            self.require_excluded(negative, expected)
                        print("F05_REAL_CANDIDATE_NEGATIVE missing-source and omitted-registration PASS")
                    for relative in candidate:
                        (root / "frontend" / relative).unlink()
            self.require_sources(root, b2)


if __name__ == "__main__":
    unittest.main()
