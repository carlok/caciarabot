"""Daily digest orchestration: fetch (no LLM) -> pick -> comment (LLM) -> send.

Structurally mirrors llm/scheduler.py's post_daily_thought -- same
silent-disable pattern, same dryRun handling, same "broadcast to every
known chat" behavior. The digest additionally records what it sent
(digest_sent) so it doesn't repeat the same link on a later day.
"""

from __future__ import annotations

import asyncio
import random
from zoneinfo import ZoneInfo

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from caciarabot.digest.language import looks_non_english, page_is_english
from caciarabot.digest.picker import normalize_url_hash, pick_candidate
from caciarabot.digest.sources import Candidate, fetch_all
from caciarabot.llm.gemini import generate_reply
from caciarabot.llm.scheduler import seconds_until_next
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import (
    get_awake_chat_ids,
    get_recent_digest_hashes,
    increment_counter,
    record_digest_sent,
)


async def run_digest_loop(bot: Bot, runtime: Runtime) -> None:
    tz = ZoneInfo(runtime.bot_config.timezone)

    while True:
        delay = seconds_until_next(runtime.bot_config.digest_time, tz)
        await asyncio.sleep(delay)
        await post_digest(bot, runtime)


# The chat reads Italian and English. A Chinese README or a French blog
# post is noise here, so the pool is filtered on metadata (free) and the
# picked link is then verified against the real page (one request).
_MAXIMUM_LANGUAGE_CHECKS = 5


def _drop_non_english_metadata(candidates: list[Candidate]) -> list[Candidate]:
    kept = [c for c in candidates if not looks_non_english(f"{c.title}\n{c.excerpt}")]
    if len(kept) != len(candidates):
        log_event("digest_language_filtered", stage="metadata", removed=len(candidates) - len(kept))
    return kept


async def _pick_readable(
    session: aiohttp.ClientSession,
    runtime: Runtime,
    candidates: list[Candidate],
    already_sent: set[str],
) -> Candidate | None:
    """Picks a candidate whose target page isn't in another language.

    Verifying the whole pool would mean fifty requests for one link, so
    only the picked candidate is fetched; a rejection drops it and draws
    again. An undetermined verdict counts as acceptable -- rejecting on
    missing evidence would thin the pool for no gain.
    """
    rejected: set[str] = set()
    for _ in range(_MAXIMUM_LANGUAGE_CHECKS):
        pool = [c for c in candidates if c.url not in rejected]
        candidate = pick_candidate(pool, already_sent)
        if candidate is None:
            return None
        if not runtime.bot_config.digest_english_only:
            return candidate

        if await page_is_english(session, candidate.url) is False:
            log_event("digest_language_rejected", stage="page", url=candidate.url)
            rejected.add(candidate.url)
            continue
        return candidate
    return None


async def post_digest(bot: Bot, runtime: Runtime) -> None:
    if not runtime.bot_config.digest_enabled or not runtime.gemini_api_key:
        return
    if not runtime.llm_digest_prompts:
        log_event("digest_failed", reason="no prompts loaded")
        return

    async with aiohttp.ClientSession() as session:
        candidates = await fetch_all(
            session, runtime.bot_config.digest_sources, runtime.bot_config.digest_reddit_subs
        )

        if not candidates:
            log_event("digest_skipped", reason="no_candidates")
            return

        if runtime.bot_config.digest_english_only:
            candidates = _drop_non_english_metadata(candidates)
            if not candidates:
                log_event("digest_skipped", reason="no_english_candidates")
                return

        already_sent = get_recent_digest_hashes(runtime.db)
        candidate = await _pick_readable(session, runtime, candidates, already_sent)

    if candidate is None:
        log_event("digest_skipped", reason="no_eligible_candidate")
        return

    prompt = random.choice(runtime.llm_digest_prompts)
    user_message = f"Title: {candidate.title}\nSource: {candidate.source}\nURL: {candidate.url}"
    if candidate.excerpt:
        user_message += f"\nExcerpt: {candidate.excerpt}"

    comment = await generate_reply(runtime.gemini_api_key, runtime.bot_config.llm_model, prompt, user_message)
    if not comment:
        log_event("digest_failed", reason="empty generation", url=candidate.url)
        return

    text = f"\U0001f4f0 {candidate.title}\n{candidate.url}\n\n{comment}\n\n— fonte: {candidate.source}"

    url_hash = normalize_url_hash(candidate.url)
    record_digest_sent(runtime.db, url_hash, candidate.url, candidate.title, candidate.source)

    for chat_id in get_awake_chat_ids(runtime.db):
        if runtime.bot_config.llm_dry_run:
            log_event("digest_dry_run", chat_id=chat_id, text=text)
            increment_counter(runtime.db, "global", "digests_sent")
            continue

        try:
            await bot.send_message(chat_id, text, disable_notification=True)
        except TelegramAPIError as exc:
            log_event("digest_send_failed", chat_id=chat_id, reason=str(exc))
            continue
        increment_counter(runtime.db, "global", "digests_sent")
        log_event("digest_sent", chat_id=chat_id, url=candidate.url)
