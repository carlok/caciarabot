"""Local media resolution and the file_id cache fingerprint.

The Telegram `file_id` returned after an upload is cached so the same
local file is not re-uploaded on every subsequent send. The cache key
(fingerprint) is path + size + mtime, which is cheap to compute and
invalidates naturally if the local file is replaced.
"""

from __future__ import annotations

import random
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def compute_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{path.resolve()}:{stat.st_size}:{int(stat.st_mtime)}"


def pick_random_photo(media_dir: Path, directory: str, rng: random.Random | None = None) -> Path:
    active_rng = rng or random.Random()
    photo_dir = media_dir / directory
    candidates = sorted(
        p for p in photo_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not candidates:
        raise FileNotFoundError(f"no image files found in {photo_dir}")
    return active_rng.choice(candidates)
