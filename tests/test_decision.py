import random

from caciarabot.config.models import ReactionRule, TextResponse, WordMatch
from caciarabot.engine.decision import select
from caciarabot.engine.matcher import MatchResult


def _match(rule_id: str, probability: float = 1.0, cooldown_seconds: int = 0, responses=None):
    rule = ReactionRule(
        id=rule_id,
        category="test",
        match=WordMatch(values=(rule_id,)),
        responses=responses or (TextResponse(value="ok", weight=1),),
        probability=probability,
        cooldown_seconds=cooldown_seconds,
    )
    return MatchResult(rule=rule, matched_value=rule_id)


def test_no_matches_means_no_decision():
    assert select([], chat_activity=1.0, max_reactions_per_message=1, is_on_cooldown=lambda _: False) == []


def test_cooldown_suppresses_match():
    match = _match("buongiorno", probability=1.0)
    decisions = select(
        [match], chat_activity=1.0, max_reactions_per_message=1, is_on_cooldown=lambda _: True
    )
    assert decisions == []


def test_probability_zero_never_fires():
    match = _match("buongiorno", probability=0.0)
    decisions = select(
        [match],
        chat_activity=1.0,
        max_reactions_per_message=1,
        is_on_cooldown=lambda _: False,
        rng=random.Random(42),
    )
    assert decisions == []


def test_probability_one_always_fires():
    match = _match("buongiorno", probability=1.0)
    decisions = select(
        [match],
        chat_activity=1.0,
        max_reactions_per_message=1,
        is_on_cooldown=lambda _: False,
        rng=random.Random(42),
    )
    assert len(decisions) == 1
    assert decisions[0].match.rule.id == "buongiorno"


def test_chat_activity_multiplies_probability():
    match = _match("buongiorno", probability=0.5)
    fired = 0
    trials = 500
    for seed in range(trials):
        decisions = select(
            [match],
            chat_activity=0.0,
            max_reactions_per_message=1,
            is_on_cooldown=lambda _: False,
            rng=random.Random(seed),
        )
        fired += len(decisions)
    assert fired == 0


def test_max_reactions_per_message_caps_output():
    matches = [_match(f"trigger_{i}", probability=1.0) for i in range(5)]
    decisions = select(
        matches,
        chat_activity=1.0,
        max_reactions_per_message=2,
        is_on_cooldown=lambda _: False,
        rng=random.Random(1),
    )
    assert len(decisions) == 2


def test_weighted_response_selection_favors_higher_weight():
    heavy = TextResponse(value="heavy", weight=99)
    light = TextResponse(value="light", weight=1)
    match = _match("buongiorno", probability=1.0, responses=(heavy, light))

    counts = {"heavy": 0, "light": 0}
    for seed in range(200):
        decisions = select(
            [match],
            chat_activity=1.0,
            max_reactions_per_message=1,
            is_on_cooldown=lambda _: False,
            rng=random.Random(seed),
        )
        counts[decisions[0].response.value] += 1

    assert counts["heavy"] > counts["light"]
