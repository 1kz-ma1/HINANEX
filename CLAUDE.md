# HINANEX Claude Instructions

Before changing code or documentation, read and follow `/AGENTS.md`.

If the target directory contains another `AGENTS.md`, follow it as an additional scoped rule set.

Key requirements:

- Never push or merge directly to `main`.
- Respect role ownership and PR dependencies.
- Never invent missing disaster-prevention facts.
- Preserve null vs zero and status semantics.
- Treat shared schemas/contracts as APIs.
- Run the required tests and report exactly what was or was not verified.

If these instructions conflict with `/AGENTS.md`, `/AGENTS.md` takes precedence.
