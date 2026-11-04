"""/stats reports how often each ambient behaviour actually fired.

A configured probability says nothing about what happened in the chat; the
measured rate against messages observed is the number that settles a
"it replies too often" question.
"""

import asyncio
from pathlib import Path

from caciarabot.localization import load_locales
from caciarabot.storage import increment_counter
from caciarabot.telegram.handlers import cmd_stats

_LOCALES = Path(__file__).resolve().parents[1] / "locales"


class _Message:
    def __init__(self) -> None:
        self.chat = type("Chat", (), {"id": 1})()
        self.sent: list[str] = []

    async def answer(self, text: str) -> None:
        self.sent.append(text)


def _stats(make_runtime, observed: int, replies: int, cited: int, emoji: int) -> str:
    runtime = make_runtime()
    runtime.locales = load_locales(_LOCALES, "it")
    for key, count in (
        ("messages_observed", observed),
        ("llm_replies_sent", replies),
        ("llm_cited_replies_sent", cited),
        ("emoji_reactions_sent", emoji),
    ):
        for _ in range(count):
            increment_counter(runtime.db, "global", key)
    message = _Message()
    asyncio.run(cmd_stats(message, runtime))
    return message.sent[0]


def test_stats_shows_measured_rate_per_behaviour(make_runtime):
    text = _stats(make_runtime, observed=200, replies=10, cited=4, emoji=66)

    assert "Risposte spontanee: 10 (5.0% dei messaggi)" in text
    assert "Risposte quando citato: 4 (2.0% dei messaggi)" in text
    assert "Emoji reaction: 66 (33.0% dei messaggi)" in text


def test_stats_with_no_messages_does_not_divide_by_zero(make_runtime):
    text = _stats(make_runtime, observed=0, replies=0, cited=0, emoji=0)

    assert "Risposte spontanee: 0 (0.0% dei messaggi)" in text
