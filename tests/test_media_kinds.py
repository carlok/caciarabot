"""Images and videos both work, and each goes out through the right API.

Telegram mints a file_id per send method and will not replay a photo's
id through sendVideo, so the kind has to follow the file rather than the
cache row.
"""

import random
from pathlib import Path

import pytest

from caciarabot.config.reactions import load_reaction_file
from caciarabot.telegram.media import (
    MEDIA_EXTENSIONS,
    maximum_bytes_for,
    media_kind,
    pick_random_media,
)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("a.jpg", "photo"),
        ("a.JPEG", "photo"),
        ("a.png", "photo"),
        ("a.webp", "photo"),
        ("a.mp4", "video"),
        ("a.MOV", "video"),
        ("a.webm", "video"),
        ("a.gif", "animation"),
    ],
)
def test_kind_follows_the_extension(filename, expected):
    assert media_kind(Path(filename)) == expected


def test_gif_is_an_animation_not_a_photo():
    """sendPhoto on a GIF delivers a still frame; sendAnimation moves."""
    assert media_kind(Path("nope.gif")) == "animation"


def test_upload_ceilings_differ_by_kind():
    assert maximum_bytes_for(Path("a.jpg")) == 10 * 1024 * 1024
    assert maximum_bytes_for(Path("a.mp4")) == 50 * 1024 * 1024
    assert maximum_bytes_for(Path("a.gif")) == 50 * 1024 * 1024


def test_random_pick_mixes_images_and_videos(tmp_path: Path):
    directory = tmp_path / "roba"
    directory.mkdir()
    for name in ("uno.jpg", "due.mp4", "tre.gif", "quattro.webp"):
        (directory / name).write_bytes(b"x")

    picked = {
        pick_random_media(tmp_path, "roba", rng=random.Random(seed)).name for seed in range(80)
    }

    assert picked == {"uno.jpg", "due.mp4", "tre.gif", "quattro.webp"}


def test_random_pick_ignores_unsupported_files(tmp_path: Path):
    directory = tmp_path / "roba"
    directory.mkdir()
    (directory / "buono.mp4").write_bytes(b"x")
    for name in ("note.txt", "foto.avif", ".DS_Store"):
        (directory / name).write_bytes(b"x")

    picked = {pick_random_media(tmp_path, "roba", rng=random.Random(s)).name for s in range(30)}

    assert picked == {"buono.mp4"}


def test_directory_with_nothing_sendable_raises(tmp_path: Path):
    directory = tmp_path / "vuota"
    directory.mkdir()
    (directory / "note.txt").write_bytes(b"x")

    with pytest.raises(FileNotFoundError):
        pick_random_media(tmp_path, "vuota")


def test_avif_is_not_claimed_as_supported():
    """Telegram rejects it, so the picker must not offer it."""
    assert ".avif" not in MEDIA_EXTENSIONS


def test_legacy_photo_response_types_still_parse(tmp_path: Path):
    """Existing packs are full of "photo"/"randomPhoto"; they must keep working."""
    path = tmp_path / "reactions.jsonl"
    path.write_text(
        '{"id":"a","category":"g","match":{"type":"word","values":["x"]},'
        '"responses":[{"type":"photo","path":"images/a.jpg","weight":1},'
        '{"type":"randomPhoto","directory":"images/dir","weight":1}]}\n'
        '{"id":"b","category":"g","match":{"type":"word","values":["y"]},'
        '"responses":[{"type":"media","path":"images/b.mp4","weight":1},'
        '{"type":"randomMedia","directory":"images/dir","weight":1}]}\n'
    )

    rules, errors = load_reaction_file(path)

    assert errors == []
    assert [type(r).__name__ for r in rules[0].responses] == [
        "MediaResponse",
        "RandomMediaResponse",
    ]
    assert [type(r).__name__ for r in rules[1].responses] == [
        "MediaResponse",
        "RandomMediaResponse",
    ]


def test_oversized_file_is_reported(tmp_path: Path):
    from caciarabot.validate import _check_media

    directory = tmp_path / "images" / "dir"
    directory.mkdir(parents=True)
    (directory / "enorme.jpg").write_bytes(b"x" * (11 * 1024 * 1024))

    path = tmp_path / "reactions.jsonl"
    path.write_text(
        '{"id":"a","category":"g","match":{"type":"word","values":["x"]},'
        '"responses":[{"type":"randomMedia","directory":"images/dir","weight":1}]}\n'
    )
    rules, _errors = load_reaction_file(path)

    media_errors, _files, _skipped = _check_media(tmp_path, rules)

    assert len(media_errors) == 1
    assert "10 MB upload limit" in media_errors[0].message


def test_unsendable_files_are_listed_separately(tmp_path: Path):
    from caciarabot.validate import _check_media

    directory = tmp_path / "images" / "dir"
    directory.mkdir(parents=True)
    (directory / "ok.mp4").write_bytes(b"x")
    (directory / "foto.avif").write_bytes(b"x")

    path = tmp_path / "reactions.jsonl"
    path.write_text(
        '{"id":"a","category":"g","match":{"type":"word","values":["x"]},'
        '"responses":[{"type":"randomMedia","directory":"images/dir","weight":1}]}\n'
    )
    rules, _errors = load_reaction_file(path)

    media_errors, files, skipped = _check_media(tmp_path, rules)

    assert media_errors == []
    assert {p.name for p in files} == {"ok.mp4"}
    assert {p.name for p in skipped} == {"foto.avif"}
