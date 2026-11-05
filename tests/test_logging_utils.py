import dataclasses
import logging

from caciarabot.config.models import BotConfig
from caciarabot.logging_utils import log_loaded_settings


def test_loaded_settings_line_carries_every_field(caplog):
    config = BotConfig(llm_reply_probability=0.05, llm_secret_probability=0.02)

    with caplog.at_level(logging.INFO, logger="caciarabot"):
        log_loaded_settings(config)

    line = caplog.records[-1].getMessage()
    assert line.startswith("settings_loaded ")
    for field in dataclasses.fields(BotConfig):
        assert f"{field.name}=" in line
    assert "llm_reply_probability=0.05" in line
    assert "llm_secret_probability=0.02" in line
