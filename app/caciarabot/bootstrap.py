"""Shared configuration-loading logic used by both the running bot and the validator.

Loading is transactional in spirit: every file is parsed and validated
first, and only if the whole set is error-free does the caller get a
usable result — a malformed reaction rule must not start the bot with
half a configuration (spec section 27).
"""

from __future__ import annotations

from pathlib import Path

from caciarabot.config.errors import ConfigError, ConfigValidationError
from caciarabot.config.loader import load_global_config
from caciarabot.config.models import BotConfig, LimitsConfig, ReactionRule
from caciarabot.config.reactions import load_reaction_pack
from caciarabot.llm.prompts import load_prompt_pool
from caciarabot.normalization import NormalizationOptions

_PROMPT_POOL_NAMES = (
    "replies",
    "daily",
    "daily_depth",
    "daily_style",
    "daily_link",
    "cited",
    "digest",
    "secret",
)

_EMPTY_BOT_CONFIG = BotConfig(
    default_locale="it",
    timezone="UTC",
    reaction_packs=(),
    max_reactions_per_message=1,
    passive_reactions=True,
    commands_enabled=True,
)


def load_reaction_rules(
    config_dir: Path, bot_config: BotConfig
) -> tuple[list[ReactionRule], list[ConfigError]]:
    all_rules: list[ReactionRule] = []
    all_errors: list[ConfigError] = []
    seen_ids: dict[str, str] = {}

    for pack_name in bot_config.reaction_packs:
        pack_dir = config_dir / "packs" / pack_name
        if not pack_dir.is_dir():
            all_errors.append(
                ConfigError(file=str(pack_dir), message=f"reaction pack directory not found: {pack_name}")
            )
            continue

        rules, errors = load_reaction_pack(pack_dir)
        all_errors.extend(errors)

        for rule in rules:
            if rule.id in seen_ids:
                all_errors.append(
                    ConfigError(
                        file=rule.source_file,
                        line=rule.source_line,
                        message=f"duplicate reaction id {rule.id!r} (also defined in {seen_ids[rule.id]})",
                        record_id=rule.id,
                    )
                )
                continue
            seen_ids[rule.id] = rule.source_file
            all_rules.append(rule)

    return all_rules, all_errors


def load_configuration(
    config_dir: Path,
) -> tuple[BotConfig, NormalizationOptions, LimitsConfig, list[ReactionRule], list[ConfigError]]:
    try:
        bot_config, normalization_options, limits_config, _ = load_global_config(config_dir)
    except ConfigValidationError as exc:
        return _EMPTY_BOT_CONFIG, NormalizationOptions(), LimitsConfig(), [], exc.errors

    rules, rule_errors = load_reaction_rules(config_dir, bot_config)
    return bot_config, normalization_options, limits_config, rules, rule_errors


def load_prompt_pools(config_dir: Path) -> dict[str, tuple[str, ...]]:
    """Loads every named prompt pool (replies/daily/cited/digest/secret).

    Shared between startup (main.py) and /reload so both build the pool
    set the exact same way.
    """
    return {name: load_prompt_pool(config_dir / "prompts" / name) for name in _PROMPT_POOL_NAMES}
