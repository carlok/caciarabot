# custom pack

Add your own `*.jsonl` reaction files here (any filename, e.g.
`reactions.jsonl`) for triggers you want on your deployment without
touching `core-it`. Files in this directory are gitignored (see the
repo's `.gitignore`), so local tuning here never conflicts with
`git pull`.

This only works for reaction ids that don't already exist in
`core-it` (or any other enabled pack) — Phase 1 rejects duplicate
ids across packs rather than merging/overriding them. To adjust an
existing `core-it` trigger's probability/cooldown/responses, edit
`core-it` directly; git protects uncommitted edits from being
silently overwritten by a pull (it errors out and asks you to
stash/commit first).

After adding a file here, run `uv run caciarabot-validate` and
restart the bot to pick it up.
