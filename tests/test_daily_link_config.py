import json
from pathlib import Path

from caciarabot.config.loader import load_bot_config


def _write_bot_jsonc(config_dir: Path, daily_thought: dict) -> None:
    (config_dir / "bot.jsonc").write_text(
        json.dumps(
            {
                "defaultLocale": "it",
                "reactionPacks": ["core-it"],
                "llm": {"dailyThought": daily_thought},
            }
        )
    )


def test_link_defaults_when_absent(tmp_path: Path):
    (tmp_path / "bot.jsonc").write_text(
        json.dumps({"defaultLocale": "it", "reactionPacks": ["core-it"]})
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.llm_daily_link_probability == 0.2
    assert bot_config.llm_daily_link_languages == ("it", "en")


def test_link_custom_values(tmp_path: Path):
    _write_bot_jsonc(
        tmp_path,
        {"enabled": True, "linkProbability": 0.5, "linkLanguages": ["it"]},
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.llm_daily_link_probability == 0.5
    assert bot_config.llm_daily_link_languages == ("it",)


def test_link_probability_above_one_is_rejected(tmp_path: Path):
    _write_bot_jsonc(tmp_path, {"enabled": True, "linkProbability": 1.5})

    _bot_config, errors = load_bot_config(tmp_path)

    assert len(errors) == 1


def test_empty_link_languages_is_rejected(tmp_path: Path):
    _write_bot_jsonc(tmp_path, {"enabled": True, "linkLanguages": []})

    _bot_config, errors = load_bot_config(tmp_path)

    assert len(errors) == 1
