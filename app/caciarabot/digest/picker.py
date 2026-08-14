"""Dedup + random pick over a pool of candidates.

`normalize_url_hash` is deliberately minimal (lowercase + strip trailing
slash) rather than the full utm-stripping normalization a production
dedup would want — good enough to avoid same-day/next-day repeats of the
exact same link, not guaranteed to catch tracking-parameter variants.
"""

from __future__ import annotations

import hashlib
import random

from caciarabot.digest.sources import Candidate


def normalize_url_hash(url: str) -> str:
    normalized = url.strip().lower().rstrip("/")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def pick_candidate(
    candidates: list[Candidate],
    already_sent_hashes: set[str],
    rng: random.Random | None = None,
) -> Candidate | None:
    eligible = [c for c in candidates if normalize_url_hash(c.url) not in already_sent_hashes]
    if not eligible:
        return None
    active_rng = rng or random.Random()
    return active_rng.choice(eligible)
