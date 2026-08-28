import random

from caciarabot.engine.rotation import prompt_hash, recent_window, select_fresh_prompt


def test_hash_is_stable_and_whitespace_insensitive():
    assert prompt_hash("ciao") == prompt_hash("  ciao\n")


def test_hash_differs_for_different_prompts():
    assert prompt_hash("uno") != prompt_hash("due")


def test_empty_pool_returns_none():
    assert select_fresh_prompt((), set(), rng=random.Random(1)) is None


def test_avoids_recently_used_prompts():
    pool = ("a", "b", "c")
    recent = {prompt_hash("a"), prompt_hash("b")}
    for seed in range(50):
        assert select_fresh_prompt(pool, recent, rng=random.Random(seed)) == "c"


def test_falls_back_to_whole_pool_when_everything_is_recent():
    pool = ("a", "b")
    recent = {prompt_hash("a"), prompt_hash("b")}
    picked = select_fresh_prompt(pool, recent, rng=random.Random(3))
    assert picked in pool


def test_no_recent_history_can_pick_anything():
    pool = ("a", "b", "c")
    seen = {select_fresh_prompt(pool, set(), rng=random.Random(s)) for s in range(60)}
    assert seen == set(pool)


def test_consecutive_picks_never_repeat_when_history_is_honoured():
    """Simulates the scheduler loop: record each pick, avoid the recent ones."""
    pool = tuple("abcdefghijklmn")  # 14, like the daily mood pool
    history: list[str] = []
    rng = random.Random(7)
    for _ in range(40):
        recent = {prompt_hash(p) for p in history[-recent_window(len(pool)) :]}
        picked = select_fresh_prompt(pool, recent, rng=rng)
        assert picked not in history[-recent_window(len(pool)) :]
        history.append(picked)


def test_recent_window_scales_with_pool_and_is_capped():
    assert recent_window(1) == 0  # single-prompt pool must stay usable
    assert recent_window(4) == 1
    assert recent_window(14) == 4
    assert recent_window(100) == 5  # capped
