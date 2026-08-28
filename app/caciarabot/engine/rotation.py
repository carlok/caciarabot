"""Pick a prompt while avoiding the ones used most recently.

Plain `random.choice` over a pool is memoryless: with 14 moods there's
still a ~7% chance of the same one two days running, and no guarantee
the pool is actually being explored. This biases selection away from
recent picks so consecutive days genuinely differ, without going all
the way to a fixed rotation (which would make the sequence predictable).

Prompts are identified by a hash of their text rather than by filename,
so nothing here depends on how the pool was loaded -- editing a prompt
simply makes it count as new, which is the behaviour we want.
"""

from __future__ import annotations

import hashlib
import random


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()[:16]


def select_fresh_prompt(
    pool: tuple[str, ...],
    recent_hashes: set[str],
    rng: random.Random | None = None,
) -> str | None:
    if not pool:
        return None

    active_rng = rng or random.Random()
    fresh = [p for p in pool if prompt_hash(p) not in recent_hashes]

    # Everything is "recent" (pool smaller than the history window, or
    # the pool shrank) -- fall back to the whole pool rather than
    # refusing to post.
    return active_rng.choice(fresh or list(pool))


def recent_window(pool_size: int) -> int:
    """How many past picks to avoid, given the pool size.

    Roughly a third of the pool, capped at 5: enough to stop obvious
    repetition, never so much that the choice becomes deterministic.
    """
    return max(0, min(5, (pool_size - 1) // 3))
