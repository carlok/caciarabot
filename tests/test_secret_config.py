import json
from pathlib import Path

from caciarabot.config.loader import load_bot_config


def test_cited_trigger_words_default_to_caciara(tmp_path: Path):
    (tmp_path / "bot.jsonc").write_text(
        json.dumps({"defaultLocale": "it", "reactionPacks": ["core-it"]})
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.llm_cited_trigger_words == ("caciara",)


def test_cited_trigger_words_custom(tmp_path: Path):
    (tmp_path / "bot.jsonc").write_text(
        json.dumps(
            {
                "defaultLocale": "it",
                "reactionPacks": ["core-it"],
                "llm": {"citedReply": {"enabled": True, "triggerWords": ["caciara", "boh"]}},
            }
        )
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.llm_cited_trigger_words == ("caciara", "boh")


def test_secret_defaults(tmp_path: Path):
    (tmp_path / "bot.jsonc").write_text(
        json.dumps({"defaultLocale": "it", "reactionPacks": ["core-it"]})
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.llm_secret_enabled is False
    assert bot_config.llm_secret_probability == 0.0
    assert bot_config.llm_secret_cooldown_seconds == 1800


def test_secret_custom_values(tmp_path: Path):
    (tmp_path / "bot.jsonc").write_text(
        json.dumps(
            {
                "defaultLocale": "it",
                "reactionPacks": ["core-it"],
                "llm": {"secret": {"enabled": True, "probability": 0.5, "cooldownSeconds": 60}},
            }
        )
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.llm_secret_enabled is True
    assert bot_config.llm_secret_probability == 0.5
    assert bot_config.llm_secret_cooldown_seconds == 60
