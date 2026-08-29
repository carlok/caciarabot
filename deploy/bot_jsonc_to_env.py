#!/usr/bin/env python3
"""One-shot migration: turn an old config/bot.jsonc into .env lines.

Bot settings used to live in config/bot.jsonc; they now come from the
environment, and that file is gone. Run this once against your old copy
and paste the output into .env:

    python3 deploy/bot_jsonc_to_env.py ~/bot.jsonc.mine >> .env

Deliberately stdlib-only and self-contained -- including its own comment
stripper -- so it runs on the deployment host without the project's
virtualenv, which is exactly where the old file is stranded.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# jsonc: strip // and /* */ outside string literals.
_STRIP = re.compile(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', re.DOTALL)

# (dotted path in bot.jsonc, environment variable)
_MAPPING = [
    ("defaultLocale", "CACIARABOT_DEFAULT_LOCALE"),
    ("timezone", "CACIARABOT_TIMEZONE"),
    ("reactionPacks", "CACIARABOT_REACTION_PACKS"),
    ("maxReactionsPerMessage", "CACIARABOT_MAX_REACTIONS_PER_MESSAGE"),
    ("passiveReactions", "CACIARABOT_PASSIVE_REACTIONS"),
    ("commands.enabled", "CACIARABOT_COMMANDS_ENABLED"),
    ("randomEvents.enabled", "CACIARABOT_EMOJI_REACTIONS_ENABLED"),
    ("randomEvents.emojiReactionProbability", "CACIARABOT_EMOJI_REACTION_PROBABILITY"),
    ("randomEvents.emojiReactionPool", "CACIARABOT_EMOJI_REACTION_POOL"),
    ("llm.enabled", "CACIARABOT_LLM_ENABLED"),
    ("llm.model", "CACIARABOT_LLM_MODEL"),
    ("llm.dryRun", "CACIARABOT_LLM_DRY_RUN"),
    ("llm.reply.probability", "CACIARABOT_LLM_REPLY_PROBABILITY"),
    ("llm.dailyThought.enabled", "CACIARABOT_LLM_DAILY_THOUGHT_ENABLED"),
    ("llm.dailyThought.time", "CACIARABOT_LLM_DAILY_THOUGHT_TIME"),
    ("llm.dailyThought.linkProbability", "CACIARABOT_LLM_DAILY_LINK_PROBABILITY"),
    ("llm.dailyThought.linkLanguages", "CACIARABOT_LLM_DAILY_LINK_LANGUAGES"),
    ("llm.citedReply.enabled", "CACIARABOT_LLM_CITED_REPLY_ENABLED"),
    ("llm.citedReply.triggerWords", "CACIARABOT_LLM_CITED_TRIGGER_WORDS"),
    ("llm.secret.enabled", "CACIARABOT_LLM_SECRET_ENABLED"),
    ("llm.secret.probability", "CACIARABOT_LLM_SECRET_PROBABILITY"),
    ("llm.secret.cooldownSeconds", "CACIARABOT_LLM_SECRET_COOLDOWN_SECONDS"),
    ("llm.digest.enabled", "CACIARABOT_DIGEST_ENABLED"),
    ("llm.digest.time", "CACIARABOT_DIGEST_TIME"),
    ("llm.digest.sources", "CACIARABOT_DIGEST_SOURCES"),
    ("llm.digest.redditSubs", "CACIARABOT_DIGEST_REDDIT_SUBS"),
]

_MISSING = object()


def _lookup(data, dotted: str):
    for key in dotted.split("."):
        if not isinstance(data, dict) or key not in data:
            return _MISSING
        data = data[key]
    return data


def _render(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} path/to/bot.jsonc", file=sys.stderr)
        raise SystemExit(2)

    raw = Path(sys.argv[1]).read_text(encoding="utf-8")
    data = json.loads(_STRIP.sub(lambda m: m.group(1) or "", raw))

    print("# Migrated from bot.jsonc")
    for dotted, variable in _MAPPING:
        value = _lookup(data, dotted)
        if value is not _MISSING:
            print(f"{variable}={_render(value)}")


if __name__ == "__main__":
    main()
