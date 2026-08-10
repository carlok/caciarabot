import json
from pathlib import Path

from caciarabot.config.loader import load_bot_config


def _write_bot_jsonc(config_dir: Path, random_events: dict) -> None:
    (config_dir / "bot.jsonc").write_text(
        json.dumps(
            {
                "defaultLocale": "it",
                "reactionPacks": ["core-it"],
                "randomEvents": random_events,
            }
        )
    )


def test_valid_emoji_pool_loads(tmp_path: Path):
    _write_bot_jsonc(
        tmp_path,
        {"enabled": True, "emojiReactionProbability": 0.33, "emojiReactionPool": ["😁", "👍"]},
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.emoji_reactions_enabled is True
    assert bot_config.emoji_reaction_probability == 0.33
    assert bot_config.emoji_reaction_pool == ("😁", "👍")


def test_unknown_emoji_is_rejected(tmp_path: Path):
    _write_bot_jsonc(
        tmp_path,
        {"enabled": True, "emojiReactionProbability": 0.33, "emojiReactionPool": ["😁", "🚀"]},
    )

    _bot_config, errors = load_bot_config(tmp_path)

    assert len(errors) == 1
    assert "🚀" in errors[0].message
