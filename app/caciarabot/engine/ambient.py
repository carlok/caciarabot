"""Ambient behaviors independent of trigger matching.

Unlike word/phrase triggers, these aren't tied to any specific
content — each is a flat chance, on any ordinary message, of doing
something (tapping an emoji reaction, generating an LLM reply). Kept
separate from decision.py's collision/cooldown machinery since these
are fundamentally different mechanisms from a triggered response.
"""

from __future__ import annotations

import random


def _pick_from_pool(
    pool: tuple[str, ...], probability: float, rng: random.Random | None = None
) -> str | None:
    if not pool or probability <= 0:
        return None

    active_rng = rng or random.Random()
    if active_rng.random() < probability:
        return active_rng.choice(pool)
    return None


def select_emoji_reaction(
    pool: tuple[str, ...], probability: float, rng: random.Random | None = None
) -> str | None:
    return _pick_from_pool(pool, probability, rng)


def select_llm_prompt(
    pool: tuple[str, ...], probability: float, rng: random.Random | None = None
) -> str | None:
    return _pick_from_pool(pool, probability, rng)
