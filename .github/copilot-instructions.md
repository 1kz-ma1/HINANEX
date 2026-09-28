# HINANEX GitHub Copilot Instructions

Read and follow `/AGENTS.md` before proposing or modifying repository code.

For scoped changes, also follow the nearest directory-level `AGENTS.md`.

Non-negotiable rules:

- `main` is controlled by the Merge Captain; do not propose direct main pushes or automatic merges.
- Preserve role boundaries: A=data research, B=frontend, C=validation, D=pipeline, E=GIS.
- Never fabricate or infer missing disaster-prevention facts.
- Preserve `score=null` vs `score=0`, Discovery/Capability states, and Gap semantics.
- Treat shared JSON Schema and RegionExport as versioned API contracts.
- If a PR depends on another PR, explicitly document the dependency.
- Prefer small, reviewable diffs.
- Run the relevant tests before calling work complete.

When uncertain about source meaning, contract compatibility, or merge order, stop and request human review.
