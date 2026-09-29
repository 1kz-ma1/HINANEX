#!/usr/bin/env python3
"""Fail role-scoped PRs that modify files outside their owned directory."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class RoleScope:
    role: str
    directory: str


ROLE_SCOPES = {
    "a": RoleScope("A / Data Research", "data-research/"),
    "b": RoleScope("B / Frontend", "frontend/"),
    "c": RoleScope("C / Validation", "validation/"),
    "d": RoleScope("D / Pipeline", "pipeline/"),
    "e": RoleScope("E / GIS", "gis/"),
}

ROLE_BRANCHES = {
    "role/a-data": "a",
    "role/b-frontend": "b",
    "role/c-validation": "c",
    "role/d-pipeline": "d",
    "role/e-gis": "e",
}

ROLE_FEATURE_PATTERN = re.compile(r"^(?:feature|fix)/([abcde])(?:-|/)", re.IGNORECASE)


def role_key_for_branch(head_ref: str) -> str | None:
    normalized = head_ref.strip()
    if normalized in ROLE_BRANCHES:
        return ROLE_BRANCHES[normalized]

    match = ROLE_FEATURE_PATTERN.match(normalized)
    if match:
        return match.group(1).lower()

    return None


def find_scope_violations(head_ref: str, changed_files: list[str]) -> tuple[RoleScope | None, list[str]]:
    role_key = role_key_for_branch(head_ref)
    if role_key is None:
        return None, []

    scope = ROLE_SCOPES[role_key]
    violations = [
        path for path in changed_files
        if path and not path.startswith(scope.directory)
    ]
    return scope, violations


def changed_files_from_git(base_sha: str, head_sha: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--changed-file", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    changed_files = list(args.changed_file)
    if not changed_files:
        if not args.base or not args.head:
            raise SystemExit("--base and --head are required when --changed-file is not supplied")
        changed_files = changed_files_from_git(args.base, args.head)

    scope, violations = find_scope_violations(args.head_ref, changed_files)

    if scope is None:
        print(f"SCOPE GUARD: SKIP ({args.head_ref} is not a role-scoped branch)")
        return 0

    print(f"SCOPE GUARD: {scope.role}")
    print(f"Allowed path: {scope.directory}")
    print(f"Changed files: {len(changed_files)}")

    if not violations:
        print("SCOPE GUARD: PASS")
        return 0

    print("SCOPE GUARD: FAIL")
    print("This role-scoped PR changes files outside its owned directory:")
    for path in violations:
        print(f"  - {path}")

    print()
    print("Move shared / cross-role changes into a separate PR instead of fixing them here.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
