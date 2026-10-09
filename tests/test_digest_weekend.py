"""Weekday digest uses tech sources; weekend digest uses non-tech Wikipedia."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from caciarabot.digest.digest import fetch_digest_candidates
from caciarabot.digest.sources import Candidate
from caciarabot.llm.wikipedia import Article

_TZ = ZoneInfo("Europe/Rome")
_FRIDAY = datetime(2026, 10, 2, 9, 0, tzinfo=_TZ)
_SATURDAY = datetime(2026, 10, 3, 9, 0, tzinfo=_TZ)


@pytest.fixture
def digest_runtime(make_runtime):
    return make_runtime(
        bot_config={
            "digest_enabled": True,
            "digest_sources": ("hackernews", "github_trending"),
            "llm_daily_link_languages": ("it", "en"),
        },
        llm_digest_prompts=("PROMPT",),
    )


def test_weekend_in_bot_timezone_saturday_and_monday(make_runtime):
    from caciarabot.llm.scheduler import is_weekend_in_bot_timezone

    runtime = make_runtime()
    monday = datetime(2026, 10, 5, 12, 0, tzinfo=_TZ)
    saturday = datetime(2026, 10, 3, 12, 0, tzinfo=_TZ)
    sunday = datetime(2026, 10, 4, 12, 0, tzinfo=_TZ)

    assert not is_weekend_in_bot_timezone(runtime, monday)
    assert is_weekend_in_bot_timezone(runtime, saturday)
    assert is_weekend_in_bot_timezone(runtime, sunday)


def test_fetch_digest_candidates_weekday_uses_configured_sources(digest_runtime, monkeypatch):
    tech = [Candidate(source="hackernews", title="HN", url="https://example.com/hn")]

    async def fake_fetch_all(session, sources, reddit_subs):
        assert sources == ("hackernews", "github_trending")
        return tech

    monkeypatch.setattr("caciarabot.digest.digest.fetch_all", fake_fetch_all)
    wiki = AsyncMock()
    monkeypatch.setattr("caciarabot.digest.digest.fetch_random_article", wiki)

    result = asyncio.run(
        fetch_digest_candidates(object(), digest_runtime, now=_FRIDAY)
    )
    assert result == tech
    wiki.assert_not_called()


def test_fetch_digest_candidates_weekend_uses_nontechnical_wikipedia(digest_runtime, monkeypatch):
    article = Article(
        title="Il nome della rosa",
        extract="Un romanzo di Umberto Eco. " * 10,
        url="https://it.wikipedia.org/wiki/Il_nome_della_rosa",
        language="it",
    )
    wiki = AsyncMock(return_value=article)
    monkeypatch.setattr("caciarabot.digest.digest.fetch_random_article", wiki)

    async def fake_fetch_all(*_args, **_kwargs):
        raise AssertionError("tech sources must not run on weekends")

    monkeypatch.setattr("caciarabot.digest.digest.fetch_all", fake_fetch_all)

    result = asyncio.run(
        fetch_digest_candidates(object(), digest_runtime, now=_SATURDAY)
    )
    assert len(result) == 1
    assert result[0].source == "wikipedia"
    assert result[0].title == article.title
    wiki.assert_awaited_once()
    assert wiki.await_args.kwargs["topic"] == "nontechnical"


def test_daily_link_weekend_requests_nontechnical_article(make_runtime, monkeypatch):
    from caciarabot.llm import scheduler

    runtime = make_runtime(
        bot_config={"llm_daily_link_probability": 1.0},
        llm_daily_link_prompts=("LINK-PROMPT",),
    )
    article = Article(
        title="Essay",
        extract="A long non-technical essay. " * 10,
        url="https://en.wikipedia.org/wiki/Essay",
        language="en",
    )
    wiki = AsyncMock(return_value=article)
    monkeypatch.setattr(scheduler, "fetch_random_article", wiki)

    async def fake_generate(*_args, **_kwargs):
        return "commento"

    monkeypatch.setattr(scheduler, "generate_reply", fake_generate)

    saturday = datetime(2026, 10, 3, 9, 0, tzinfo=_TZ)
    text = asyncio.run(scheduler._generate_link_thought(runtime, __import__("random").Random(0), now=saturday))
    assert text is not None
    assert wiki.await_args.kwargs["topic"] == "nontechnical"


def test_daily_link_weekday_does_not_filter_topic(make_runtime, monkeypatch):
    from caciarabot.llm import scheduler

    runtime = make_runtime(
        bot_config={"llm_daily_link_probability": 1.0},
        llm_daily_link_prompts=("LINK-PROMPT",),
    )
    article = Article(
        title="Linux",
        extract="An operating system kernel. " * 10,
        url="https://en.wikipedia.org/wiki/Linux",
        language="en",
    )
    wiki = AsyncMock(return_value=article)
    monkeypatch.setattr(scheduler, "fetch_random_article", wiki)
    monkeypatch.setattr(scheduler, "generate_reply", AsyncMock(return_value="commento"))

    friday = datetime(2026, 10, 2, 9, 0, tzinfo=_TZ)
    asyncio.run(scheduler._generate_link_thought(runtime, __import__("random").Random(0), now=friday))
    assert wiki.await_args.kwargs.get("topic", "any") == "any"


def _run_post_digest(runtime, monkeypatch, candidate: Candidate) -> str:
    """Runs post_digest with the network stubbed; returns the prompt Gemini got."""
    from caciarabot.digest import digest as digest_module
    from caciarabot.storage import touch_chat

    seen: list[str] = []

    async def fake_candidates(session, rt, now=None):
        return [candidate]

    async def fake_generate(_key, _model, prompt, _message):
        seen.append(prompt)
        return "commento"

    monkeypatch.setattr(digest_module, "fetch_digest_candidates", fake_candidates)
    monkeypatch.setattr(digest_module, "generate_reply", fake_generate)
    touch_chat(runtime.db, 1)
    asyncio.run(digest_module.post_digest(object(), runtime))
    return seen[0]


def _prompt_runtime(make_runtime, weekend_prompts):
    return make_runtime(
        bot_config={"digest_enabled": True, "llm_dry_run": True},
        llm_digest_prompts=("TECH",),
        llm_digest_weekend_prompts=weekend_prompts,
    )


def test_wikipedia_candidate_gets_the_weekend_prompt(make_runtime, monkeypatch):
    runtime = _prompt_runtime(make_runtime, ("WEEKEND",))
    wiki = Candidate(source="wikipedia", title="Kotka", url="https://it.wikipedia.org/wiki/Kotka")

    assert _run_post_digest(runtime, monkeypatch, wiki) == "WEEKEND"


def test_tech_candidate_keeps_the_tech_prompt(make_runtime, monkeypatch):
    runtime = _prompt_runtime(make_runtime, ("WEEKEND",))
    hn = Candidate(source="hackernews", title="HN", url="https://example.com/hn")

    assert _run_post_digest(runtime, monkeypatch, hn) == "TECH"


def test_empty_weekend_pool_falls_back_rather_than_losing_the_day(make_runtime, monkeypatch):
    runtime = _prompt_runtime(make_runtime, ())
    wiki = Candidate(source="wikipedia", title="Kotka", url="https://it.wikipedia.org/wiki/Kotka")

    assert _run_post_digest(runtime, monkeypatch, wiki) == "TECH"
