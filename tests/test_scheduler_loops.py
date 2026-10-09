"""One bad morning must not end every future one.

The daily-thought and digest loops run as background tasks. An exception
escaping the job would end the task silently -- no log line, no further
posts, until someone restarts the container -- so each loop has to survive
a failing run and fire again the next time it is due.
"""

import asyncio

import pytest
from caciarabot.digest import digest as digest_module
from caciarabot.llm import scheduler


async def _drive(loop_fn, monkeypatch, make_runtime, module, job_name: str, seconds_name: str):
    """Runs the loop with zero delay; the first job run raises, later ones count."""
    runs: list[int] = []
    second_run = asyncio.Event()

    async def flaky_job(_bot, _runtime):
        runs.append(1)
        if len(runs) == 1:
            raise RuntimeError("boom")
        second_run.set()

    monkeypatch.setattr(module, job_name, flaky_job)
    monkeypatch.setattr(module, seconds_name, lambda *_a, **_k: 0)

    task = asyncio.create_task(loop_fn(object(), make_runtime()))
    try:
        await asyncio.wait_for(second_run.wait(), timeout=2)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    return runs


def test_daily_thought_loop_survives_a_failing_run(make_runtime, monkeypatch):
    runs = asyncio.run(
        _drive(
            scheduler.run_daily_thought_loop,
            monkeypatch,
            make_runtime,
            scheduler,
            "post_daily_thought",
            "seconds_until_next",
        )
    )
    assert len(runs) >= 2


def test_digest_loop_survives_a_failing_run(make_runtime, monkeypatch):
    runs = asyncio.run(
        _drive(
            digest_module.run_digest_loop,
            monkeypatch,
            make_runtime,
            digest_module,
            "post_digest",
            "seconds_until_next",
        )
    )
    assert len(runs) >= 2
