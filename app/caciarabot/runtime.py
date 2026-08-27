"""Composition root's runtime object: everything a handler needs, assembled once at startup."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from caciarabot.config.models import BotConfig, LimitsConfig, ReactionRule
from caciarabot.localization import Locales
from caciarabot.normalization import NormalizationOptions


@dataclass(slots=True)
class Runtime:
    bot_config: BotConfig
    normalization_options: NormalizationOptions
    limits_config: LimitsConfig
    rules: list[ReactionRule]
    locales: Locales
    db: sqlite3.Connection
    media_dir: Path
    config_dir: Path
    owner_id: int | None
    gemini_api_key: str | None = None
    llm_reply_prompts: tuple[str, ...] = ()
    llm_daily_prompts: tuple[str, ...] = ()
    llm_daily_link_prompts: tuple[str, ...] = ()
    llm_cited_prompts: tuple[str, ...] = ()
    llm_digest_prompts: tuple[str, ...] = ()
    llm_secret_prompts: tuple[str, ...] = ()
    bot_id: int | None = None
    bot_username: str | None = None
