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
chmod 777 data && chmod -R o+rX config media # see "Bind mount permissions" below
podman compose up -d
```

Then add the bot to an Italian Telegram group — but read
[Telegram privacy mode](#telegram-privacy-mode-read-this-first) below
first, or passive triggers silently won't work.

### Bind mount permissions

The container runs as a fixed non-root UID (1000), which under
rootless Podman's default user-namespace shift does **not** map 1:1 to
your host user's UID — so every bind-mounted directory needs its
permissions opened up for that shifted UID to read (`config`, `media`)
or write (`data`) it. Skip this and you'll hit either
`sqlite3.OperationalError: unable to open database file` (data) or
`PermissionError: [Errno 13] Permission denied: '/config/bot.jsonc'`
(config) at startup.

- **`./data`** (read-write — SQLite needs to create its file there):
  - **Native Linux host (rootless Podman):** `podman unshare chown 1000:1000 ./data`
    — sets ownership as seen from inside the container's user
    namespace, no world-writable permissions needed.
  - **macOS / Podman machine (remote client):** `podman unshare` doesn't
    work against a remote client. Use `chmod 777 ./data` instead — it's
    local dev-machine data, not a shared multi-user system, so the
    broader permission bit is an acceptable trade for not fighting the
    VM's UID mapping.
- **`./config` and `./media`** (read-only — just need to be readable):
  `chmod -R o+rX config media` on either platform. Neither directory
  holds secrets (those live in `.env`, never bind-mounted), so making
  them world-readable is safe.

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
├── packs/
│   └── core-it/
│       ├── manifest.jsonc
│       ├── greetings.jsonl
│       └── reactions.jsonl
└── prompts/              # only used if bot.jsonc's "llm" is enabled
    ├── replies/*.txt      # picked at random for ambient LLM replies
    ├── daily/*.txt        # picked at random for the daily thought
    └── cited/*.txt        # picked at random when the bot is directly addressed
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

### Native Linux: enable the Podman socket first

`podman compose` delegates to a Docker-API-compatible compose provider
(`docker-compose` or `podman-compose`), which needs Podman's REST API
socket running. On **macOS**, `podman machine` starts this
automatically — nothing to do. On **native Linux** (e.g. Ubuntu), it's
a systemd user service that isn't always enabled by default, and its
absence is exactly this error:

```text
failed to connect to the docker API at unix:///run/user/1000/podman/podman.sock
```

Fix, once per machine:

```bash
systemctl --user enable --now podman.socket
```

Then `podman compose up -d` works as above. This isn't a project
config issue — it's the same compose files on both platforms, just a
one-time host prerequisite that macOS's `podman machine` happens to
handle for you automatically.

Volumes:

- `./config` → `/config` (read-only)
- `./media` → `/media` (read-only)
- `./data` → `/data` (read-write — SQLite database lives here)

### Surviving a host reboot

`compose.yaml`'s `restart: unless-stopped` only restarts the container
if Podman's own tracking process is already up — it does **not**, by
itself, guarantee the container comes back after a full host reboot.
Rootless Podman has no persistent system daemon like Docker's; that
requires two more things to be true:

```bash
loginctl show-user $USER | grep Linger              # should say Linger=yes
systemctl --user is-enabled podman-restart.service   # should say "enabled"
```

If either isn't set: `sudo loginctl enable-linger $USER` and
`systemctl --user enable podman-restart.service`.

For a setup that doesn't depend on getting both of those right, use
the **Quadlet** unit at [`deploy/caciarabot.container`](deploy/caciarabot.container)
instead — systemd manages the container directly (no linger/
podman-restart dependency at all). Install instructions are in the
file's header comment.

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
mount, closer to what you'd actually run in the group. This is pinned
explicitly via `build.target: runtime` in `compose.yaml` — without it,
an unpinned build defaults to the *last* stage in `Containerfile`
(`dev`), which some compose providers pick up differently than others.
If you ever see `No module named caciarabot.main` in the logs, rebuild
with `podman compose build --no-cache` — that's a stale image built
from the wrong stage, not a code bug.

## Ambient behaviors (optional, off by default)

Two mechanisms independent of the word/phrase trigger system, both
configured in `bot.jsonc`:

### Emoji reactions

```jsonc
"randomEvents": {
  "enabled": true,
  "emojiReactionProbability": 0.33,
  "emojiReactionPool": ["😁", "😢", "😡", "🤣", "👍", "👎", "🤡"]
}
```

On any ordinary group message, roll this probability to tap a random
emoji from the pool onto it — Telegram's native tap-to-react badge
(`setMessageReaction`), not a reply message. Telegram only accepts a
fixed set of emoji here; `emojiReactionPool` is validated against that
set at config load time (`app/caciarabot/config/allowed_reactions.py`),
so a typo fails `caciarabot-validate` instead of erroring against the
live API.

### LLM replies, daily thought, and cited replies (requires a Gemini API key)

```jsonc
"llm": {
  "enabled": true,
  "model": "gemini-3.1-flash-lite",
  "dryRun": false,
  "reply": { "probability": 0.1 },
  "dailyThought": { "enabled": true, "time": "09:00" },
  "citedReply": { "enabled": true }
}
```

Set `GEMINI_API_KEY` in `.env` (get one free at
[aistudio.google.com](https://aistudio.google.com/apikey) — a couple
of calls a day comfortably fits inside the free tier, though free
quota is best-effort and can change). The bot fails to start if
`llm.enabled` is `true` and the key is missing.

- **Reply**: on any group message that didn't already get a word-trigger
  reaction, roll `reply.probability`; if it hits, a random prompt is
  picked from `config/prompts/replies/*.txt` and sent to Gemini
  along with *only that one message's text* — no stored conversation
  history — and the response is sent back as a normal text reply.
- **Daily thought**: an in-process scheduler (not a host cron job —
  this is one long-running container/process, so a background asyncio
  loop needs no extra infrastructure) wakes up once a day at
  `dailyThought.time` (in `bot.jsonc`'s `timezone`), picks a random
  prompt from `config/prompts/daily/*.txt`, generates a short
  unprompted message, and posts it to every chat the bot has seen.
- **Cited reply**: when someone directly addresses the bot — types its
  `@username` in text, or uses Telegram's native reply feature on one
  of the bot's own earlier messages — it *always* replies (no
  probability roll; a direct address going unanswered reads as broken,
  not restrained). Detection uses Telegram's message entities (exact
  `@mention` spans), not a raw text search, so it can't be fooled by
  the username appearing as a substring of something else. A random
  prompt is picked from `config/prompts/cited/*.txt`; if the citation
  was a reply to the bot's own message, that earlier message is
  included as context so the reply can actually address it. This
  takes priority over word triggers and the ambient reply for that
  message — no double-reply.
- Add more variety by dropping additional `.txt` files into any
  `prompts/` subfolder — one prompt per file, picked at random each
  time. No JSON structure needed, it's just prose.
- **`dryRun: true`**: still makes the real Gemini call (so you can
  iterate on prompts/probability and see actual output), but logs the
  generated text (`llm_reply_dry_run` / `daily_thought_dry_run` /
  `llm_cited_reply_dry_run` events) instead of sending it to Telegram.
  Use this to test the feature without spamming a real group.
- Model default is `gemini-3.1-flash-lite`; free-tier quota varies by
  model and can be `0` for some (confirmed live against a real key:
  `gemini-2.0-flash` was quota-0, `gemini-2.5-flash-lite` is retired
  for new users, `gemini-3.1-flash-lite` and `gemini-flash-lite-latest`
  both worked) — if you hit `429 RESOURCE_EXHAUSTED` with a real
  quota-exceeded message, try a different model name here.

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

**Exception**: if `llm.enabled` is `true`, the LLM reply feature sends
the *single message text that triggered a reply roll* to Google's
Gemini API over the network — this is the one place message content
leaves the machine. It is not stored locally either way, and no
conversation history is sent, only that one message. If this is a
concern, leave `llm.enabled: false` (the default).

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
