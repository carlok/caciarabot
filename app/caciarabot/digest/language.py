"""Keeps the digest to links the group can actually read.

The chat is Italian, but the material is English-language tech: a
Chinese README or a Russian blog post is noise to everyone here. Two
layers, cheapest first:

1. `looks_non_english` reads only the title and excerpt the source
   already gave us -- no extra request, and it catches the common case
   outright. GitHub trending routinely surfaces repos whose entire
   description is Chinese.
2. `page_is_english` actually fetches the target. Accurate but costly,
   so it runs against one picked candidate at a time rather than the
   whole pool.

Neither ever raises, matching sources.py: a language check that fails
should cost one candidate, never the whole digest.
"""

from __future__ import annotations

import re

import aiohttp

from caciarabot.digest.sources import USER_AGENT
from caciarabot.logging_utils import log_event

_REQUEST_TIMEOUT_SECONDS = 10
# Enough of the document to carry <html lang> and a representative slab
# of prose, without pulling a multi-megabyte single-page app in full.
_MAXIMUM_BYTES = 200_000

# Greek is deliberately absent: in this corpus a lone alpha or sigma is
# far more likely to be mathematics than Greek-language content, and a
# short title made mostly of symbols would trip the ratio.
_NON_LATIN_SCRIPT = re.compile(
    "["
    "Ѐ-ӿ"  # Cyrillic
    "֐-׿"  # Hebrew
    "؀-ۿ"  # Arabic
    "ऀ-ॿ"  # Devanagari
    "฀-๿"  # Thai
    "぀-ヿ"  # Hiragana + Katakana
    "㐀-䶿"  # CJK extension A
    "一-鿿"  # CJK unified ideographs
    "가-힯"  # Hangul
    "＀-ﾟ"  # halfwidth/fullwidth forms
    "]"
)
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)
_NON_LATIN_RATIO_LIMIT = 0.10

_HTML_LANG = re.compile(r"<html[^>]*?\blang\s*=\s*[\"']?([A-Za-z]{2,3})", re.IGNORECASE)
_SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WORD = re.compile(r"[a-z']+")

_ENGLISH_STOPWORDS = frozenset(
    """the of and to in a is that for it with as on are this be by or an from at not
    you your we have has was were will can all more which they their our but if when
    what how about into than then them its also may""".split()
)
# Prose in English sits well above this; technical pages sit lower than
# ordinary writing, so the bar is set low enough not to punish them.
_MINIMUM_WORDS_TO_JUDGE = 120
_MINIMUM_STOPWORD_RATIO = 0.06

_GITHUB_REPO_PATH = re.compile(r"^/([^/]+)/([^/]+)/?$")


def looks_non_english(text: str) -> bool:
    """True when the text is visibly written in a non-Latin script.

    Latin-script languages (French, Spanish, German) pass here by design
    -- distinguishing them from English on a ten-word title is guesswork,
    and `page_is_english` settles it properly on the real page.
    """
    letters = _LETTER.findall(text)
    if not letters:
        return False
    non_latin = sum(1 for letter in letters if _NON_LATIN_SCRIPT.match(letter))
    return non_latin / len(letters) > _NON_LATIN_RATIO_LIMIT


def _stopword_ratio(text: str) -> tuple[float, int]:
    words = _WORD.findall(text.lower())
    if not words:
        return 0.0, 0
    hits = sum(1 for word in words if word in _ENGLISH_STOPWORDS)
    return hits / len(words), len(words)


def judge_document(body: str) -> bool | None:
    """True/False for English, None when the document doesn't say enough.

    None is not a rejection. A page that is mostly JavaScript, or a
    three-line README, carries no evidence either way, and dropping good
    links over missing evidence would quietly shrink the pool to nothing.
    """
    declared = _HTML_LANG.search(body)
    if declared:
        return declared.group(1).lower().startswith("en")

    text = _TAG.sub(" ", _SCRIPT_OR_STYLE.sub(" ", body))
    if looks_non_english(text):
        return False

    ratio, word_count = _stopword_ratio(text)
    if word_count < _MINIMUM_WORDS_TO_JUDGE:
        return None
    return ratio >= _MINIMUM_STOPWORD_RATIO


def readme_url(url: str) -> str | None:
    """Maps a GitHub repo URL to its raw README, or None if not one.

    github.com serves `<html lang="en">` on every page it renders,
    including repos whose README is entirely Chinese, so checking the
    rendered page would wave through exactly what this is here to catch.
    The README is the actual content being recommended.
    """
    if not url.startswith(("https://github.com/", "http://github.com/")):
        return None
    path = url.split("github.com", 1)[1].split("?", 1)[0].split("#", 1)[0]
    match = _GITHUB_REPO_PATH.match(path)
    if not match:
        return None
    owner, repo = match.groups()
    if owner in {"orgs", "topics", "collections", "sponsors", "features"}:
        return None
    return f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"


async def _fetch_body(session: aiohttp.ClientSession, url: str) -> str | None:
    # Wikipedia (among others) answers 403 to a request with no
    # User-Agent, which would silently turn every wiki link into an
    # undetermined verdict rather than a judged one.
    try:
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
        async with session.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=timeout
        ) as response:
            if response.status != 200:
                return None
            raw = await response.content.read(_MAXIMUM_BYTES)
    except (aiohttp.ClientError, TimeoutError, UnicodeDecodeError):
        return None
    return raw.decode("utf-8", errors="replace")


async def page_is_english(session: aiohttp.ClientSession, url: str) -> bool | None:
    """Fetches the target and judges it. None means undetermined."""
    target = readme_url(url) or url
    body = await _fetch_body(session, target)
    if body is None:
        # A repo with no README at HEAD, a paywall, a 403: no evidence,
        # and the metadata pass already had its say.
        log_event("digest_language_unknown", url=url, reason="fetch failed")
        return None
    return judge_document(body)
