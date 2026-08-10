"""In-process daily scheduler for the "thought of the day" LLM post.

Runs as a plain asyncio task alongside aiogram's polling loop rather
than a host-level cron job: this bot is a single long-running process
in one container, and a background asyncio loop gets the same "once a
day" behavior with no second container, systemd timer, or separate
script invocation to deploy and keep in sync with the running bot.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from caciarabot.llm.gemini import generate_reply
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import get_all_chat_ids, increment_counter


def seconds_until_next(time_str: str, tz: ZoneInfo, now: datetime | None = None) -> float:
    hour, minute = (int(part) for part in time_str.split(":"))
    current = now or datetime.now(tz)
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return (target - current).total_seconds()


async def run_daily_thought_loop(bot: Bot, runtime: Runtime) -> None:
    tz = ZoneInfo(runtime.bot_config.timezone)

    while True:
        delay = seconds_until_next(runtime.bot_config.llm_daily_thought_time, tz)
        await asyncio.sleep(delay)
        await post_daily_thought(bot, runtime)


async def post_daily_thought(bot: Bot, runtime: Runtime) -> None:
    if not runtime.llm_daily_prompts or not runtime.gemini_api_key:
        return

    prompt = random.choice(runtime.llm_daily_prompts)
    text = await generate_reply(
        runtime.gemini_api_key,
        runtime.bot_config.llm_model,
        prompt,
        "Write your thought of the day now.",
    )
    if not text:
        log_event("daily_thought_failed", reason="empty generation")
        return

    for chat_id in get_all_chat_ids(runtime.db):
        if runtime.bot_config.llm_dry_run:
            log_event("daily_thought_dry_run", chat_id=chat_id, text=text)
            increment_counter(runtime.db, "global", "daily_thoughts_sent")
            continue

        try:
            await bot.send_message(chat_id, text)
        except TelegramAPIError as exc:
            log_event("daily_thought_send_failed", chat_id=chat_id, reason=str(exc))
            continue
        increment_counter(runtime.db, "global", "daily_thoughts_sent")
        log_event("daily_thought_sent", chat_id=chat_id)
