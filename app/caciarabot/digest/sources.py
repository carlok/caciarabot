"""Deterministic candidate sourcing — no LLM involved anywhere in this file.

Each fetcher is a thin async HTTP shell around a pure `_parse_*` function,
so parsing is testable against fixture JSON with zero network access. A
fetcher never raises: a failing source just contributes an empty list,
never breaks the digest for the other sources.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import aiohttp

from caciarabot.logging_utils import log_event

_REQUEST_TIMEOUT_SECONDS = 10
_USER_AGENT = "caciarabot/1.0 (self-hosted Telegram bot; +https://github.com/carlok/caciarabot)"


@dataclass(frozen=True, slots=True)
class Candidate:
    source: str
    title: str
    url: str
    excerpt: str = ""


def _parse_hackernews(data: dict) -> list[Candidate]:
    candidates = []
    for hit in data.get("hits", []):
        title = hit.get("title")
        object_id = hit.get("objectID")
        if not title or not object_id:
            continue
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
        excerpt = (hit.get("story_text") or "").strip()
        candidates.append(Candidate(source="hackernews", title=title, url=url, excerpt=excerpt))
    return candidates


async def fetch_hackernews(session: aiohttp.ClientSession) -> list[Candidate]:
    url = "https://hn.algolia.com/api/v1/search?tags=front_page"
    try:
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
        async with session.get(url, timeout=timeout) as response:
            if response.status != 200:
                log_event("digest_source_failed", source="hackernews", status=response.status)
                return []
            data = await response.json()
    except (aiohttp.ClientError, TimeoutError) as exc:
        log_event("digest_source_failed", source="hackernews", reason=str(exc))
        return []
    return _parse_hackernews(data)


def _parse_github_trending(data: dict) -> list[Candidate]:
    candidates = []
    for item in data.get("items", []):
        full_name = item.get("full_name")
        html_url = item.get("html_url")
        if not full_name or not html_url:
            continue
        excerpt = (item.get("description") or "").strip()
        candidates.append(
            Candidate(source="github_trending", title=full_name, url=html_url, excerpt=excerpt)
        )
    return candidates


async def fetch_github_trending(session: aiohttp.ClientSession) -> list[Candidate]:
    since = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    query = f"created:>{since} stars:>50"
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc"}
    try:
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
        async with session.get(url, params=params, timeout=timeout) as response:
            if response.status != 200:
                log_event("digest_source_failed", source="github_trending", status=response.status)
                return []
            data = await response.json()
    except (aiohttp.ClientError, TimeoutError) as exc:
        log_event("digest_source_failed", source="github_trending", reason=str(exc))
        return []
    return _parse_github_trending(data)


def _parse_reddit(data: dict) -> list[Candidate]:
    candidates = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = post.get("title")
        permalink = post.get("permalink")
        if not title or not permalink:
            continue
        is_self = post.get("is_self", False)
        url = f"https://www.reddit.com{permalink}" if is_self else post.get("url") or ""
        if not url:
            continue
        excerpt = (post.get("selftext") or "").strip()[:500]
        candidates.append(Candidate(source="reddit", title=title, url=url, excerpt=excerpt))
    return candidates


async def fetch_reddit(session: aiohttp.ClientSession, subs: tuple[str, ...]) -> list[Candidate]:
    """Not enabled by default (config/models.py) -- verified live that
    reddit's public .json endpoints commonly return a 403 bot-challenge
    page to unauthenticated non-browser clients regardless of User-Agent
    content. A working integration would need Reddit OAuth (script-type
    app credentials), out of scope for this v1. Kept here, and still
    fails gracefully like the other sources, for anyone who opts in with
    a setup that works for them."""
    candidates: list[Candidate] = []
    headers = {"User-Agent": _USER_AGENT}
    timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
    for sub in subs:
        url = f"https://www.reddit.com/r/{sub}/top.json"
        params = {"t": "day", "limit": 30}
        try:
            async with session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    log_event("digest_source_failed", source="reddit", sub=sub, status=response.status)
                    continue
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            log_event("digest_source_failed", source="reddit", sub=sub, reason=str(exc))
            continue
        candidates.extend(_parse_reddit(data))
    return candidates


_FETCHERS = {
    "hackernews": lambda session, reddit_subs: fetch_hackernews(session),
    "github_trending": lambda session, reddit_subs: fetch_github_trending(session),
    "reddit": lambda session, reddit_subs: fetch_reddit(session, reddit_subs),
}


async def fetch_all(
    session: aiohttp.ClientSession, enabled_sources: tuple[str, ...], reddit_subs: tuple[str, ...]
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for source_name in enabled_sources:
        fetcher = _FETCHERS.get(source_name)
        if fetcher is None:
            continue
        candidates.extend(await fetcher(session, reddit_subs))
    return candidates
