"""Ensure local-only F17 is never exposed by the actual Render frontend copier."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deploy.build_staging import _copy_public_frontend, UNPUBLISHED_F17_PREVIEW_PATHS


class F17UnpublishedBundleTests(unittest.TestCase):
    def test_f17_is_excluded_with_future_nested_assets(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / "frontend"
            dest = root / "dist/frontend"
            files = {
                "index.html": "<p>existing public UI</p>",
                "prototypes/f02-shelter-explore/index.html": "existing public synthetic page",
                "prototypes/f17-training/index.html": "F17 PRIVATE",
                "prototypes/f17-training/app.js": "F17 PRIVATE",
                "prototypes/f17-training/model.js": "F17 PRIVATE",
                "prototypes/f17-training/browser-http.test.cjs": "F17 PRIVATE QA",
                "prototypes/f17-training/deeper/future-extra.js": "F17 FUTURE PRIVATE",
            }
            for relative, data in files.items():
                target = src / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(data, encoding="utf-8")
            _copy_public_frontend(src, dest)
            self.assertTrue((dest / "index.html").exists())
            self.assertTrue((dest / "prototypes/f02-shelter-explore/index.html").exists())
            self.assertFalse((dest / "prototypes/f17-training").exists())
            for relative in UNPUBLISHED_F17_PREVIEW_PATHS:
                self.assertFalse((dest / relative).exists(), relative)

    def test_exclusion_is_exactly_the_f17_subtree(self):
        self.assertEqual(UNPUBLISHED_F17_PREVIEW_PATHS, frozenset({
            "prototypes/f17-training",
        }))


if __name__ == "__main__":
    unittest.main()
