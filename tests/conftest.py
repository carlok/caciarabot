"""Shared Runtime builder for tests that exercise the scheduler."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from caciarabot.config.models import BotConfig, LimitsConfig
from caciarabot.localization import Locales
from caciarabot.normalization import NormalizationOptions
from caciarabot.runtime import Runtime
from caciarabot.storage import connect

_BASE_BOT_CONFIG = BotConfig(
    default_locale="it",
    timezone="Europe/Rome",
    reaction_packs=(),
    max_reactions_per_message=1,
    passive_reactions=False,
    commands_enabled=False,
    llm_enabled=True,
    llm_dry_run=True,
    llm_daily_thought_enabled=True,
    # The Wikipedia branch makes a real network call; every test here is
    # about the non-link path, so keep the roll from ever succeeding.
    llm_daily_link_probability=0.0,
)


@pytest.fixture
def make_runtime(tmp_path: Path):
    def build(**overrides) -> Runtime:
        bot_config_overrides = overrides.pop("bot_config", {})
        return Runtime(
            bot_config=dataclasses.replace(_BASE_BOT_CONFIG, **bot_config_overrides),
            normalization_options=NormalizationOptions(),
            limits_config=LimitsConfig(),
            rules=[],
            locales=Locales({}, "it"),
            db=connect(tmp_path / "test.db"),
            media_dir=tmp_path,
            config_dir=tmp_path,
            owner_id=None,
            gemini_api_key="test-key",
            llm_daily_prompts=("MOOD-A", "MOOD-B", "MOOD-C", "MOOD-D"),
            llm_daily_depth_prompts=("DEPTH-A", "DEPTH-B", "DEPTH-C", "DEPTH-D"),
            llm_daily_style_prompts=("STYLE-A", "STYLE-B", "STYLE-C", "STYLE-D"),
            **overrides,
        )

    return build
