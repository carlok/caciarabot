"""The daily thought is assembled from three independent pools.

Mood alone was not enough: the model kept landing in the same lyrical
register every morning, so diction became its own dimension. These tests
pin down that all three actually reach the prompt, and that consecutive
days differ on every one of them.
"""

import asyncio
from pathlib import Path

import pytest

from caciarabot.config.models import BotConfig, LimitsConfig
from caciarabot.llm import scheduler
from caciarabot.localization import Locales
from caciarabot.normalization import NormalizationOptions
from caciarabot.runtime import Runtime
from caciarabot.storage import connect


def _runtime(tmp_path: Path) -> Runtime:
    return Runtime(
        bot_config=BotConfig(
            default_locale="it",
            timezone="Europe/Rome",
            reaction_packs=(),
            max_reactions_per_message=1,
            passive_reactions=False,
            commands_enabled=False,
            llm_enabled=True,
            llm_dry_run=True,
            llm_daily_thought_enabled=True,
            llm_daily_link_probability=0.0,
        ),
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
    )


def _run_days(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, days: int) -> list[str]:
    seen: list[str] = []

    async def fake_generate(_key, _model, prompt, _user_text):
        seen.append(prompt)
        return "pensiero"

    monkeypatch.setattr(scheduler, "generate_reply", fake_generate)
    runtime = _runtime(tmp_path)
    for _ in range(days):
        asyncio.run(scheduler.post_daily_thought(object(), runtime))
    return seen


def test_prompt_carries_mood_depth_and_style(tmp_path, monkeypatch):
    (prompt,) = _run_days(tmp_path, monkeypatch, 1)
    assert any(f"MOOD-{c}" in prompt for c in "ABCD")
    assert any(f"DEPTH-{c}" in prompt for c in "ABCD")
    assert any(f"STYLE-{c}" in prompt for c in "ABCD")


def test_consecutive_days_change_every_dimension(tmp_path, monkeypatch):
    prompts = _run_days(tmp_path, monkeypatch, 6)

    def picked(prompt: str, prefix: str) -> str:
        return next(c for c in "ABCD" if f"{prefix}-{c}" in prompt)

    for prefix in ("MOOD", "DEPTH", "STYLE"):
        chosen = [picked(p, prefix) for p in prompts]
        for earlier, later in zip(chosen, chosen[1:]):
            assert earlier != later, f"{prefix} repeated on consecutive days: {chosen}"
