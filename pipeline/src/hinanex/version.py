"""Version metadata for the HINANEX D-MVP baseline.

Project release and data-contract/engine versions are intentionally separated.
A repository release may change without forcing B/C to migrate their JSON
contract when the schema itself has not changed.
"""

PROJECT_VERSION = "1.0.0"
PROJECT_RELEASE = "v1.0-D-MVP"

# B/C JSON contract. Keep this stable until the RegionExport shape changes.
CONTRACT_SCHEMA_VERSION = "0.9"

# Evaluation semantics currently validated by the v0.9 test suite.
ASSESSMENT_ENGINE_VERSION = "0.9"
CAPABILITY_ENGINE_VERSION = "0.9"
GAP_ENGINE_VERSION = "0.9"
MANIFEST_VERSION = "0.9"
