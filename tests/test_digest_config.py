import json
from pathlib import Path

from caciarabot.config.loader import load_bot_config


def _write_bot_jsonc(config_dir: Path, digest: dict) -> None:
    (config_dir / "bot.jsonc").write_text(
        json.dumps(
            {
                "defaultLocale": "it",
                "reactionPacks": ["core-it"],
                "llm": {"digest": digest},
            }
        )
    )


def test_digest_defaults_when_section_absent(tmp_path: Path):
    (tmp_path / "bot.jsonc").write_text(
        json.dumps({"defaultLocale": "it", "reactionPacks": ["core-it"]})
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.digest_enabled is False
    assert bot_config.digest_time == "08:00"
    assert bot_config.digest_sources == ("hackernews", "github_trending")
    assert bot_config.digest_reddit_subs == ("programming",)


def test_digest_config_parses_custom_values(tmp_path: Path):
    _write_bot_jsonc(
        tmp_path,
        {
            "enabled": True,
            "time": "07:30",
            "sources": ["hackernews", "reddit"],
            "redditSubs": ["compsci", "rust"],
        },
    )

    bot_config, errors = load_bot_config(tmp_path)

    assert errors == []
    assert bot_config.digest_enabled is True
    assert bot_config.digest_time == "07:30"
    assert bot_config.digest_sources == ("hackernews", "reddit")
    assert bot_config.digest_reddit_subs == ("compsci", "rust")


def test_digest_rejects_unknown_source(tmp_path: Path):
    _write_bot_jsonc(tmp_path, {"enabled": True, "sources": ["not_a_real_source"]})

    _bot_config, errors = load_bot_config(tmp_path)

    assert len(errors) == 1


def test_digest_rejects_bad_time_format(tmp_path: Path):
    _write_bot_jsonc(tmp_path, {"enabled": True, "time": "25:99"})

    _bot_config, errors = load_bot_config(tmp_path)

    assert len(errors) == 1
