import unittest

from check_pr_scope import find_scope_violations, role_key_for_branch


class ScopeGuardTests(unittest.TestCase):
    def test_feature_b_maps_to_frontend(self):
        self.assertEqual(role_key_for_branch("feature/b-capability-card"), "b")

    def test_role_branch_maps_to_role(self):
        self.assertEqual(role_key_for_branch("role/c-validation"), "c")

    def test_shared_branch_is_not_role_scoped(self):
        self.assertIsNone(role_key_for_branch("fix/pr-scope-guard"))

    def test_role_change_inside_owned_directory_passes(self):
        scope, violations = find_scope_violations(
            "feature/b-capability-card",
            ["frontend/index.html", "frontend/src/app.js"],
        )
        self.assertEqual(scope.directory, "frontend/")
        self.assertEqual(violations, [])

    def test_role_change_outside_owned_directory_fails(self):
        _, violations = find_scope_violations(
            "feature/b-capability-card",
            [
                "frontend/index.html",
                ".github/workflows/test.yml",
                "pipeline/tests/test_release_metadata.py",
            ],
        )
        self.assertEqual(
            violations,
            [".github/workflows/test.yml", "pipeline/tests/test_release_metadata.py"],
        )

    def test_role_branch_to_main_is_also_scoped(self):
        _, violations = find_scope_violations(
            "role/e-gis",
            ["gis/map.js", "README.md"],
        )
        self.assertEqual(violations, ["README.md"])


if __name__ == "__main__":
    unittest.main()
