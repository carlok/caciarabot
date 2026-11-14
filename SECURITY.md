# Security policy

## Supported versions

Security fixes are applied on the default branch (`master`). Deployments
should track recent commits on `master` or tagged releases when available.

## Reporting a vulnerability

**Do not open a public GitHub issue** for security vulnerabilities.

Report them privately through [GitHub private vulnerability
reporting](https://github.com/carlok/caciarabot/security/advisories/new)
for this repository (repository **Security** tab → **Report a
vulnerability**). That channel keeps details confidential while a fix is
prepared.

Include when you can:

- A description of the issue and potential impact
- Steps to reproduce, if applicable
- Any suggested fix or mitigation you have in mind

The maintainer ([@carlok](https://github.com/carlok)) will acknowledge
reports through GitHub when possible and coordinate disclosure after a
fix.

## Scope notes

CaciaraBot is a self-hosted Telegram bot. Typical concerns include
leaked bot tokens or LLM API keys in `.env`, misconfigured file
permissions on bind-mounted `data/`, and accidental logging of message
content. Credentials belong only in `.env` (never committed) and must not
appear in configuration packs under `config/`.