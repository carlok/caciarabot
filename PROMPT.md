# CaciaraBot — Italian-First, Self-Hosted Reactive Telegram Bot

Design and implement **CaciaraBot**, a small self-hosted Telegram group bot inspired by the general interaction model of the historical Italian Telegram bot SpacoBot.

CaciaraBot is **Italian-first, but not Italian-only**.

Its primary target is ordinary Italian Telegram group conversation. Its default reaction corpus, linguistic normalization, examples, humor, and group-chat behavior should therefore be optimized for Italian.

However, the software itself must use **English throughout**:

* source code;
* identifiers;
* function/class names;
* configuration keys;
* Telegram commands;
* comments;
* logs;
* tests;
* database schema;
* developer documentation.

Italian is the primary language of the **conversation being observed and reacted to**, not the language of the software interface or implementation.

The bot should remain structurally multilingual and reusable with other reaction packs later.

---

# 1. Product concept

CaciaraBot is not a conventional chatbot and should not behave like an assistant.

It is a **reactive Telegram group mascot**.

It remains mostly silent, observes ordinary group conversation, recognizes configured words, phrases, slang, expressions, emoji, or patterns, and occasionally reacts with:

* text;
* images;
* stickers;
* GIFs/animations;
* audio;
* voice messages;
* video;
* other predefined Telegram media.

Example:

```text
Marco:
Ragazzi buongiorno

CaciaraBot:
[random configured morning reaction]
```

Another:

```text
Luca:
Windows ha deciso di morire

CaciaraBot:
[random local reaction image]
```

Another:

```text
Giulia:
Che disastro

CaciaraBot:
Procede tutto secondo i piani.
```

The bot should behave like an eccentric participant who occasionally notices exactly the wrong or right word.

It should **not respond to every message**.

Restraint is a first-class feature.

---

# 2. Inspiration, not cloning

The interaction model is inspired by SpacoBot-like behavior:

* passive listening in group chats;
* keyword and phrase triggers;
* randomized predefined responses;
* media reactions;
* direct commands;
* sleep/wake behavior;
* reaction categories.

Do not create an exact clone.

Do not:

* scrape SpacoBot's private or public response corpus;
* copy its media library;
* reproduce its branding;
* reverse engineer private implementation details;
* aim for protocol or behavioral compatibility.

Build an independent bot using independently supplied content.

---

# 3. Core architecture

The fundamental pipeline should remain simple:

```text
Telegram update
      ↓
message normalization
      ↓
trigger matching
      ↓
eligibility filtering
      ↓
priority / probability / cooldown
      ↓
weighted response selection
      ↓
Telegram response
```

Do **not** require an LLM.

The humor should come primarily from:

* curated trigger definitions;
* curated reaction pools;
* timing;
* randomness;
* cooldowns;
* context;
* rarity.

An LLM may eventually exist as an optional plugin, but it must not be part of the core architecture.

---

# 4. Configuration philosophy

Do not use YAML.

Use:

* **JSONC** for structured global configuration;
* **JSONL** for trigger/reaction corpora;
* **`.env`** for secrets and deployment/runtime variables;
* SQLite for persistent runtime state.

Recommended structure:

```text
config/
├── bot.jsonc
├── normalization.jsonc
├── limits.jsonc
└── packs/
    ├── core-it/
    │   ├── manifest.jsonc
    │   ├── greetings.jsonl
    │   ├── reactions.jsonl
    │   ├── technology.jsonl
    │   └── night.jsonl
    └── custom/
        ├── manifest.jsonc
        └── reactions.jsonl
```

The distinction is intentional.

## JSONC

Use JSONC for configuration that humans frequently inspect and where comments improve maintainability.

Examples:

```text
bot.jsonc
normalization.jsonc
limits.jsonc
manifest.jsonc
```

## JSONL

Use JSONL for potentially large collections of independent reaction definitions.

One line should normally represent one logical rule.

Advantages:

* easy append/remove operations;
* clean diffs;
* simple streaming parsing;
* easy generation from scripts;
* trivial concatenation of reaction packs;
* malformed records can be identified by exact line number;
* no huge enclosing JSON array;
* suitable for thousands of reactions later.

Treat each JSONL line as an independent JSON document.

Do not allow comments inside JSONL records.

---

# 5. Environment configuration

Use `.env` for secrets and host-specific runtime settings.

Example:

```dotenv
TELEGRAM_BOT_TOKEN=
CACIARABOT_OWNER_ID=
TZ=Europe/Rome

CACIARABOT_CONFIG_DIR=/config
CACIARABOT_MEDIA_DIR=/media
CACIARABOT_DATA_DIR=/data
```

Provide:

```text
.env.example
```

Never commit a real Telegram token.

Configuration semantics belong in JSONC/JSONL rather than accumulating application behavior inside environment variables.

Environment variables should primarily cover:

* secrets;
* paths;
* deployment-specific overrides;
* process/runtime settings.

---

# 6. Example global JSONC configuration

Example `config/bot.jsonc`:

```jsonc
{
  // Default interaction corpus.
  "defaultLocale": "it",

  // Time context for Italian deployments.
  "timezone": "Europe/Rome",

  "reactionPacks": [
    "core-it",
    "custom"
  ],

  "maxReactionsPerMessage": 1,

  "passiveReactions": true,

  "commands": {
    "enabled": true
  },

  "randomEvents": {
    "enabled": false
  }
}
```

Use camelCase consistently unless there is a strong reason to choose another convention.

---

# 7. JSONL trigger model

Each JSONL record represents a reaction rule.

Example:

```json
{"id":"buongiorno","category":"greetings","match":{"type":"phrase","values":["buongiorno","buon giorno"]},"probability":0.18,"cooldownSeconds":900,"priority":3,"responses":[{"type":"text","value":"Addirittura buongiorno.","weight":3},{"type":"text","value":"Vediamo quanto dura.","weight":2},{"type":"randomPhoto","directory":"images/buongiorno","weight":1}]}
```

The actual JSONL file contains one compact JSON object per line.

For documentation, the same record may be pretty-printed:

```json
{
  "id": "buongiorno",
  "category": "greetings",

  "match": {
    "type": "phrase",
    "values": [
      "buongiorno",
      "buon giorno"
    ]
  },

  "probability": 0.18,
  "cooldownSeconds": 900,
  "priority": 3,

  "responses": [
    {
      "type": "text",
      "value": "Addirittura buongiorno.",
      "weight": 3
    },
    {
      "type": "text",
      "value": "Vediamo quanto dura.",
      "weight": 2
    },
    {
      "type": "randomPhoto",
      "directory": "images/buongiorno",
      "weight": 1
    }
  ]
}
```

Internally, however, it remains one JSONL record.

---

# 8. Trigger types

Support at least:

## Word

```json
{
  "match": {
    "type": "word",
    "values": ["apple"]
  }
}
```

It should match:

```text
Apple costa troppo.
```

but not automatically:

```text
pineapple
```

---

## Phrase

```json
{
  "match": {
    "type": "phrase",
    "values": [
      "buongiorno a tutti",
      "buongiorno ragazzi"
    ]
  }
}
```

---

## Regex

```json
{
  "match": {
    "type": "regex",
    "pattern": "\\bwindows\\s+(vista|me)\\b"
  }
}
```

---

## Emoji

```json
{
  "match": {
    "type": "emoji",
    "values": ["🤡"]
  }
}
```

---

# 9. Italian-first normalization

Real Italian Telegram messages do not look like formal prose.

Expect forms such as:

```text
boh
vabbè
vabbe
vabbeh
raga
regà
cioè
cioe
però
pero
daiiii
nooooooo
AHAHAHAHAH
ma che cazzo
```

Implement a conservative normalization layer.

Potential pipeline:

```text
original input
    ↓
Unicode normalization
    ↓
case folding
    ↓
apostrophe normalization
    ↓
optional accent folding
    ↓
optional repeated-character normalization
    ↓
tokenization
```

Always retain both:

```text
originalText
normalizedText
```

The trigger engine should be able to select which representation it needs.

---

# 10. Configurable normalization

Normalization behavior should be configurable globally and overridable per rule.

Example `normalization.jsonc`:

```jsonc
{
  "caseInsensitive": true,
  "normalizeApostrophes": true,

  // Keep accents by default.
  "ignoreAccents": false,

  // Potentially destructive, therefore disabled globally.
  "collapseRepeatedLetters": false
}
```

A specific reaction may override this:

```json
{
  "id": "vabbe",
  "match": {
    "type": "word",
    "values": ["vabbè", "vabbe"]
  },
  "normalization": {
    "ignoreAccents": true
  }
}
```

Another:

```json
{
  "id": "dai",
  "match": {
    "type": "word",
    "values": ["dai"]
  },
  "normalization": {
    "collapseRepeatedLetters": true
  }
}
```

This may allow:

```text
dai
daiiii
DAIIII
```

to activate the same trigger.

Do not implement uncontrolled fuzzy matching.

---

# 11. Italian apostrophes

Handle typographic and ASCII apostrophes consistently:

```text
com'è
com’è

l'amico
l’amico

po'
po’
```

Normalize apostrophe code points for matching purposes without modifying the original message.

---

# 12. Accent handling

Italian chat frequently omits accents:

```text
però / pero
cioè / cioe
vabbè / vabbe
```

Allow accent-insensitive matching where explicitly enabled.

Do not globally assume accented and unaccented words are always semantically interchangeable.

---

# 13. Responses

Support at minimum:

```text
text
photo
animation
sticker
audio
voice
video
```

And directory pools:

```text
randomPhoto
randomAnimation
randomAudio
randomVideo
```

Example:

```json
{
  "type": "randomPhoto",
  "directory": "images/disastro"
}
```

---

# 14. Local media first

A central requirement is that media may live entirely on the self-hosted machine.

Recommended layout:

```text
media/
├── images/
│   ├── buongiorno/
│   ├── disastro/
│   └── technology/
├── animations/
├── stickers/
├── audio/
├── voice/
└── video/
```

No CDN or external image host should be required.

Local media is the source of truth.

After successfully uploading media to Telegram, cache the corresponding Telegram `file_id` when beneficial.

Reuse `file_id` on subsequent sends to avoid unnecessary uploads.

If the local source changes, the cache should be invalidatable.

A simple fingerprint based on path, file size, and modification time is sufficient initially.

---

# 15. Response weights

Support weighted random selection.

Example:

```json
{
  "responses": [
    {
      "type": "text",
      "value": "Eccoci.",
      "weight": 8
    },
    {
      "type": "photo",
      "path": "images/reactions/eccoci.jpg",
      "weight": 2
    }
  ]
}
```

Weights need not sum to any particular value.

---

# 16. Probability

Trigger occurrence does not imply reaction.

Example:

```json
{
  "probability": 0.12
}
```

means an eligible trigger fires approximately 12% of the time.

Allow a per-chat activity multiplier.

For example:

```text
effective probability =
    trigger probability × chat activity
```

with:

```text
chat activity ∈ [0,1]
```

This allows noisy groups to reduce CaciaraBot without disabling it entirely.

---

# 17. Cooldowns

Implement multiple anti-spam controls.

## Trigger cooldown

```json
{
  "cooldownSeconds": 300
}
```

## Per-chat interval

Configured globally:

```jsonc
{
  "minimumChatIntervalSeconds": 20
}
```

## Per-user rate limiting

Prevent intentional trigger spam.

## Time-window limits

Example:

```jsonc
{
  "maximumPassiveReactionsPer10Minutes": 8
}
```

Explicit commands should be governed independently from passive reactions.

---

# 18. Collision handling

One message may match several rules.

Example:

```text
Buongiorno ragazzi, Windows è di nuovo un disastro.
```

may match:

```text
buongiorno
windows
disastro
```

Do not automatically emit three messages.

Algorithm:

```text
collect matches
      ↓
remove ineligible matches
      ↓
consider priority
      ↓
evaluate probabilities
      ↓
weighted/random selection
      ↓
emit at most configured maximum
```

Default:

```jsonc
{
  "maxReactionsPerMessage": 1
}
```

---

# 19. Priority

Each rule may include:

```json
{
  "priority": 10
}
```

Higher-priority specific expressions should be able to supersede generic triggers.

For example:

```text
windows vista
```

may reasonably override the generic:

```text
windows
```

reaction.

---

# 20. Reaction packs

Treat reaction content as installable/loadable packs from the beginning, even if no package-management feature exists yet.

Suggested structure:

```text
packs/
├── core-it/
│   ├── manifest.jsonc
│   ├── greetings.jsonl
│   ├── general.jsonl
│   ├── technology.jsonl
│   └── media/
│
├── programmers-it/
│   ├── manifest.jsonc
│   ├── reactions.jsonl
│   └── media/
│
└── custom/
```

Example manifest:

```jsonc
{
  "id": "programmers-it",
  "version": 1,
  "locale": "it",

  "name": {
    "it": "Programmatori",
    "en": "Programmers"
  }
}
```

The engine should not assume that every pack is Italian.

---

# 21. English Telegram commands

Telegram commands should remain English.

Use conventional names:

```text
/start
/help
/status
/categories
/sleep
/wake
/stats
/reload
```

Optional content commands:

```text
/photo
/sticker
/audio
/reaction
/quote
```

Do not create Italian aliases such as:

```text
/dormi
/sveglia
/statistiche
```

The bot's Italian-first nature comes from **what it reacts to and how it reacts**, not from translating technical commands.

---

# 22. User-facing command output

Command names are English, but the textual response may default to Italian because the default chat locale is Italian.

Example:

```text
/status

CaciaraBot:
Attivo.
Reazioni passive: sì
Attività: 45%
Categorie attive: 7
```

This is acceptable.

A future English locale could produce:

```text
Active.
Passive reactions: yes
Activity: 45%
Enabled categories: 7
```

Commands remain stable across locales.

---

# 23. Sleep and wake

Use:

```text
/sleep
/wake
```

When asleep:

* passive reactions stop;
* administrative commands remain available;
* status/help remain available;
* state persists across restart.

The awake/asleep state is per Telegram chat.

---

# 24. Localization

Do not hard-code user-facing strings into application logic.

Since JSONC is the chosen configuration family, use:

```text
locales/
├── it.json
└── en.json
```

Plain JSON is appropriate here because these files can be mechanically validated and do not require extensive comments.

Example:

```json
{
  "status.awake": "Attivo.",
  "status.sleeping": "Sto dormendo.",
  "reload.success": "Configurazione ricaricata.",
  "permission.denied": "Comando riservato agli amministratori."
}
```

Italian is the default locale.

English should remain available structurally.

---

# 25. Per-chat configuration

Persist settings such as:

```text
locale
activity
awake
enabled categories
disabled categories
passive reaction state
```

Example conceptual state:

```json
{
  "locale": "it",
  "activity": 0.45,
  "awake": true,
  "enabledCategories": [
    "greetings",
    "general",
    "technology"
  ]
}
```

Runtime state belongs in SQLite, not configuration JSONL.

---

# 26. Administration

Telegram group administrators may control settings for their group.

An optional global owner is configured via numeric Telegram user ID.

Never use usernames for authorization.

Possible commands:

```text
/status
/sleep
/wake
/categories
/stats
/reload
```

Optional later commands:

```text
/activity 0.5
/category enable technology
/category disable audio
/locale it
```

Keep commands concise.

Do not prematurely build a complicated command DSL.

---

# 27. Hot reload

`/reload` should reload:

* JSONC configuration;
* JSONL reaction databases;
* locale files;
* media directory indexes.

Use transactional semantics:

```text
read candidate configuration
        ↓
parse
        ↓
validate
        ↓
build candidate runtime model
        ↓
success?
   yes             no
    ↓               ↓
atomic swap      preserve old state
```

A malformed reaction must not crash the running bot.

For JSONL errors, report at least:

```text
filename
line number
reaction ID if available
validation error
```

For example:

```text
packs/custom/reactions.jsonl:42
invalid field "probability": expected number between 0 and 1
```

JSONL should make such diagnostics particularly straightforward.

---

# 28. JSON Schema

Provide formal JSON Schema definitions for:

```text
bot.jsonc
normalization.jsonc
pack manifest
reaction JSONL records
locale files where practical
```

A JSONL file should be validated record-by-record against the reaction schema.

Include a command-line validation tool:

```bash
python -m caciarabot.validate
```

or equivalent.

It should validate the complete configuration without starting Telegram connectivity.

Example:

```text
Configuration valid.
12 files
483 reaction rules
176 local media files
0 errors
```

This is important for maintainability.

---

# 29. JSONL ergonomics

Because JSONL records can become long, support two complementary authoring modes.

Primary runtime format:

```text
*.jsonl
```

Optional development helper:

```text
tools/build_pack.py
```

which may compile pretty-formatted individual JSON/JSONC files into JSONL.

Do not require this compilation process for normal operation.

A human should still be able to add a one-line reaction directly to a `.jsonl` file.

---

# 30. Statistics

Maintain lightweight operational counters:

* messages observed;
* triggers matched;
* passive reactions sent;
* command reactions sent;
* counts by trigger;
* counts by category;
* counts by response;
* media usage.

Example:

```text
/stats
```

Response:

```text
Messaggi osservati: 28.421
Trigger riconosciuti: 1.392
Reazioni inviate: 417

Più frequenti:
1. buongiorno — 103
2. windows — 72
3. disastro — 55
```

Do not persist full message bodies merely for analytics.

---

# 31. Privacy

Default processing model:

```text
receive message
      ↓
normalize transiently
      ↓
evaluate reactions
      ↓
update aggregate counters
      ↓
discard message content
```

Do not create a permanent archive of group conversations.

Do not log complete messages by default.

---

# 32. Structured logging

Use English structured logs.

Useful fields:

```text
chat_id
message_id
user_id
trigger_id
response_id
response_type
decision
reason
cooldown_state
```

Example:

```text
INFO reaction_selected chat_id=-123 trigger_id=buongiorno response_id=buongiorno_02
```

Never log:

```text
TELEGRAM_BOT_TOKEN
```

---

# 33. Persistence

Use SQLite.

Store:

```text
chats
chat settings
awake/sleep state
category settings
Telegram file_id cache
statistics
relevant cooldown state
```

Do not add PostgreSQL unless a future requirement genuinely justifies it.

---

# 34. Podman-first deployment

The project is **Podman-first**.

Primary supported workflow:

```bash
podman compose up -d
```

or another current Podman-native Compose workflow where appropriate.

The repository should provide:

```text
Containerfile
compose.yaml
```

Prefer the OCI-neutral name:

```text
Containerfile
```

rather than making `Dockerfile` the canonical build definition.

Keep the image compatible with Docker where doing so requires no significant compromise.

Expected deployment:

```bash
cp .env.example .env
$EDITOR .env
podman compose up -d
```

Typical management:

```bash
podman compose ps
podman compose logs -f
podman compose restart
podman compose down
```

Do not make Docker Desktop or a Docker daemon a requirement.

---

# 35. Rootless Podman

The default deployment should work with **rootless Podman**.

Avoid unnecessary:

```text
--privileged
host networking
root-owned persistent volumes
special Linux capabilities
```

The bot only needs:

* outbound HTTPS connectivity to Telegram;
* read access to configuration/media;
* write access to its data directory.

Design with least privilege.

---

# 36. Container user

Run the application as a non-root user inside the container.

Make UID/GID handling practical for mounted directories.

Document required permissions for:

```text
/config
/media
/data
```

Only `/data` normally requires write access.

Configuration and media should preferably be mounted read-only:

```text
/config:ro
/media:ro
```

while:

```text
/data
```

is writable.

---

# 37. Example compose configuration

Provide a clean Podman-compatible `compose.yaml`.

Conceptually:

```yaml
services:
  caciarabot:
    build:
      context: .
      dockerfile: Containerfile

    env_file:
      - .env

    volumes:
      - ./config:/config:ro
      - ./media:/media:ro
      - ./data:/data

    restart: unless-stopped
```

If SELinux labeling is relevant for common Podman installations, document appropriate volume-label handling rather than disabling SELinux.

Do not require host networking.

---

# 38. Optional Quadlet deployment

As a secondary deployment mode, consider providing an optional Podman Quadlet definition for users who want systemd-managed production operation.

For example:

```text
deploy/
└── caciarabot.container
```

This is optional.

The basic development/self-hosting workflow should remain:

```text
podman compose up -d
```

Do not make systemd knowledge necessary for initial use.

---

# 39. Technology stack

Prefer:

* Python 3;
* a maintained Telegram Bot API framework such as `aiogram`;
* SQLite;
* JSON / JSONC / JSONL;
* Podman;
* OCI containers.

Do not require:

* Redis;
* PostgreSQL;
* RabbitMQ;
* Kubernetes;
* vector databases;
* external cloud services;
* external media hosting;
* an LLM API.

The entire application should comfortably run on:

* a small VPS;
* a home server;
* NAS;
* Raspberry Pi-class hardware;
* ordinary Linux workstation.

---

# 40. Repository structure

Recommended:

```text
caciarabot/
├── app/
│   └── caciarabot/
│       ├── telegram/
│       ├── engine/
│       ├── matching/
│       ├── normalization/
│       ├── localization/
│       ├── models/
│       ├── config/
│       ├── storage/
│       └── main.py
│
├── config/
│   ├── bot.jsonc
│   ├── normalization.jsonc
│   ├── limits.jsonc
│   └── packs/
│       ├── core-it/
│       │   ├── manifest.jsonc
│       │   ├── greetings.jsonl
│       │   ├── reactions.jsonl
│       │   └── technology.jsonl
│       └── custom/
│
├── locales/
│   ├── it.json
│   └── en.json
│
├── media/
│   ├── images/
│   ├── animations/
│   ├── stickers/
│   ├── audio/
│   ├── voice/
│   └── video/
│
├── data/
│
├── tests/
├── tools/
├── deploy/
│   └── caciarabot.container
├── Containerfile
├── compose.yaml
├── .env.example
├── pyproject.toml
└── README.md
```

---

# 41. Telegram privacy requirements

The bot must receive ordinary group messages for passive triggers to work.

Document the necessary BotFather/group configuration prominently.

Do not allow the common failure mode where:

```text
/help
```

works but:

```text
buongiorno
```

is invisible to the bot.

Explain clearly why this happens and how to configure the Telegram bot accordingly.

---

# 42. Testing

The reaction engine must be testable independently from Telegram.

Test at minimum:

### Word boundaries

```text
trigger: roma

"Roma oggi è calda"  → match
```

while avoiding accidental larger-word matches.

### Case normalization

```text
buongiorno
Buongiorno
BUONGIORNO
```

### Accents

When configured:

```text
però
pero
```

### Apostrophes

```text
com'è
com’è
```

### Repeated characters

When enabled:

```text
dai
daiiii
```

### Multiple matches

One message should not generate multiple unsolicited reactions by default.

### Priority

Specific triggers should supersede more generic ones where configured.

### Cooldowns

Repeated trigger spam should not repeatedly summon the bot.

### Probability

Use seeded or injected randomness for deterministic tests.

### Weighted responses

Test weighted selection independently.

### JSONL validation

Malformed line:

```text
filename + line number + precise validation error
```

### Missing media

Missing local file or directory should be detected during validation.

---

# 43. Clean internal interfaces

Keep Telegram transport separate from the reaction engine.

Conceptually:

```python
normalized = normalizer.normalize(message.text)

matches = matcher.find_matches(normalized)

decision = decision_engine.select(
    matches=matches,
    chat_state=chat_state,
    user_state=user_state,
)

if decision:
    await telegram_renderer.send(decision)
```

Do not scatter:

* regex matching;
* random calls;
* cooldown logic;
* filesystem operations;
* Telegram API calls;

across individual Telegram handlers.

---

# 44. Content, not code, defines personality

The default Italian personality should be:

* concise;
* dry;
* slightly absurd;
* occasionally sarcastic;
* repetitive enough that reactions become group in-jokes;
* infrequent enough to remain funny.

Examples:

```text
Eh.
```

```text
Ottimo.
```

```text
Eccoci.
```

```text
Partiamo bene.
```

```text
Non ho visto niente.
```

```text
Era inevitabile.
```

Do not hard-code these into engine behavior.

They belong in reaction JSONL records.

---

# 45. The desired interaction pattern

Good:

```text
human
human
human
human
human mentions trigger
CaciaraBot reacts
human
human
human
human
```

Bad:

```text
human
bot
human
bot
human
bot
```

A good reaction bot is noticeable precisely because it is usually silent.

---

# 46. Phase 1 — complete vertical slice

Implement first:

1. Telegram connectivity;
2. ordinary group-message reception;
3. Italian-oriented normalization;
4. JSONC global configuration;
5. JSONL trigger loading;
6. word and phrase matching;
7. probability;
8. one cooldown mechanism;
9. weighted text responses;
10. local image responses;
11. SQLite persistence;
12. Podman containerization;
13. `podman compose up -d`;
14. `/help`;
15. `/status`.

This must work end-to-end before adding abstraction.

---

# 47. Phase 2 — complete reaction engine

Then add:

* regex;
* emoji;
* per-trigger normalization;
* priorities;
* trigger cooldowns;
* user rate limiting;
* directory media pools;
* animation;
* stickers;
* audio;
* voice;
* video;
* replies;
* placeholders;
* reaction packs.

---

# 48. Phase 3 — real group operation

Then implement:

```text
/sleep
/wake
/categories
/stats
/reload
```

plus:

* per-chat activity;
* category enable/disable;
* persisted configuration;
* administrative permissions;
* Telegram `file_id` cache;
* locale support;
* transactional hot reload.

---

# 49. Phase 4 — optional extensions

Only afterwards consider:

* inline Telegram mode;
* time-aware rules;
* limited previous-message context;
* random spontaneous reactions;
* richer administration;
* pack import/export;
* optional plugin API;
* optional LLM-generated responses.

None of these should complicate the core engine prematurely.

---

# 50. Deliverables

Produce:

1. architecture proposal;
2. repository structure;
3. JSONC configuration specification;
4. JSONL reaction-record specification;
5. formal JSON Schemas;
6. Italian normalization specification;
7. SQLite schema;
8. complete Phase-1 implementation;
9. subsequent Phase-2/3 implementation;
10. `Containerfile`;
11. Podman-compatible `compose.yaml`;
12. `.env.example`;
13. optional Quadlet deployment file;
14. small original Italian demonstration reaction pack;
15. placeholder media structure;
16. BotFather configuration instructions;
17. configuration validator;
18. tests;
19. README;
20. administrator documentation.

---

# 51. Implementation priority

Optimize for:

```text
small codebase
+
JSONL reaction corpus
+
predictable matching
+
excellent Italian chat normalization
+
easy local media handling
+
strong anti-spam controls
+
rootless Podman deployment
```

Do not optimize for feature count.

The target experience is:

```text
git clone
      ↓
copy .env.example to .env
      ↓
set Telegram token
      ↓
edit JSONC configuration
      ↓
add/edit JSONL reactions
      ↓
copy local media
      ↓
podman compose up -d
      ↓
add CaciaraBot to an Italian Telegram group
```

and it works.

Before implementation, briefly critique the specification and identify anything that can be simplified further.

Then implement **Phase 1 as a complete working vertical slice before expanding the system**.

