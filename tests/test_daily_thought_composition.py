"""The daily thought is assembled from three independent pools.

Mood alone was not enough: the model kept landing in the same lyrical
register every morning, so diction became its own dimension. These tests
pin down that all three actually reach the prompt, and that consecutive
days differ on every one of them.
"""

import asyncio

from caciarabot.llm import scheduler


def _run_days(make_runtime, monkeypatch, days: int) -> list[str]:
    seen: list[str] = []

    async def fake_generate(_key, _model, prompt, _user_text):
        seen.append(prompt)
        return "pensiero"

    monkeypatch.setattr(scheduler, "generate_reply", fake_generate)
    runtime = make_runtime()
    for _ in range(days):
        asyncio.run(scheduler.post_daily_thought(object(), runtime))
    return seen


def test_prompt_carries_mood_depth_and_style(make_runtime, monkeypatch):
    (prompt,) = _run_days(make_runtime, monkeypatch, 1)
    assert any(f"MOOD-{c}" in prompt for c in "ABCD")
    assert any(f"DEPTH-{c}" in prompt for c in "ABCD")
    assert any(f"STYLE-{c}" in prompt for c in "ABCD")


def test_consecutive_days_change_every_dimension(make_runtime, monkeypatch):
    prompts = _run_days(make_runtime, monkeypatch, 6)

    def picked(prompt: str, prefix: str) -> str:
        return next(c for c in "ABCD" if f"{prefix}-{c}" in prompt)

    for prefix in ("MOOD", "DEPTH", "STYLE"):
        chosen = [picked(p, prefix) for p in prompts]
        for earlier, later in zip(chosen, chosen[1:]):
            assert earlier != later, f"{prefix} repeated on consecutive days: {chosen}"
