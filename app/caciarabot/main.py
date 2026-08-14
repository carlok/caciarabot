"""Composition root: loads configuration, wires up storage and Telegram, starts polling."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from caciarabot.bootstrap import load_configuration
from caciarabot.digest import run_digest_loop
from caciarabot.llm import load_prompt_pool, run_daily_thought_loop
from caciarabot.localization import load_locales
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import connect
from caciarabot.telegram import router


def _env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


async def _main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        sys.exit(1)

    config_dir = _env_path("CACIARABOT_CONFIG_DIR", "config")
    media_dir = _env_path("CACIARABOT_MEDIA_DIR", "media")
    data_dir = _env_path("CACIARABOT_DATA_DIR", "data")

    owner_id_raw = os.environ.get("CACIARABOT_OWNER_ID")
    owner_id = int(owner_id_raw) if owner_id_raw else None

    bot_config, normalization_options, limits_config, rules, errors = load_configuration(config_dir)
    if errors:
        print("Configuration is invalid:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        sys.exit(1)

    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if bot_config.llm_enabled and not gemini_api_key:
        print(
            "config/bot.jsonc has llm.enabled=true but GEMINI_API_KEY is not set in the environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    llm_reply_prompts = load_prompt_pool(config_dir / "prompts" / "replies")
    llm_daily_prompts = load_prompt_pool(config_dir / "prompts" / "daily")
    llm_cited_prompts = load_prompt_pool(config_dir / "prompts" / "cited")
    llm_digest_prompts = load_prompt_pool(config_dir / "prompts" / "digest")
    llm_secret_prompts = load_prompt_pool(config_dir / "prompts" / "secret")

    locales = load_locales(Path("locales"), bot_config.default_locale)
    db = connect(data_dir / "caciarabot.db")

    bot = Bot(token=token)
    me = await bot.get_me()

    runtime = Runtime(
        bot_config=bot_config,
        normalization_options=normalization_options,
        limits_config=limits_config,
        rules=rules,
        locales=locales,
        db=db,
        media_dir=media_dir,
        owner_id=owner_id,
        gemini_api_key=gemini_api_key,
        llm_reply_prompts=llm_reply_prompts,
        llm_daily_prompts=llm_daily_prompts,
        llm_cited_prompts=llm_cited_prompts,
        llm_digest_prompts=llm_digest_prompts,
        llm_secret_prompts=llm_secret_prompts,
        bot_id=me.id,
        bot_username=me.username,
    )

    log_event(
        "startup",
        reaction_rules=len(rules),
        reaction_packs=len(bot_config.reaction_packs),
        bot_username=me.username,
    )

    dp = Dispatcher()
    dp.include_router(router)

    if bot_config.llm_enabled and bot_config.llm_daily_thought_enabled:
        asyncio.create_task(run_daily_thought_loop(bot, runtime))

    if bot_config.llm_enabled and bot_config.digest_enabled:
        asyncio.create_task(run_digest_loop(bot, runtime))

    await dp.start_polling(bot, runtime=runtime)


def run() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run()
