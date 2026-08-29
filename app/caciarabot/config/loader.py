"""Loads and validates the global configuration.

The bot settings come from the environment (config/env.py); the two
remaining files here describe behaviour that is the same on every
deployment, so they stay tracked JSONC.
"""

from __future__ import annotations

import os
from pathlib import Path

from caciarabot.config.env import bot_config_from_env
from caciarabot.config.errors import ConfigError, ConfigValidationError
from caciarabot.config.jsonc import load_jsonc
from caciarabot.config.models import BotConfig, LimitsConfig, normalization_options_from_dict
from caciarabot.config.validation import validate_instance
from caciarabot.normalization import NormalizationOptions


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


def load_global_config(
    config_dir: Path,
) -> tuple[BotConfig, NormalizationOptions, LimitsConfig, list[ConfigError]]:
    all_errors: list[ConfigError] = []

    bot_config, errors = bot_config_from_env(os.environ)
    all_errors.extend(errors)

    normalization_options, errors = load_normalization_config(config_dir)
    all_errors.extend(errors)

    limits_config, errors = load_limits_config(config_dir)
    all_errors.extend(errors)

    if all_errors:
        raise ConfigValidationError(all_errors)

    return bot_config, normalization_options, limits_config, []
