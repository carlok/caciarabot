"""Detects whether a message directly addresses the bot.

Kept free of aiogram types (per the clean-interfaces design): the
caller extracts plain (offset, length) mention spans from Telegram's
message entities rather than passing entity objects in directly.
"""

from __future__ import annotations


def is_bot_mentioned(text: str, mention_spans: list[tuple[int, int]], bot_username: str) -> bool:
    target = f"@{bot_username.lower()}"
    return any(text[start : start + length].lower() == target for start, length in mention_spans)


def is_bot_cited(
    text: str,
    mention_spans: list[tuple[int, int]],
    bot_username: str | None,
    replied_to_bot: bool,
) -> bool:
    if replied_to_bot:
        return True
    if not bot_username:
        return False
    return is_bot_mentioned(text, mention_spans, bot_username)
