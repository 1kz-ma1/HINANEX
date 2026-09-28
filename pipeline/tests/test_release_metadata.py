import unittest
from pathlib import Path

from src.hinanex.models.assessment import DatasetAssessment
from src.hinanex.models.capability import CapabilityAssessment
from src.hinanex.models.export import ExportMeta
from src.hinanex.models.gap import GapAnalysis
from src.hinanex.models.integration import ValidationManifest
from src.hinanex.version import (
    ASSESSMENT_ENGINE_VERSION,
    CAPABILITY_ENGINE_VERSION,
    CONTRACT_SCHEMA_VERSION,
    GAP_ENGINE_VERSION,
    MANIFEST_VERSION,
    PROJECT_RELEASE,
)


class ReleaseMetadataTests(unittest.TestCase):
    def test_release_label_is_v1_d_mvp(self):
        self.assertEqual(PROJECT_RELEASE, "v1.0-D-MVP")

    def test_model_defaults_follow_central_version_metadata(self):
        self.assertEqual(
            ExportMeta.model_fields["schema_version"].default,
            CONTRACT_SCHEMA_VERSION,
        )
        self.assertEqual(
            DatasetAssessment.model_fields["assessment_version"].default,
            ASSESSMENT_ENGINE_VERSION,
        )
        self.assertEqual(
            CapabilityAssessment.model_fields["engine_version"].default,
            CAPABILITY_ENGINE_VERSION,
        )
        self.assertEqual(
            GapAnalysis.model_fields["engine_version"].default,
            GAP_ENGINE_VERSION,
        )
        self.assertEqual(
            ValidationManifest.model_fields["manifest_version"].default,
            MANIFEST_VERSION,
        )
        self.assertEqual(
            ValidationManifest.model_fields["contract_schema_version"].default,
            CONTRACT_SCHEMA_VERSION,
        )

    def test_integration_ready_files_exist(self):
        pipeline_root = Path(__file__).resolve().parents[1]
        repo_root = pipeline_root.parent

        required = [
            repo_root / ".github/workflows/test.yml",
            repo_root / ".github/pull_request_template.md",
            repo_root / "AGENTS.md",
            repo_root / "CONTRIBUTING.md",
            pipeline_root / "docs/ARCHITECTURE.md",
            pipeline_root / "docs/HANDOFF_A.md",
            pipeline_root / "docs/HANDOFF_B.md",
            pipeline_root / "docs/HANDOFF_C.md",
            pipeline_root / "docs/HANDOFF_E.md",
            pipeline_root / "docs/GIT_WORKFLOW.md",
            pipeline_root / "docs/INTEGRATION_CHECKLIST.md",
            pipeline_root / "docs/D_MVP_COMPLETION_v1.0.md",
        ]
        missing = [str(path) for path in required if not path.exists()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
