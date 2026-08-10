"""Ambient emoji reactions: independent of trigger matching.

Unlike word/phrase triggers, this isn't tied to any specific content —
it's a flat chance, on any ordinary message, of tapping a random emoji
reaction onto it. Kept separate from decision.py's collision/cooldown
machinery since it's a fundamentally different mechanism (a Telegram
message *reaction*, not a new message the bot sends).
"""

from __future__ import annotations

import random


def select_emoji_reaction(
    pool: tuple[str, ...], probability: float, rng: random.Random | None = None
) -> str | None:
    if not pool or probability <= 0:
        return None

    active_rng = rng or random.Random()
    if active_rng.random() < probability:
        return active_rng.choice(pool)
    return None
