import random

from caciarabot.engine.ambient import pick_secret_targets, select_emoji_reaction, select_llm_prompt


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


def test_llm_prompt_selection_picks_a_pool_member():
    pool = ("dry.txt content", "absurd.txt content")
    for seed in range(50):
        prompt = select_llm_prompt(pool, probability=1.0, rng=random.Random(seed))
        assert prompt in pool


def test_llm_prompt_selection_respects_zero_probability():
    assert select_llm_prompt(("x",), probability=0.0, rng=random.Random(1)) is None


def test_pick_secret_targets_empty_members_returns_empty():
    assert pick_secret_targets([], rng=random.Random(1)) == []


def test_pick_secret_targets_single_member():
    assert pick_secret_targets(["Marco"], rng=random.Random(1)) == ["Marco"]


def test_pick_secret_targets_picks_one_or_two():
    members = ["Marco", "Luca", "Giulia", "Anna"]
    for seed in range(100):
        targets = pick_secret_targets(members, rng=random.Random(seed))
        assert 1 <= len(targets) <= 2
        assert len(targets) == len(set(targets))
        assert all(t in members for t in targets)


def test_pick_secret_targets_never_exceeds_available_members():
    members = ["Marco", "Luca"]
    for seed in range(50):
        targets = pick_secret_targets(members, rng=random.Random(seed))
        assert len(targets) <= 2
