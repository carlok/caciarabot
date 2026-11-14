# Contributing to CaciaraBot

Thank you for helping improve CaciaraBot. This project is maintained by
[@carlok](https://github.com/carlok) on GitHub.

## Before you open a PR

1. Fork and branch from `master`.
2. Install dependencies: `uv sync --frozen`.
3. Run the same checks as CI:

   ```bash
   uv run --frozen ruff check app tests
   uv run --frozen caciarabot-validate
   uv run --frozen pytest
   ```

   Tests include coverage reporting for `app/caciarabot` and enforce a
   minimum coverage floor. New behavior should come with tests; try not to
   reduce overall coverage.

4. Do **not** commit `.env`, tokens, API keys, or machine-specific paths.
   See [AGENT.md](AGENT.md) for the full agent-oriented safety rules.

## Scope and style

- Match existing structure under `app/caciarabot/` and the design notes in
  [PROMPT.md](PROMPT.md).
- Keep changes focused; avoid drive-by refactors.
- User-facing docs should stay accurate but generic (no real secrets).

## Pull requests

Use the PR template checklist. Describe what changed and how you
verified it (commands run, manual checks if any).

## Code of conduct

Participants are expected to follow
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

See [SECURITY.md](SECURITY.md) for how to report vulnerabilities
privately. **Do not** open public issues or use the bug-report template for
security problems.

## Questions

Open a [GitHub issue](https://github.com/carlok/caciarabot/issues) or
comment on an existing one. Contact the maintainer as
[@carlok](https://github.com/carlok) on GitHub only.
