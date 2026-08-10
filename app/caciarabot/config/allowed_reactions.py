"""Telegram's fixed set of emoji allowed for message reactions.

Unlike a normal message, `setMessageReaction` rejects any emoji outside
this specific list — the Bot API does not accept arbitrary emoji here.
Kept as a local constant so a typo in configuration is caught by the
validator instead of failing at the live API call.
"""

from __future__ import annotations

ALLOWED_REACTION_EMOJI: frozenset[str] = frozenset(
    {
        "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱",
        "🤬", "😢", "🎉", "🤩", "🤮", "😍", "🐳", "❤‍🔥", "🌚", "🌭",
        "💯", "🤣", "⚡", "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾",
        "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃",
        "🙈", "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃",
        "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄", "😘", "💊", "🙊",
        "😎", "👾", "🤷‍♂", "🤷", "🤷‍♀", "😡", "🤡",
    }
)
