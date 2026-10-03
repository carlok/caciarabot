"""Random Wikipedia article fetching for the daily-thought link variant.

No LLM involved here -- this is deterministic sourcing, same split as
digest/sources.py: a thin async HTTP shell around a pure `_parse_summary`
so parsing is testable against fixture JSON with no network access, and
a fetcher that never raises (a failure just means no link today, and the
caller falls back to a normal daily thought).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Literal

import aiohttp

from caciarabot.logging_utils import log_event

_REQUEST_TIMEOUT_SECONDS = 10
_USER_AGENT = "caciarabot/1.0 (self-hosted Telegram bot; +https://github.com/carlok/caciarabot)"

# English Wikipedia in particular serves a lot of one-line stubs (gene
# entries, tiny localities) that give the model nothing to react to.
_MINIMUM_EXTRACT_CHARS = 150
_MAX_ATTEMPTS = 3
_MAX_FILTERED_ATTEMPTS = 10

TopicFilter = Literal["any", "technical", "nontechnical"]

_TECHNICAL_PATTERN = re.compile(
    r"\b("
    r"software|computer|computing|programming|programmer|algorithm|"
    r"javascript|typescript|python|java|golang|rust|linux|"
    r"kernel|database|cryptocurrency|bitcoin|blockchain|"
    r"semiconductor|microprocessor|"
    r"artificial intelligence|machine learning|neural network|"
    r"open.?source|github|kubernetes|docker|"
    r"cybersecurity|hacker"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Article:
    title: str
    extract: str
    url: str
    language: str


def looks_technical(title: str, extract: str) -> bool:
    """Heuristic: True when the article is clearly about technology."""
    haystack = f"{title}\n{extract}"
    return _TECHNICAL_PATTERN.search(haystack) is not None


def _matches_topic(title: str, extract: str, topic: TopicFilter) -> bool:
    if topic == "any":
        return True
    technical = looks_technical(title, extract)
    if topic == "technical":
        return technical
    return not technical


def _parse_summary(data: dict, language: str) -> Article | None:
    title = data.get("title")
    extract = (data.get("extract") or "").strip()
    url = data.get("content_urls", {}).get("desktop", {}).get("page")

    if not title or not url or len(extract) < _MINIMUM_EXTRACT_CHARS:
        return None

    return Article(title=title, extract=extract, url=url, language=language)


async def fetch_random_article(
    session: aiohttp.ClientSession,
    languages: tuple[str, ...],
    rng: random.Random | None = None,
    topic: TopicFilter = "any",
) -> Article | None:
    if not languages:
        return None

    active_rng = rng or random.Random()
    timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
    headers = {"User-Agent": _USER_AGENT}
    attempts = _MAX_FILTERED_ATTEMPTS if topic != "any" else _MAX_ATTEMPTS

    for _ in range(attempts):
        language = active_rng.choice(languages)
        url = f"https://{language}.wikipedia.org/api/rest_v1/page/random/summary"
        try:
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    log_event("wikipedia_fetch_failed", language=language, status=response.status)
                    continue
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            log_event("wikipedia_fetch_failed", language=language, reason=str(exc))
            continue

        article = _parse_summary(data, language)
        if article is None:
            continue
        if not _matches_topic(article.title, article.extract, topic):
            continue
        return article

    log_event("wikipedia_fetch_failed", reason="no substantive article found")
    return None
