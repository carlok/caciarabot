"""Loads a pool of plain-text prompt files.

Each `.txt` file under the given directory is one prompt variant.
Kept as flat text rather than JSON/JSONL since a prompt is prose, not
structured data — there's no match/probability/response shape to it.
"""

from __future__ import annotations

from pathlib import Path


def load_prompt_pool(prompts_dir: Path) -> tuple[str, ...]:
    if not prompts_dir.is_dir():
        return ()
    return tuple(
        path.read_text(encoding="utf-8").strip()
        for path in sorted(prompts_dir.glob("*.txt"))
    )
