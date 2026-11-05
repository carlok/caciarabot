"""Structured-ish English log lines (spec section 32): `event key=value key=value`."""

from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from caciarabot.config.models import BotConfig

logger = logging.getLogger("caciarabot")


def log_event(event: str, **fields: object) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("%s %s", event, rendered_fields)


def log_loaded_settings(bot_config: BotConfig) -> None:
    """Log every BotConfig field as the running process sees it.

    BotConfig holds behaviour knobs only; credentials (the bot token, the
    Gemini key) are read from the environment separately and never reach it.
    The fields are enumerated rather than named one by one, so a new setting
    shows up here without touching this function. CodeQL also stops flagging
    `llm_secret_probability` (a float) as a secret by name.
    """
    log_event("settings_loaded", **dataclasses.asdict(bot_config))
