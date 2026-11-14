# Agent guide (coding agents)

This file is for **automated coding agents** working in
[carlok/caciarabot](https://github.com/carlok/caciarabot). Human
contributors should read [CONTRIBUTING.md](CONTRIBUTING.md).

## Setup

- **Python:** 3.11+ (CI uses 3.12).
- **Package manager:** [uv](https://docs.astral.sh/uv/) only — do not
  hand-edit `uv.lock` except via `uv lock` / `uv add`.
- **Install dev dependencies:**

  ```bash
  uv sync --frozen
  ```

- **Secrets:** copy `.env.example` to `.env` locally for a real bot
  token. `.env` is gitignored; never commit it or paste tokens into
  issues, PRs, commits, or public docs.

## Tests and coverage

```bash
uv run --frozen ruff check app tests
uv run --frozen caciarabot-validate
uv run --frozen pytest
```

`pytest` is configured (via `pyproject.toml`) to report coverage for
`app/caciarabot` and fail if total coverage drops below the configured
floor. CI runs the same checks.

**Before every commit:** run the commands above. If you change behavior,
add or extend tests so **total coverage does not go down** — aim to
increase it when you touch related code. Do not lower `fail_under` to
make CI pass without maintainer approval.

## Repository layout

| Path | Role |
|------|------|
| `app/caciarabot/` | Application code: Telegram layer, engine, config, storage, LLM hooks, CLI entrypoints |
| `config/` | JSONC/JSONL reaction packs, prompts, limits (no deployment secrets) |
| `locales/` | UI strings |
| `media/` | Local image responses |
| `tests/` | Pytest suite |
| `deploy/` | Container/update helpers |
| `docs/` | Static assets (e.g. logo) |
| `PROMPT.md` | Multi-phase design spec (architecture reference) |

Layer boundaries follow `PROMPT.md` (clean interfaces between transport,
engine, config, and storage). Prefer extending existing modules over new
parallel abstractions.

## Conventions

- **Lint:** `ruff` with the rules in `pyproject.toml` (E, F, I, UP, B,
  RUF006). No project-wide formatter; line length is not enforced.
- **Config validation:** `uv run caciarabot-validate` must pass after
  config or schema changes.
- **Deployment settings** live in environment variables (`CACIARABOT_*`,
  `TELEGRAM_BOT_TOKEN`, optional `LLM_API_KEY`). Defaults are in code;
  `.env.example` documents overrides. Do not commit host-specific paths,
  tokens, API keys, or owner IDs.
- **Public documentation** (`README.md`, issue/PR text, comments intended
  for operators): keep examples generic — no real tokens, no private
  hostnames, no personal chat IDs unless they are clearly fake placeholders.

## Credentials and safety (strict)

This repository is a **Telegram bot**. Treat all credentials as toxic:

- Never commit `.env`, API keys, bot tokens, or production database files.
- Never add secrets to `config/`, tracked JSONC, tests, or workflow logs.
- Never print or echo secrets in CI or agent output.
- If you need a token in a test, use mocks or obvious placeholders
  (e.g. `000000000:TEST`).

## Contact

Maintainer: GitHub [@carlok](https://github.com/carlok). Use GitHub
issues/PRs for development; report vulnerabilities only as described in
[SECURITY.md](SECURITY.md).
