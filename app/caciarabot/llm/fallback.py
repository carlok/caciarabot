"""Deterministic, zero-cost stand-in for a failed LLM generation.

The daily thought is a single API call a day, so any transient failure
-- a 429 on a free-tier key, a timeout, an empty candidate -- costs the
whole day's post. Retrying spends more quota against a key that has
most likely just run out of it, so the recovery here is local instead:
a hand-written Italian corpus, composed and rotated with the same
no-repeat machinery the prompt pools use.

The corpus files hold the bot's *own words* rather than instructions
for a model, which is why they live under `config/fallback/` and are
line-based -- one message per line -- instead of one-prose-file-per-
variant like `config/prompts/`.
"""

from __future__ import annotations

from pathlib import Path


def load_message_pool(path: Path) -> tuple[str, ...]:
    if not path.is_file():
        return ()
    return tuple(
        line
        for raw_line in path.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    )
