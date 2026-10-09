"""Reads an image's pixel dimensions from its header, stdlib only.

Telegram rejects a photo whose width + height exceeds 10000 px or whose
longer side is more than 20x the shorter (PHOTO_INVALID_DIMENSIONS), and
it only says so when the send is attempted, in a group, hours after the
file was dropped in. Pillow would answer this in one line, but it is a
sizeable dependency to add for three header reads, and the container
image has no other use for it.

Only the formats the bot sends as photos are handled: PNG, JPEG, WebP.
Anything unparseable returns None, and the caller treats that as "no
evidence", never as a violation: refusing a good file because a header
was odd would be worse than the failure being prevented.
"""

from __future__ import annotations

import struct
from pathlib import Path

MAXIMUM_WIDTH_PLUS_HEIGHT = 10_000
MAXIMUM_ASPECT_RATIO = 20

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# JPEG start-of-frame markers carry the dimensions. C4 (DHT), C8 (JPG) and
# CC (DAC) sit in the same range but are not frames.
_JPEG_FRAME_MARKERS = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}
_HEADER_BYTES = 64 * 1024


def _png(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(_PNG_SIGNATURE) or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _jpeg(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    position = 2
    while position + 4 <= len(data):
        if data[position] != 0xFF:
            return None
        marker = data[position + 1]
        if marker == 0xFF:  # fill byte
            position += 1
            continue
        if marker in _JPEG_FRAME_MARKERS:
            if position + 9 > len(data):
                return None
            height, width = struct.unpack(">HH", data[position + 5 : position + 9])
            return width, height
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:  # no length field
            position += 2
            continue
        (length,) = struct.unpack(">H", data[position + 2 : position + 4])
        position += 2 + length
    return None


def _webp(data: bytes) -> tuple[int, int] | None:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP" or len(data) < 16:
        return None
    chunk = data[12:16]
    # Each variant stores its dimensions at a different depth, so the length
    # guard is per variant: VP8L's header ends at byte 25, the others at 30.
    if chunk == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if chunk == b"VP8 " and len(data) >= 30:
        if data[23:26] != b"\x9d\x01\x2a":
            return None
        width, height = struct.unpack("<HH", data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 25:
        if data[20] != 0x2F:
            return None
        bits = int.from_bytes(data[21:25], "little")
        return 1 + (bits & 0x3FFF), 1 + ((bits >> 14) & 0x3FFF)
    return None


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as handle:
            data = handle.read(_HEADER_BYTES)
    except OSError:
        return None
    for reader in (_png, _jpeg, _webp):
        try:
            dimensions = reader(data)
        except (struct.error, IndexError):
            dimensions = None
        if dimensions is not None and all(side > 0 for side in dimensions):
            return dimensions
    return None


def photo_shape_problem(path: Path) -> str | None:
    """Why Telegram would reject this photo's shape, or None if it would not."""
    dimensions = image_dimensions(path)
    if dimensions is None:
        return None
    width, height = dimensions
    if width + height > MAXIMUM_WIDTH_PLUS_HEIGHT:
        return (
            f"{width}x{height} px: width + height is {width + height}, "
            f"Telegram's limit for a photo is {MAXIMUM_WIDTH_PLUS_HEIGHT}"
        )
    ratio = max(width, height) / min(width, height)
    if ratio > MAXIMUM_ASPECT_RATIO:
        return (
            f"{width}x{height} px: aspect ratio {ratio:.0f}:1, "
            f"Telegram's limit for a photo is {MAXIMUM_ASPECT_RATIO}:1"
        )
    return None
