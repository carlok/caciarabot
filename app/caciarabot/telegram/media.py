"""Local media resolution and the file_id cache fingerprint.

Telegram sends photos, videos and animations through three different
API methods, and a file_id minted by one cannot be replayed through
another. The kind is therefore derived from the file extension in one
place here, and both the send path and the cache read the same answer.

The Telegram `file_id` returned after an upload is cached so the same
local file is not re-uploaded on every subsequent send. The cache key
(fingerprint) is path + size + mtime, which is cheap to compute and
invalidates naturally if the local file is replaced.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Literal

MediaKind = Literal["photo", "video", "animation"]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
# A GIF sent through sendPhoto arrives as a still frame; sendAnimation is
# what makes it move (Telegram transcodes it to mp4 on the way in).
ANIMATION_EXTENSIONS = {".gif"}

MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | ANIMATION_EXTENSIONS

# Bot API upload ceilings for a locally-uploaded file. Exceed them and
# the send fails at runtime, which is why caciarabot-validate checks
# them up front.
MAXIMUM_PHOTO_BYTES = 10 * 1024 * 1024
MAXIMUM_FILE_BYTES = 50 * 1024 * 1024


def media_kind(path: Path) -> MediaKind:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in ANIMATION_EXTENSIONS:
        return "animation"
    return "photo"


def maximum_bytes_for(path: Path) -> int:
    return MAXIMUM_PHOTO_BYTES if media_kind(path) == "photo" else MAXIMUM_FILE_BYTES


def compute_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{path.resolve()}:{stat.st_size}:{int(stat.st_mtime)}"


def pick_random_media(media_dir: Path, directory: str, rng: random.Random | None = None) -> Path:
    active_rng = rng or random.Random()
    source_dir = media_dir / directory
    candidates = sorted(
        p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS
    )
    if not candidates:
        raise FileNotFoundError(f"no image or video files found in {source_dir}")
    return active_rng.choice(candidates)
