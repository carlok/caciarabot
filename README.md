# CaciaraBot

<img src="docs/CaciaraBot.png" alt="CaciaraBot logo" width="200">

Italian-first, self-hosted, reactive Telegram group bot. It mostly stays
silent, watches ordinary group conversation, and occasionally reacts to
configured words/phrases with a text or local image response. No LLM,
no cloud dependencies — everything runs from local JSONC/JSONL
configuration and a local SQLite database.

This is the **Phase 1** vertical slice: Telegram connectivity, Italian
normalization, word/phrase triggers, probability, one cooldown
mechanism, weighted text/photo responses, SQLite persistence, Podman
deployment, `/help`, `/status`. See [PROMPT.md](PROMPT.md) for the full
multi-phase design spec this project is built from.

## Quick start

```bash
git clone <this repo>
cd caciarabot
cp .env.example .env
$EDITOR .env   # set TELEGRAM_BOT_TOKEN at minimum
chmod 777 data # see "Data directory permissions" below
podman compose up -d
```

Then add the bot to an Italian Telegram group — but read
[Telegram privacy mode](#telegram-privacy-mode-read-this-first) below
first, or passive triggers silently won't work.

### Data directory permissions

The container runs as a fixed non-root UID (1000). `./data` is bind-mounted
read-write so SQLite can create its database file there, but the host
directory is owned by whoever cloned the repo — not UID 1000 — so the
container can't write to it until you fix that up. If you skip this,
the bot fails at startup with `sqlite3.OperationalError: unable to open
database file`.

- **Native Linux host (rootless Podman):** `podman unshare chown 1000:1000 ./data`
  — this sets ownership as seen from inside the container's user
  namespace, no world-writable permissions needed.
- **macOS / Podman machine (remote client):** `podman unshare` doesn't
  work against a remote client. Use `chmod 777 ./data` instead — it's
  local dev-machine data, not a shared multi-user system, so the
  broader permission bit is an acceptable trade for not fighting the
  VM's UID mapping.

## Telegram privacy mode (read this first)

By default, Telegram bots only receive messages that are commands
(`/help`, `/status`, ...) or that directly mention/reply to them. This
is BotFather's **group privacy mode**, and it is **on by default**.

CaciaraBot's whole purpose is to react to ordinary conversation it was
never directly addressed to — so group privacy mode must be turned
**off** for the bot, or it will silently never see `buongiorno` while
`/help` keeps working fine. This is the single most common setup
mistake with this kind of bot.

To disable it:

1. Talk to [@BotFather](https://t.me/BotFather).
2. `/mybots` → select your bot → **Bot Settings** → **Group Privacy** → **Turn off**.
3. Remove the bot from the group and re-add it (privacy mode changes
   only take effect for chats the bot joins after the change).

The bot also needs to actually be a member of the group (not just have
been sent a `/start` in DM) and, for supergroups, does not need admin
rights for passive reactions.

## Configuration

```text
config/
├── bot.jsonc            # global settings: locale, packs, maxReactionsPerMessage, ...
├── normalization.jsonc  # global text-normalization defaults
├── limits.jsonc          # reserved anti-spam knobs (see note below)
└── packs/
    └── core-it/
        ├── manifest.jsonc
        ├── greetings.jsonl
        └── reactions.jsonl
```

- **JSONC** (`bot.jsonc`, `normalization.jsonc`, `limits.jsonc`,
  `manifest.jsonc`) is used for configuration humans read/edit, with
  `//` and `/* */` comments allowed.
- **JSONL** (`greetings.jsonl`, `reactions.jsonl`, ...) holds reaction
  rules, one compact JSON object per line. No comments inside JSONL —
  each line must be valid standalone JSON.

`limits.jsonc` currently only reserves `minimumChatIntervalSeconds` and
`maximumPassiveReactionsPer10Minutes` for later phases. Phase 1's only
active anti-spam control is each reaction rule's own `cooldownSeconds`.

### Adding a reaction

Append one line to any `.jsonl` file under a pack directory:

```json
{"id":"boh","category":"general","match":{"type":"word","values":["boh"]},"probability":0.1,"cooldownSeconds":600,"responses":[{"type":"text","value":"Boh anche a me.","weight":1}]}
```

Fields:

- `match.type`: `"word"` (whole-word match) or `"phrase"` (multi-word,
  matched as a unit). `regex` and `emoji` match types are accepted by
  later phases, not Phase 1.
- `probability` (0–1): chance the trigger fires once eligible.
- `cooldownSeconds`: minimum time between this trigger firing again in
  the same chat.
- `priority`: accepted by the schema, not yet enforced (Phase 2).
- `normalization`: optional per-rule override of the global
  normalization options (e.g. `{"ignoreAccents": true}`).
- `responses`: weighted list of `text`, `photo` (single file, `path`
  relative to `media/`), or `randomPhoto` (`directory` relative to
  `media/`, one file picked at random per send).

Run the validator after editing (see below) — a bad line is reported
with its exact file and line number and won't silently break the bot.

## Local media

```text
media/
└── images/
    ├── buongiorno/
    └── disastro/
```

Drop `.jpg`/`.jpeg`/`.png`/`.webp`/`.gif` files into the directory a
`randomPhoto` response points at. No CDN or external host is used —
local files are the source of truth. After the first successful
upload, CaciaraBot caches Telegram's `file_id` (keyed by path + size +
modification time) so it never re-uploads the same file; replacing the
file on disk invalidates the cache automatically.

## Validating configuration

Check the whole configuration (JSONC/JSONL syntax, schema, referenced
media files) without connecting to Telegram at all:

```bash
uv run caciarabot-validate
```

```text
Configuration valid.
6 files
5 reaction rules
0 local media files
0 errors
```

Run this after every configuration change, and definitely before
`podman compose up -d`.

## Running

Podman is the primary, supported deployment path and works rootless
with no host networking:

```bash
podman compose up -d
podman compose ps
podman compose logs -f
podman compose restart
podman compose down
```

`docker compose` works too if you'd rather use Docker, but Podman is
what this project is built and tested against.

Volumes:

- `./config` → `/config` (read-only)
- `./media` → `/media` (read-only)
- `./data` → `/data` (read-write — SQLite database lives here)

### Fast local iteration

For active development, use the `dev` overlay instead of rebuilding
the image on every code change. It builds the `dev` target (an
editable install) and bind-mounts `./app` and `./locales` over the
same paths inside the container, so a plain restart — no rebuild —
picks up source edits:

```bash
podman compose -f compose.yaml -f compose.dev.yaml up -d --build
# edit app/caciarabot/...
podman compose -f compose.yaml -f compose.dev.yaml restart
podman compose -f compose.yaml -f compose.dev.yaml logs -f
```

The default `podman compose up -d` (no overlay) always uses the
production target: a non-editable wheel install with no source bind
mount, closer to what you'd actually run in the group.

## Commands (Phase 1)

```text
/help    - list available commands
/status  - show whether passive reactions are on, chat activity, category count
```

Command names stay in English regardless of locale; only their text
output is localized (Italian by default). Administrative commands
(`/sleep`, `/wake`, `/categories`, `/reload`, ...) are a later phase —
Phase 1 has no per-chat admin surface yet, only global environment
configuration (`.env`) and file-based reaction packs.

## Privacy

CaciaraBot does not archive conversation content. Messages are
normalized and evaluated against triggers in memory, aggregate
counters are updated, and the message body is discarded. No full
message text is logged or persisted by default.

## Development

```bash
uv sync
uv run pytest
uv run caciarabot-validate
uv run caciarabot   # requires TELEGRAM_BOT_TOKEN in the environment
```

Repository layout: `app/caciarabot/` (Telegram transport, matching
engine, normalization, storage, config loading — kept as separate
layers per the clean-interfaces design in PROMPT.md §43), `config/`
(JSONC/JSONL content), `locales/`, `media/`, `tests/`.
