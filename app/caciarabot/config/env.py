"""Builds the global bot configuration from environment variables.

There used to be a `config/bot.jsonc`, and it was the single worst part
of running this bot: it is per-deployment by nature, but it was also a
tracked file, so every `git pull` that touched it aborted on the live
box. Making it untracked only moved the problem -- git still refuses to
merge a commit that touches a locally-modified file.

So the file is gone. Every knob has a default in `BotConfig`, and each
one is overridable by an environment variable, which the deployment
already has in a `.env` that git has never tracked and never will. One
per-deployment file instead of two, and no config file for a pull to
collide with.

Variable names are derived from the field names rather than listed, so
a new `BotConfig` field is configurable the moment it exists:
`llm_daily_thought_time` reads `CACIARABOT_LLM_DAILY_THOUGHT_TIME`.
"""

from __future__ import annotations

import dataclasses
import re
import typing
from collections.abc import Mapping

from caciarabot.config.allowed_reactions import ALLOWED_REACTION_EMOJI
from caciarabot.config.errors import ConfigError
from caciarabot.config.models import BotConfig

ENV_PREFIX = "CACIARABOT_"
ENV_SOURCE = "environment"

# CACIARABOT_-prefixed names that are deliberately not BotConfig fields.
# Anything else with the prefix is almost certainly a typo in .env, and
# silently ignoring it is how you spend an evening wondering why a knob
# you set had no effect.
_NON_CONFIG_VARIABLES = frozenset(
    {
        "CACIARABOT_CONFIG_DIR",
        "CACIARABOT_MEDIA_DIR",
        "CACIARABOT_DATA_DIR",
        "CACIARABOT_OWNER_ID",
    }
)

_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})
_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_PROBABILITY_FIELDS = (
    "emoji_reaction_probability",
    "llm_reply_probability",
    "llm_daily_link_probability",
    "llm_secret_probability",
)
_TIME_FIELDS = ("llm_daily_thought_time", "digest_time")
_NON_EMPTY_FIELDS = ("default_locale", "timezone", "llm_model", "reaction_packs")
_KNOWN_DIGEST_SOURCES = frozenset({"hackernews", "github_trending", "reddit"})


def environment_variable_name(field_name: str) -> str:
    return ENV_PREFIX + field_name.upper()


def _parse(raw: str, annotation: object) -> object:
    if annotation is bool:
        lowered = raw.strip().lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
        raise ValueError("expected a boolean (true/false, yes/no, on/off, 1/0)")
    if annotation is int:
        return int(raw.strip())
    if annotation is float:
        return float(raw.strip())
    if annotation is str:
        return raw.strip()
    # The only remaining shape in BotConfig is tuple[str, ...].
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _constraint_errors(values: Mapping[str, object]) -> list[ConfigError]:
    """Range and vocabulary checks the JSON Schema used to do."""
    errors: list[ConfigError] = []

    def fail(field_name: str, message: str) -> None:
        errors.append(
            ConfigError(
                file=ENV_SOURCE, field=environment_variable_name(field_name), message=message
            )
        )

    for name in _PROBABILITY_FIELDS:
        value = values[name]
        if not 0.0 <= value <= 1.0:
            fail(name, f"must be between 0 and 1, got {value}")

    for name in _TIME_FIELDS:
        if not _TIME_PATTERN.match(values[name]):
            fail(name, f"must be HH:MM in 24-hour form, got {values[name]!r}")

    for name in _NON_EMPTY_FIELDS:
        if not values[name]:
            fail(name, "must not be empty")

    for name in ("max_reactions_per_message", "llm_secret_cooldown_seconds"):
        if values[name] < 0:
            fail(name, f"must not be negative, got {values[name]}")

    unknown_emoji = [e for e in values["emoji_reaction_pool"] if e not in ALLOWED_REACTION_EMOJI]
    if unknown_emoji:
        fail(
            "emoji_reaction_pool",
            f"not Telegram-allowed reaction emoji: {unknown_emoji!r} "
            "(see app/caciarabot/config/allowed_reactions.py)",
        )

    unknown_sources = [s for s in values["digest_sources"] if s not in _KNOWN_DIGEST_SOURCES]
    if unknown_sources:
        fail(
            "digest_sources",
            f"unknown digest sources: {unknown_sources!r} "
            f"(known: {sorted(_KNOWN_DIGEST_SOURCES)})",
        )

    return errors


def bot_config_from_env(environ: Mapping[str, str]) -> tuple[BotConfig, list[ConfigError]]:
    annotations = typing.get_type_hints(BotConfig)
    errors: list[ConfigError] = []
    overrides: dict[str, object] = {}
    recognised = set(_NON_CONFIG_VARIABLES)

    for field in dataclasses.fields(BotConfig):
        variable = environment_variable_name(field.name)
        recognised.add(variable)
        raw = environ.get(variable)
        if raw is None or not raw.strip():
            continue
        try:
            overrides[field.name] = _parse(raw, annotations[field.name])
        except ValueError as exc:
            errors.append(ConfigError(file=ENV_SOURCE, field=variable, message=str(exc)))

    for variable in sorted(environ):
        if variable.startswith(ENV_PREFIX) and variable not in recognised:
            errors.append(
                ConfigError(
                    file=ENV_SOURCE,
                    field=variable,
                    message="unknown setting -- check the spelling against .env.example",
                )
            )

    if errors:
        return BotConfig(), errors

    config = BotConfig(**overrides)
    constraint_errors = _constraint_errors(dataclasses.asdict(config))
    if constraint_errors:
        return BotConfig(), constraint_errors
    return config, []
