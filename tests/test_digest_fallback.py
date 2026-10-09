"""A failed digest comment must not cost the day's link.

By the time the comment is generated the hard part has succeeded: a link
was fetched, deduplicated and language-checked. These pin down that the
link is still posted with a canned line, with no network call of its own,
and that a run of bad days does not repeat the same line.
"""

import asyncio

from caciarabot.digest import digest as digest_module
from caciarabot.digest.sources import Candidate
from caciarabot.storage import touch_chat

_COMMENTS = ("UNO", "DUE", "TRE", "QUATTRO")


def _post_digests(make_runtime, monkeypatch, days: int, **runtime_kwargs) -> list[str]:
    sent: list[str] = []
    counter = iter(range(1000))

    async def fake_candidates(_session, _runtime, now=None):
        # A fresh URL each day so the dedup table never empties the pool.
        n = next(counter)
        return [Candidate(source="hackernews", title=f"T{n}", url=f"https://example.com/{n}")]

    async def failing_generate(*_args, **_kwargs):
        return None

    generate = runtime_kwargs.pop("_generate", failing_generate)

    class _Bot:
        @staticmethod
        async def send_message(_chat_id, text, **_kwargs):
            sent.append(text)

    monkeypatch.setattr(digest_module, "fetch_digest_candidates", fake_candidates)
    monkeypatch.setattr(digest_module, "generate_reply", generate)

    runtime = make_runtime(
        bot_config={"digest_enabled": True, "llm_dry_run": False, "digest_english_only": False},
        llm_digest_prompts=("PROMPT",),
        **{"digest_fallback_comments": _COMMENTS, **runtime_kwargs},
    )
    touch_chat(runtime.db, 1)
    for _ in range(days):
        asyncio.run(digest_module.post_digest(_Bot(), runtime))
    return sent


def test_failed_comment_still_posts_the_link(make_runtime, monkeypatch):
    (text,) = _post_digests(make_runtime, monkeypatch, 1)

    assert "https://example.com/0" in text
    assert any(comment in text for comment in _COMMENTS)


def test_fallback_message_keeps_the_normal_layout(make_runtime, monkeypatch):
    (text,) = _post_digests(make_runtime, monkeypatch, 1)

    assert text.startswith("\U0001f4f0 T0\nhttps://example.com/0\n\n")
    assert text.endswith("— fonte: hackernews")


def test_fallback_does_not_retry_the_model(make_runtime, monkeypatch):
    """The point is cost: a retry spends more quota against a key that just ran out."""
    calls: list[int] = []

    async def counting_generate(*_args, **_kwargs):
        calls.append(1)
        return None

    sent = _post_digests(make_runtime, monkeypatch, 3, _generate=counting_generate)

    assert len(sent) == 3
    assert len(calls) == 3  # exactly one attempt per day, never two


def test_consecutive_failed_days_do_not_repeat_a_comment(make_runtime, monkeypatch):
    texts = _post_digests(make_runtime, monkeypatch, 4)

    def comment_of(text: str) -> str:
        return next(c for c in _COMMENTS if c in text)

    comments = [comment_of(t) for t in texts]
    for earlier, later in zip(comments, comments[1:]):
        assert earlier != later, comments


def test_empty_corpus_still_skips_rather_than_crashing(make_runtime, monkeypatch):
    assert _post_digests(make_runtime, monkeypatch, 1, digest_fallback_comments=()) == []
