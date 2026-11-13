# Security policy

## Supported versions

Security fixes are applied on the default branch (`master`). Deployments
should track recent commits on `master` or tagged releases when available.

## Reporting a vulnerability

**Please do not open a public GitHub issue** for security vulnerabilities.

Report privately using
[GitHub Security Advisories](https://github.com/carlok/caciarabot/security/advisories/new)
for this repository. That channel keeps details confidential until a fix
is ready.

Include:

- A description of the issue and potential impact
- Steps to reproduce, if applicable
- Any suggested fix or mitigation you have in mind

The maintainer ([@carlok](https://github.com/carlok)) will acknowledge
reports via GitHub when possible and coordinate disclosure after a fix.

## Scope notes

CaciaraBot is a self-hosted Telegram bot. Typical concerns include
leaked bot tokens or LLM API keys in `.env`, misconfigured file
permissions on bind-mounted `data/`, and accidental logging of message
content. Credentials belong only in `.env` (never committed) and must not
appear in configuration packs under `config/`.

## Contact

Maintainer: [@carlok](https://github.com/carlok) on GitHub (issues,
discussions, and Security Advisories only — no email for security
reports).
