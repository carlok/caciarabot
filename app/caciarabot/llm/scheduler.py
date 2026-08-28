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

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from caciarabot.engine.rotation import prompt_hash, recent_window, select_fresh_prompt
from caciarabot.llm.gemini import generate_reply
from caciarabot.llm.wikipedia import fetch_random_article
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import (
    get_awake_chat_ids,
    get_recent_prompt_hashes,
    increment_counter,
    record_prompt_use,
)


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


def _pick_rotating(
    runtime: Runtime, pool_name: str, pool: tuple[str, ...], rng: random.Random
) -> str | None:
    """Pick from a pool, biased away from what was used most recently.

    Plain random is memoryless, so the same mood could reappear the very
    next day; this records each pick and avoids the recent ones, which is
    what makes consecutive days actually feel different.
    """
    recent = get_recent_prompt_hashes(runtime.db, pool_name, recent_window(len(pool)))
    prompt = select_fresh_prompt(pool, recent, rng=rng)
    if prompt is not None:
        record_prompt_use(runtime.db, pool_name, prompt_hash(prompt))
    return prompt


async def _generate_link_thought(runtime: Runtime, rng: random.Random) -> str | None:
    """The "Wikipedia rabbit hole" variant: comment on a random article and link it.

    Returns None for any reason at all (feature off, lost the roll, no
    prompts, fetch failed, empty generation) so the caller can simply
    fall back to a normal thought -- a bad Wikipedia day never costs the
    daily post.
    """
    if not runtime.llm_daily_link_prompts:
        return None
    if rng.random() >= runtime.bot_config.llm_daily_link_probability:
        return None

    async with aiohttp.ClientSession() as session:
        article = await fetch_random_article(
            session, runtime.bot_config.llm_daily_link_languages, rng=rng
        )
    if article is None:
        return None

    prompt = _pick_rotating(runtime, "daily_link", runtime.llm_daily_link_prompts, rng)
    comment = await generate_reply(
        runtime.gemini_api_key,
        runtime.bot_config.llm_model,
        prompt,
        f"Title: {article.title}\nLanguage: {article.language}\nExtract: {article.extract}",
    )
    if not comment:
        log_event("daily_link_failed", reason="empty generation", url=article.url)
        return None

    log_event("daily_link_selected", language=article.language, url=article.url)
    return f"{comment}\n\n{article.title}\n{article.url}"


async def post_daily_thought(bot: Bot, runtime: Runtime) -> None:
    if not runtime.llm_daily_prompts or not runtime.gemini_api_key:
        return

    rng = random.Random()

    text = await _generate_link_thought(runtime, rng)

    if text is None:
        # Mood and depth are picked independently, so the pools multiply:
        # 14 moods x 4 depths is far more distinct days than either alone.
        prompt = _pick_rotating(runtime, "daily", runtime.llm_daily_prompts, rng)
        depth = _pick_rotating(runtime, "daily_depth", runtime.llm_daily_depth_prompts, rng)
        if depth:
            prompt = f"{prompt}\n\n{depth}"

        text = await generate_reply(
            runtime.gemini_api_key,
            runtime.bot_config.llm_model,
            prompt,
            "Write your thought of the day now.",
        )
    if not text:
        log_event("daily_thought_failed", reason="empty generation")
        return

    for chat_id in get_awake_chat_ids(runtime.db):
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
