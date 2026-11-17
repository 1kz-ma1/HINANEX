"""F09 must stay inaccessible in public Render bundles, even after source-only integration.

The real public builder deliberately copies frontend/** broadly. Explicitly protect
F09's local-only prototype, unit/browser tests, and its unpublished specification.
This test does not touch real RegionExport or disaster data.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deploy.build_staging import _copy_public_frontend, UNPUBLISHED_F09_PREVIEW_PATHS


class F09UnpublishedBundleTests(unittest.TestCase):
    def test_f09_prototype_and_qa_are_not_copied(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            src = root / "frontend"
            dst = root / "dist" / "frontend"
            fixtures = {
                "index.html": "<html>Existing public frontend</html>",
                "prototypes/f02-shelter-explore/index.html": "<html>Existing public synthetic F02</html>",
                "prototypes/f09-preparedness/index.html": "<html>F09 NOT PUBLIC</html>",
                "prototypes/f09-preparedness/model.js": "F09 NOT PUBLIC",
                "prototypes/f09-preparedness/nested/future.js": "F09 NOT PUBLIC",
                "docs/F09_PREPAREDNESS_CHECKLIST_PROTOTYPE_20261117.md": "F09 private spec",
                "tests/f09-preparedness.test.js": "F09 test",
                "tests/f09-preparedness-browser.cjs": "F09 browser test",
            }
            for relative, contents in fixtures.items():
                path = src / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, encoding="utf-8")
            _copy_public_frontend(src, dst)

            self.assertTrue((dst / "index.html").exists())
            self.assertTrue((dst / "prototypes/f02-shelter-explore/index.html").exists())
            self.assertFalse((dst / "prototypes/f09-preparedness").exists())
            for private in UNPUBLISHED_F09_PREVIEW_PATHS:
                self.assertFalse((dst / private).exists(), private)

    def test_f09_paths_match_intended_private_scope(self):
        self.assertEqual(UNPUBLISHED_F09_PREVIEW_PATHS, frozenset({
            "prototypes/f09-preparedness",
            "docs/F09_PREPAREDNESS_CHECKLIST_PROTOTYPE_20261117.md",
            "tests/f09-preparedness.test.js",
            "tests/f09-preparedness-browser.cjs",
        }))


if __name__ == "__main__":
    unittest.main()
