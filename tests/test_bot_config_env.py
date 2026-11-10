"""Bot settings come from the environment, not from a config file.

These replace the four per-feature bot.jsonc test modules: with a single
loader and a single source, splitting them by feature no longer bought
anything.
"""

import dataclasses

import pytest
from caciarabot.config.env import (
    bot_config_from_env,
    environment_variable_name,
    llm_api_key_from_env,
)
from caciarabot.config.models import BotConfig
from caciarabot.llm.chat_completions import DEFAULT_BASE_URL


def test_empty_environment_gives_a_usable_default_deployment():
    config, errors = bot_config_from_env({})

    assert errors == []
    assert config == BotConfig()
    assert config.default_locale == "it"
    assert config.reaction_packs == ("core-it", "custom")
    assert config.llm_enabled is False


def test_every_field_has_a_variable_and_none_of_them_collide():
    names = [environment_variable_name(f.name) for f in dataclasses.fields(BotConfig)]

    assert len(names) == len(set(names))
    assert "CACIARABOT_LLM_DAILY_THOUGHT_TIME" in names


@pytest.mark.parametrize("raw", ["true", "TRUE", "1", "yes", "on"])
def test_booleans_accept_the_usual_spellings(raw):
    config, errors = bot_config_from_env({"CACIARABOT_LLM_ENABLED": raw})

    assert errors == []
    assert config.llm_enabled is True


@pytest.mark.parametrize("raw", ["false", "0", "no", "off"])
def test_booleans_accept_the_usual_negative_spellings(raw):
    config, errors = bot_config_from_env({"CACIARABOT_PASSIVE_REACTIONS": raw})

    assert errors == []
    assert config.passive_reactions is False


def test_nonsense_boolean_is_rejected():
    _config, errors = bot_config_from_env({"CACIARABOT_LLM_ENABLED": "maybe"})

    assert len(errors) == 1
    assert errors[0].field == "CACIARABOT_LLM_ENABLED"


def test_lists_are_comma_separated_and_tolerate_spacing():
    config, errors = bot_config_from_env(
        {"CACIARABOT_LLM_CITED_TRIGGER_WORDS": " caciara , boh ,"}
    )

    assert errors == []
    assert config.llm_cited_trigger_words == ("caciara", "boh")


def test_blank_variable_is_treated_as_unset():
    config, errors = bot_config_from_env({"CACIARABOT_DEFAULT_LOCALE": "   "})

    assert errors == []
    assert config.default_locale == "it"


def test_numbers_and_times_round_trip():
    config, errors = bot_config_from_env(
        {
            "CACIARABOT_LLM_SECRET_PROBABILITY": "0.5",
            "CACIARABOT_LLM_SECRET_COOLDOWN_SECONDS": "60",
            "CACIARABOT_DIGEST_TIME": "08:30",
        }
    )

    assert errors == []
    assert config.llm_secret_probability == 0.5
    assert config.llm_secret_cooldown_seconds == 60
    assert config.digest_time == "08:30"


def test_probability_out_of_range_is_rejected():
    _config, errors = bot_config_from_env({"CACIARABOT_LLM_DAILY_LINK_PROBABILITY": "1.5"})

    assert len(errors) == 1
    assert "between 0 and 1" in errors[0].message


def test_malformed_time_is_rejected():
    _config, errors = bot_config_from_env({"CACIARABOT_DIGEST_TIME": "25:99"})

    assert len(errors) == 1
    assert errors[0].field == "CACIARABOT_DIGEST_TIME"


def test_valid_emoji_pool_loads():
    config, errors = bot_config_from_env(
        {
            "CACIARABOT_EMOJI_REACTIONS_ENABLED": "true",
            "CACIARABOT_EMOJI_REACTION_PROBABILITY": "0.33",
            "CACIARABOT_EMOJI_REACTION_POOL": "😁,👍",
        }
    )

    assert errors == []
    assert config.emoji_reactions_enabled is True
    assert config.emoji_reaction_probability == 0.33
    assert config.emoji_reaction_pool == ("😁", "👍")


def test_emoji_outside_telegrams_reaction_set_is_rejected():
    _config, errors = bot_config_from_env({"CACIARABOT_EMOJI_REACTION_POOL": "😁,🚀"})

    assert len(errors) == 1
    assert "🚀" in errors[0].message


def test_unknown_digest_source_is_rejected():
    _config, errors = bot_config_from_env({"CACIARABOT_DIGEST_SOURCES": "not_a_real_source"})

    assert len(errors) == 1
    assert "not_a_real_source" in errors[0].message


def test_empty_list_that_must_not_be_empty_is_rejected():
    _config, errors = bot_config_from_env({"CACIARABOT_REACTION_PACKS": ","})

    assert len(errors) == 1
    assert errors[0].field == "CACIARABOT_REACTION_PACKS"


def test_misspelled_variable_is_reported_rather_than_ignored():
    """The whole point of the old JSON Schema's additionalProperties: false."""
    _config, errors = bot_config_from_env({"CACIARABOT_LLM_ENABLE": "true"})

    assert len(errors) == 1
    assert "CACIARABOT_LLM_ENABLE" == errors[0].field
    assert "unknown setting" in errors[0].message


def test_path_and_owner_variables_are_not_mistaken_for_typos():
    _config, errors = bot_config_from_env(
        {
            "CACIARABOT_CONFIG_DIR": "/config",
            "CACIARABOT_MEDIA_DIR": "/media",
            "CACIARABOT_DATA_DIR": "/data",
            "CACIARABOT_OWNER_ID": "12345",
        }
    )

    assert errors == []


def test_env_example_documents_every_setting():
    """The example file is now the only place these are written down."""
    from pathlib import Path

    documented = Path(__file__).resolve().parents[1].joinpath(".env.example").read_text()
    undocumented = [
        environment_variable_name(field.name)
        for field in dataclasses.fields(BotConfig)
        if environment_variable_name(field.name) not in documented
    ]

    assert undocumented == []


def test_llm_base_url_defaults_to_gemini_openai_endpoint():
    config, errors = bot_config_from_env({})

    assert errors == []
    assert config.llm_base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_llm_base_url_can_point_elsewhere():
    config, errors = bot_config_from_env({"CACIARABOT_LLM_BASE_URL": "http://localhost:11434/v1"})

    assert errors == []
    assert config.llm_base_url == "http://localhost:11434/v1"


def test_llm_base_url_must_be_an_http_url():
    _, errors = bot_config_from_env({"CACIARABOT_LLM_BASE_URL": "api.openai.com/v1"})

    assert [error.field for error in errors] == ["CACIARABOT_LLM_BASE_URL"]


def test_api_key_prefers_llm_api_key():
    environ = {"LLM_API_KEY": "new", "GEMINI_API_KEY": "old"}

    assert llm_api_key_from_env(environ, "https://api.openai.com/v1") == "new"
    assert llm_api_key_from_env(environ, DEFAULT_BASE_URL) == "new"


def test_gemini_key_is_used_only_against_gemini():
    environ = {"GEMINI_API_KEY": "old"}

    assert llm_api_key_from_env(environ, DEFAULT_BASE_URL) == "old"
    assert llm_api_key_from_env(environ, "https://api.openai.com/v1") is None


def test_blank_keys_count_as_unset():
    assert llm_api_key_from_env({"LLM_API_KEY": " ", "GEMINI_API_KEY": ""}, DEFAULT_BASE_URL) is None
