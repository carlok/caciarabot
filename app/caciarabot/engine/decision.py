"""Collision handling, probability, cooldowns, and weighted response selection.

Pipeline (spec section 18):

    collect matches -> remove ineligible (cooldown) -> evaluate probability
    -> weighted/random selection -> emit at most maxReactionsPerMessage
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from caciarabot.config.models import Response
from caciarabot.engine.matcher import MatchResult


@dataclass(frozen=True, slots=True)
class Decision:
    match: MatchResult
    response: Response


def _effective_probability(rule_probability: float, chat_activity: float) -> float:
    return max(0.0, min(1.0, rule_probability * chat_activity))


def _pick_weighted(items: list, weight_of: Callable[[object], float], rng: random.Random) -> object:
    total_weight = sum(weight_of(item) for item in items)
    if total_weight <= 0:
        return rng.choice(items)

    threshold = rng.random() * total_weight
    cumulative = 0.0
    for item in items:
        cumulative += weight_of(item)
        if cumulative >= threshold:
            return item
    return items[-1]


def select(
    matches: list[MatchResult],
    chat_activity: float,
    max_reactions_per_message: int,
    is_on_cooldown: Callable[[str], bool],
    rng: random.Random | None = None,
) -> list[Decision]:
    if max_reactions_per_message <= 0 or not matches:
        return []

    active_rng = rng or random.Random()

    eligible = [m for m in matches if not is_on_cooldown(m.rule.id)]
    if not eligible:
        return []

    firing = [
        m for m in eligible if active_rng.random() < _effective_probability(m.rule.probability, chat_activity)
    ]
    if not firing:
        return []

    active_rng.shuffle(firing)
    chosen_matches = firing[:max_reactions_per_message]

    decisions: list[Decision] = []
    for match in chosen_matches:
        response = _pick_weighted(
            list(match.rule.responses), weight_of=lambda r: r.weight, rng=active_rng
        )
        decisions.append(Decision(match=match, response=response))

    return decisions
