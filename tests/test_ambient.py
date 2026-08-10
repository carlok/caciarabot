import random

from caciarabot.engine.ambient import select_emoji_reaction


def test_empty_pool_never_reacts():
    assert select_emoji_reaction((), probability=1.0, rng=random.Random(1)) is None


def test_zero_probability_never_reacts():
    assert select_emoji_reaction(("😁",), probability=0.0, rng=random.Random(1)) is None


def test_probability_one_always_reacts_with_pool_member():
    pool = ("😁", "😢", "🤡")
    for seed in range(50):
        emoji = select_emoji_reaction(pool, probability=1.0, rng=random.Random(seed))
        assert emoji in pool


def test_probability_roughly_matches_over_many_trials():
    pool = ("😁",)
    hits = sum(
        1 for seed in range(2000) if select_emoji_reaction(pool, 0.33, random.Random(seed)) is not None
    )
    rate = hits / 2000
    assert 0.28 < rate < 0.38
