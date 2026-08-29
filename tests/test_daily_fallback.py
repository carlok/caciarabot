"""A failed generation must not cost the day's post.

The daily thought is a single API call, so a 429 or a timeout would
otherwise mean silence until tomorrow. These pin down that the local
corpus takes over, costs nothing, and doesn't repeat itself across a
run of bad days.
"""

import asyncio
from pathlib import Path

from caciarabot.llm import scheduler
from caciarabot.llm.fallback import load_message_pool
from caciarabot.storage import touch_chat

_OPENERS = ("UNO", "DUE", "TRE", "QUATTRO", "CINQUE")


def test_load_message_pool_skips_blanks_and_comments(tmp_path: Path):
    path = tmp_path / "daily.txt"
    path.write_text("# a comment\n\nprimo\n  secondo  \n\n# another\nterzo\n", encoding="utf-8")
    assert load_message_pool(path) == ("primo", "secondo", "terzo")


def test_load_message_pool_missing_file_is_empty(tmp_path: Path):
    assert load_message_pool(tmp_path / "nope.txt") == ()


def _run_failing_days(make_runtime, monkeypatch, days: int, **runtime_kwargs) -> list[str]:
    sent: list[str] = []

    async def failing_generate(*_args, **_kwargs):
        return None

    monkeypatch.setattr(scheduler, "generate_reply", failing_generate)

    runtime = make_runtime(
        bot_config={"llm_dry_run": False},
        **{
            "daily_fallback_messages": _OPENERS,
            "daily_fallback_tails": ("TAIL-A", "TAIL-B"),
            **runtime_kwargs,
        },
    )
    touch_chat(runtime.db, 42)

    class _Bot:
        @staticmethod
        async def send_message(_chat_id, text):
            sent.append(text)

    for _ in range(days):
        asyncio.run(scheduler.post_daily_thought(_Bot(), runtime))
    return sent


def test_failed_generation_falls_back_to_local_corpus(make_runtime, monkeypatch):
    (text,) = _run_failing_days(make_runtime, monkeypatch, 1)
    assert text.split("\n\n")[0] in _OPENERS


def test_fallback_makes_no_network_call(make_runtime, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("the fallback must not touch the network")

    monkeypatch.setattr("aiohttp.ClientSession", explode)
    assert _run_failing_days(make_runtime, monkeypatch, 1)


def test_consecutive_failed_days_do_not_repeat(make_runtime, monkeypatch):
    openers = [t.split("\n\n")[0] for t in _run_failing_days(make_runtime, monkeypatch, 5)]
    for earlier, later in zip(openers, openers[1:]):
        assert earlier != later, openers


def test_empty_corpus_stays_silent_rather_than_crashing(make_runtime, monkeypatch):
    sent = _run_failing_days(
        make_runtime, monkeypatch, 1, daily_fallback_messages=(), daily_fallback_tails=()
    )
    assert sent == []
