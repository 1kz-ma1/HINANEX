import json
import shutil
import tempfile
import unittest
from pathlib import Path

from deploy.build_staging import StagingBuildError, build_bundle


REGIONS = {
    "edogawa.json": ("13123", "東京都江戸川区"),
    "niigata.json": ("15100", "新潟県新潟市"),
    "nagoya.json": ("23100", "愛知県名古屋市"),
}


def payload(code: str, name: str) -> dict:
    return {
        "region": {"code": code, "name": name},
        "datasets": [],
        "assessments": [],
        "capabilities": [],
        "gaps": [],
        "recommendations": [],
        "meta": {"schema_version": "0.9"},
    }


class StagingBuildTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        (root / "frontend").mkdir(parents=True)
        (root / "frontend" / "index.html").write_text("frontend", encoding="utf-8")
        (root / "gis" / "gis").mkdir(parents=True)
        (root / "gis" / "gis" / "index.html").write_text("gis", encoding="utf-8")
        evidence = root / "validation" / "demo" / "2019_edogawa_evidence_cases.json"
        evidence.parent.mkdir(parents=True)
        shutil.copyfile(
            Path(__file__).resolve().parents[2] / "validation" / "demo" / evidence.name,
            evidence,
        )
        (root / "deploy").mkdir(parents=True)
        (root / "deploy" / "staging-index.html").write_text("staging", encoding="utf-8")
        output = root / "pipeline" / "data" / "output"
        output.mkdir(parents=True)
        for filename, (code, name) in REGIONS.items():
            (output / filename).write_text(
                json.dumps(payload(code, name), ensure_ascii=False),
                encoding="utf-8",
            )
        (output / "manifest.json").write_text("{}", encoding="utf-8")

    def test_builds_curated_static_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            target = root / "deploy" / "dist"

            build_bundle(root, target, run_pipeline=False)

            self.assertEqual((target / "index.html").read_text(encoding="utf-8"), "staging")
            self.assertTrue((target / "frontend" / "index.html").is_file())
            published = json.loads((target / "evidence" / "2019_edogawa_evidence_cases.json").read_text(encoding="utf-8"))
            self.assertFalse(published["historical_prediction_approved"])
            self.assertEqual([c["id"] for c in published["cases"]], ["trace", "abstain", "negative"])
            self.assertTrue((target / "gis" / "gis" / "index.html").is_file())
            for filename in REGIONS:
                self.assertTrue((target / "pipeline" / "data" / "output" / filename).is_file())
            self.assertTrue((target / "pipeline" / "data" / "output" / "manifest.json").is_file())
            meta = json.loads((target / "_staging.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["regions"]["edogawa.json"]["region_code"], "13123")

    def test_rejects_region_export_filename_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            bad = root / "pipeline" / "data" / "output" / "edogawa.json"
            bad.write_text(
                json.dumps(payload("15100", "新潟県新潟市"), ensure_ascii=False),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(StagingBuildError, "filename/region mismatch"):
                build_bundle(root, root / "deploy" / "dist", run_pipeline=False)

    def test_missing_or_promoted_c_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            evidence = root / "validation" / "demo" / "2019_edogawa_evidence_cases.json"
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["historical_prediction_approved"] = True
            evidence.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(StagingBuildError, "must remain unapproved"):
                build_bundle(root, root / "deploy" / "dist", run_pipeline=False)
            evidence.unlink()
            with self.assertRaisesRegex(StagingBuildError, "evidence manifest is missing"):
                build_bundle(root, root / "deploy" / "dist", run_pipeline=False)

    def test_fails_closed_when_required_export_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            (root / "pipeline" / "data" / "output" / "nagoya.json").unlink()

            with self.assertRaisesRegex(StagingBuildError, "Required RegionExport is missing"):
                build_bundle(root, root / "deploy" / "dist", run_pipeline=False)


if __name__ == "__main__":
    unittest.main()
