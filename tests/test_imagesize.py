"""Header-only image sizing and Telegram's photo-shape limits.

The readers were also checked against macOS `sips` on 142 real images
(JPEG, PNG and WebP): every one matched. These synthetic headers cover
what a real collection does not -- every WebP variant, extreme shapes,
and files that are not what their extension claims.
"""

import struct
import zlib
from pathlib import Path

import pytest
from caciarabot.telegram.imagesize import image_dimensions, photo_shape_problem


def _png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IEND", b"")


def _jpeg(width: int, height: int) -> bytes:
    # SOI, an APP0 segment the parser must skip, then SOF0 with one component.
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


def _webp_vp8x(width: int, height: int) -> bytes:
    body = b"\x00\x00\x00\x00" + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(body)) + b"WEBP" + b"VP8X" + struct.pack("<I", len(body)) + body


def _webp_vp8(width: int, height: int) -> bytes:
    frame = b"\x00\x00\x00" + b"\x9d\x01\x2a" + struct.pack("<HH", width, height)
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(frame)) + b"WEBP" + b"VP8 " + struct.pack("<I", len(frame)) + frame


def _webp_vp8l(width: int, height: int) -> bytes:
    bits = (width - 1) | ((height - 1) << 14)
    body = b"\x2f" + bits.to_bytes(4, "little")
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(body)) + b"WEBP" + b"VP8L" + struct.pack("<I", len(body)) + body


@pytest.mark.parametrize(
    ("builder", "suffix"),
    [(_png, ".png"), (_jpeg, ".jpg"), (_webp_vp8x, ".webp"), (_webp_vp8, ".webp"), (_webp_vp8l, ".webp")],
)
def test_reads_dimensions_from_each_format(tmp_path: Path, builder, suffix):
    path = tmp_path / f"x{suffix}"
    path.write_bytes(builder(1234, 567))

    assert image_dimensions(path) == (1234, 567)


def test_extension_is_not_trusted(tmp_path: Path):
    path = tmp_path / "actually_a_png.jpg"
    path.write_bytes(_png(300, 200))

    assert image_dimensions(path) == (300, 200)


@pytest.mark.parametrize("payload", [b"", b"not an image at all", b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff"])
def test_garbage_is_unparseable_not_an_error(tmp_path: Path, payload):
    path = tmp_path / "bad.jpg"
    path.write_bytes(payload)

    assert image_dimensions(path) is None
    assert photo_shape_problem(path) is None


def test_missing_file_is_none(tmp_path: Path):
    assert image_dimensions(tmp_path / "nope.png") is None


def test_ordinary_photo_has_no_problem(tmp_path: Path):
    path = tmp_path / "ok.jpg"
    path.write_bytes(_jpeg(4000, 3000))

    assert photo_shape_problem(path) is None


def test_width_plus_height_over_limit_is_flagged(tmp_path: Path):
    path = tmp_path / "huge.png"
    path.write_bytes(_png(6000, 4001))

    assert "10001" in photo_shape_problem(path)


def test_exactly_at_the_dimension_limit_is_allowed(tmp_path: Path):
    path = tmp_path / "edge.png"
    path.write_bytes(_png(6000, 4000))

    assert photo_shape_problem(path) is None


def test_extreme_aspect_ratio_is_flagged(tmp_path: Path):
    path = tmp_path / "panorama.jpg"
    path.write_bytes(_jpeg(4100, 200))  # 20.5:1, sum well under 10000

    assert "aspect ratio" in photo_shape_problem(path)


def test_exactly_twenty_to_one_is_allowed(tmp_path: Path):
    path = tmp_path / "ok.jpg"
    path.write_bytes(_jpeg(4000, 200))

    assert photo_shape_problem(path) is None
