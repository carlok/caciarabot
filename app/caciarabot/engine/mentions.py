"""Detects whether a message directly addresses the bot.

Kept free of aiogram types (per the clean-interfaces design): the
caller extracts plain (offset, length) mention spans from Telegram's
message entities rather than passing entity objects in directly.
"""

from __future__ import annotations

import re


def is_bot_mentioned(text: str, mention_spans: list[tuple[int, int]], bot_username: str) -> bool:
    target = f"@{bot_username.lower()}"
    return any(text[start : start + length].lower() == target for start, length in mention_spans)


def contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is not None


def is_bot_cited(
    text: str,
    mention_spans: list[tuple[int, int]],
    bot_username: str | None,
    replied_to_bot: bool,
    extra_trigger_words: tuple[str, ...] = (),
) -> bool:
    if replied_to_bot:
        return True
    if bot_username and is_bot_mentioned(text, mention_spans, bot_username):
        return True
    return any(contains_word(text, word) for word in extra_trigger_words)
