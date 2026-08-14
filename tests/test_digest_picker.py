import random

from caciarabot.digest.picker import normalize_url_hash, pick_candidate
from caciarabot.digest.sources import Candidate


def _candidate(url: str, title: str = "t") -> Candidate:
    return Candidate(source="hackernews", title=title, url=url)


def test_normalize_url_hash_ignores_trailing_slash():
    assert normalize_url_hash("https://example.com/post") == normalize_url_hash("https://example.com/post/")


def test_normalize_url_hash_is_case_insensitive():
    assert normalize_url_hash("https://Example.com/Post") == normalize_url_hash("https://example.com/post")


def test_normalize_url_hash_does_not_strip_utm_params():
    # documented v1 limitation -- utm_* variants are treated as distinct
    assert normalize_url_hash("https://example.com/post?utm_source=x") != normalize_url_hash(
        "https://example.com/post"
    )


def test_pick_candidate_excludes_already_sent():
    candidates = [_candidate("https://a.example"), _candidate("https://b.example")]
    already_sent = {normalize_url_hash("https://a.example")}
    picked = pick_candidate(candidates, already_sent, rng=random.Random(1))
    assert picked.url == "https://b.example"


def test_pick_candidate_returns_none_when_everything_already_sent():
    candidates = [_candidate("https://a.example")]
    already_sent = {normalize_url_hash("https://a.example")}
    assert pick_candidate(candidates, already_sent, rng=random.Random(1)) is None


def test_pick_candidate_returns_none_for_empty_pool():
    assert pick_candidate([], set(), rng=random.Random(1)) is None


def test_pick_candidate_is_deterministic_under_seeded_rng():
    candidates = [_candidate(f"https://{i}.example") for i in range(10)]
    first = pick_candidate(candidates, set(), rng=random.Random(42))
    second = pick_candidate(candidates, set(), rng=random.Random(42))
    assert first == second
