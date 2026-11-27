"""Protect private F05 candidates independently of the builder's exclusion list.

Inventory is from #371 (469224f), #483 (03d8f92) and existing B2 on main.
Candidate paths absent from this Shared checkout use synthetic sentinels; actual
candidate checkouts and LIVE HTTP acceptance remain separate verification gates.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from deploy import build_staging as staging


B1_PATHS = (
    "docs/F05_MINIMAL_JOURNEY_20261113.md",
    "prototypes/f05-flood-journey/README.md",
    "prototypes/f05-flood-journey/index.html",
    "src/f05-journey-model.js",
    "tests/f05-journey.test.js",
    "tests/f05-journey-http-browser.test.cjs",
)
B2_PATHS = tuple("prototypes/f05-flood-journey/b2-compare/" + name for name in (
    "README.md", "index.html", "fixtures.js", "model.js", "model.test.js",
    "browser-http.test.cjs",
))
MJ01_PATHS = tuple("prototypes/f05-flood-journey/mj01-shell/" + name for name in (
    "README.md", "index.html", "fixtures.js", "model.js", "app.js",
    "model.test.js", "browser-http.test.cjs",
))
OTHER_PRIVATE_PATHS = (
    "f02.html", "f02.css", "src/f02-page.js", "src/f02-shelter-reference.js",
    "scripts/check-f02-real-export.js", "scripts/serve-f02-preview.cjs",
    "docs/F02_REGION_EXPORT_CONSUMER_20261111.md",
    "tests/f02-page-http-browser.test.cjs", "tests/f02-preview-http.test.cjs",
    "tests/f02-real-export-check.test.js", "tests/f02-shelter-reference.test.js",
    "prototypes/f03-storage-contract-qa/nested/index.html",
    "docs/F03_P02_STORAGE_CONTRACT_QA_20261111.md",
    "docs/evidence/f03-p02-20261111/nested/evidence.json",
    "tests/f03-storage-contract.test.js", "tests/f03-storage-http-chrome.test.js",
    "prototypes/f09-preparedness/nested/future.js",
    "docs/F09_PREPAREDNESS_CHECKLIST_PROTOTYPE_20261117.md",
    "tests/f09-preparedness.test.js", "tests/f09-preparedness-browser.cjs",
    "prototypes/f17-training/nested/future.js",
)
FUTURE_PATHS = (
    "prototypes/f05-flood-journey/b2-compare/nested/future.js",
    "prototypes/f05-flood-journey/mj01-shell/nested/future.js",
)
PRIVATE_PATHS = B1_PATHS + B2_PATHS + MJ01_PATHS + OTHER_PRIVATE_PATHS + FUTURE_PATHS
PUBLIC_PATHS = (
    "index.html", "styles.css", "src/app.js",
    "prototypes/f02-shelter-explore/index.html",
    "prototypes/f05-flood-journey-public-control/index.html",
    "tests/f05-journey-http-browser.test.cjs.control",
)
MISSING_GUARD = "tests/f05-journey-http-browser.test.cjs"


def write_fixture(source, paths):
    for relative in paths:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("synthetic sentinel: " + relative).encode("utf-8"))


class F05UnpublishedBundleTests(unittest.TestCase):
    def assert_private_absent(self, destination):
        for relative in PRIVATE_PATHS:
            self.assertFalse((destination / relative).exists(), relative)

    def test_private_inventory_excluded_and_public_bytes_unchanged(self):
        with TemporaryDirectory() as scratch:
            source = Path(scratch) / "frontend"
            destination = Path(scratch) / "dist" / "frontend"
            write_fixture(source, PRIVATE_PATHS + PUBLIC_PATHS)
            staging._copy_public_frontend(source, destination)
            self.assert_private_absent(destination)
            self.assertFalse((destination / "prototypes/f05-flood-journey").exists())
            for relative in PUBLIC_PATHS:
                self.assertEqual((destination / relative).read_bytes(),
                                 (source / relative).read_bytes(), relative)
            self.assertTrue(all((source / p).is_file() for p in PRIVATE_PATHS))

    def test_inventory_detects_missing_registration(self):
        with TemporaryDirectory() as scratch:
            source = Path(scratch) / "frontend"
            destination = Path(scratch) / "dist" / "frontend"
            write_fixture(source, PRIVATE_PATHS + PUBLIC_PATHS)
            # Simulate forgetting the precise QA path. Builder's own post-copy
            # check only knows registered paths; independent inventory must fail.
            self.assertIn(MISSING_GUARD, staging.UNPUBLISHED_PREVIEW_PATHS)
            with patch.object(staging, "UNPUBLISHED_PREVIEW_PATHS",
                              staging.UNPUBLISHED_PREVIEW_PATHS - {MISSING_GUARD}):
                staging._copy_public_frontend(source, destination)
            self.assertTrue((destination / MISSING_GUARD).is_file())
            with self.assertRaisesRegex(AssertionError, MISSING_GUARD):
                self.assert_private_absent(destination)

    def test_registered_leak_aborts_copy(self):
        with TemporaryDirectory() as scratch:
            source = Path(scratch) / "frontend"
            destination = Path(scratch) / "dist" / "frontend"
            write_fixture(source, (MISSING_GUARD,))

            def leaking_copytree(src, dst, **kwargs):
                write_fixture(dst, (MISSING_GUARD,))

            with patch.object(staging.shutil, "copytree", side_effect=leaking_copytree):
                with self.assertRaisesRegex(staging.StagingBuildError, MISSING_GUARD):
                    staging._copy_public_frontend(source, destination)

    def test_existing_b2_and_available_candidate_source_bytes_excluded(self):
        # Shared branch has B2 on main. B1/MJ01 may not yet exist: never pretend
        # the absent candidate was executed. When integrated, actual files are
        # automatically covered in addition to the independent inventory test.
        checkout = Path(__file__).resolve().parents[2] / "frontend"
        with TemporaryDirectory() as scratch:
            source = Path(scratch) / "frontend"
            destination = Path(scratch) / "dist" / "frontend"
            for relative in B2_PATHS:
                self.assertTrue((checkout / relative).is_file(), relative)
            for relative in B1_PATHS + B2_PATHS + MJ01_PATHS:
                original = checkout / relative
                if original.is_file():
                    copy = source / relative
                    copy.parent.mkdir(parents=True, exist_ok=True)
                    copy.write_bytes(original.read_bytes())
            write_fixture(source, PUBLIC_PATHS + FUTURE_PATHS)
            staging._copy_public_frontend(source, destination)
            self.assert_private_absent(destination)
            for relative in PUBLIC_PATHS:
                self.assertEqual((destination / relative).read_bytes(),
                                 (source / relative).read_bytes(), relative)


if __name__ == "__main__":
    unittest.main()
