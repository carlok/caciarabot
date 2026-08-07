"""Loads and validates the JSONC global configuration files."""

from __future__ import annotations

from pathlib import Path

from caciarabot.config.errors import ConfigError, ConfigValidationError
from caciarabot.config.jsonc import load_jsonc
from caciarabot.config.models import BotConfig, LimitsConfig, normalization_options_from_dict
from caciarabot.config.validation import validate_instance
from caciarabot.normalization import NormalizationOptions


def load_bot_config(config_dir: Path) -> tuple[BotConfig, list[ConfigError]]:
    path = config_dir / "bot.jsonc"
    data = load_jsonc(path)
    errors = validate_instance(data, "bot.schema.json", str(path))
    if errors:
        return _empty_bot_config(), errors

    return (
        BotConfig(
            default_locale=data["defaultLocale"],
            timezone=data.get("timezone", "UTC"),
            reaction_packs=tuple(data["reactionPacks"]),
            max_reactions_per_message=data.get("maxReactionsPerMessage", 1),
            passive_reactions=data.get("passiveReactions", True),
            commands_enabled=data.get("commands", {}).get("enabled", True),
        ),
        [],
    )


def load_normalization_config(config_dir: Path) -> tuple[NormalizationOptions, list[ConfigError]]:
    path = config_dir / "normalization.jsonc"
    data = load_jsonc(path)
    errors = validate_instance(data, "normalization.schema.json", str(path))
    if errors:
        return NormalizationOptions(), errors

    options = normalization_options_from_dict(data) or NormalizationOptions()
    return options, []


def load_limits_config(config_dir: Path) -> tuple[LimitsConfig, list[ConfigError]]:
    path = config_dir / "limits.jsonc"
    data = load_jsonc(path)
    errors = validate_instance(data, "limits.schema.json", str(path))
    if errors:
        return LimitsConfig(), errors

    return (
        LimitsConfig(
            minimum_chat_interval_seconds=data.get("minimumChatIntervalSeconds", 0),
            maximum_passive_reactions_per_10_minutes=data.get(
                "maximumPassiveReactionsPer10Minutes", 0
            ),
        ),
        [],
    )


def _empty_bot_config() -> BotConfig:
    return BotConfig(
        default_locale="it",
        timezone="UTC",
        reaction_packs=(),
        max_reactions_per_message=1,
        passive_reactions=True,
        commands_enabled=True,
    )


def load_global_config(
    config_dir: Path,
) -> tuple[BotConfig, NormalizationOptions, LimitsConfig, list[ConfigError]]:
    all_errors: list[ConfigError] = []

    bot_config, errors = load_bot_config(config_dir)
    all_errors.extend(errors)

    normalization_options, errors = load_normalization_config(config_dir)
    all_errors.extend(errors)

    limits_config, errors = load_limits_config(config_dir)
    all_errors.extend(errors)

    if all_errors:
        raise ConfigValidationError(all_errors)

    return bot_config, normalization_options, limits_config, []
