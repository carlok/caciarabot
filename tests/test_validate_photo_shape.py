"""The validator reports a photo Telegram would reject for its shape."""

from pathlib import Path

from caciarabot.config.reactions import load_reaction_file
from caciarabot.validate import _check_media

from tests.test_imagesize import _jpeg, _png


def _rules(tmp_path: Path):
    jsonl = tmp_path / "rules.jsonl"
    jsonl.write_text(
        '{"id":"pano","category":"general","match":{"type":"word","values":["pano"]},'
        '"probability":1,"cooldownSeconds":0,'
        '"responses":[{"type":"randomMedia","directory":"images/pano","weight":1}]}\n'
    )
    rules, errors = load_reaction_file(jsonl)
    assert errors == []
    return rules


def test_over_ratio_photo_is_reported(tmp_path: Path):
    media = tmp_path / "media"
    (media / "images" / "pano").mkdir(parents=True)
    (media / "images" / "pano" / "wide.jpg").write_bytes(_jpeg(4100, 200))
    (media / "images" / "pano" / "fine.png").write_bytes(_png(800, 600))

    errors, _seen, _skipped = _check_media(media, _rules(tmp_path))

    assert len(errors) == 1
    assert errors[0].file.endswith("wide.jpg")
    assert "aspect ratio" in errors[0].message


def test_normal_photos_pass(tmp_path: Path):
    media = tmp_path / "media"
    (media / "images" / "pano").mkdir(parents=True)
    (media / "images" / "pano" / "a.jpg").write_bytes(_jpeg(4000, 3000))

    errors, _seen, _skipped = _check_media(media, _rules(tmp_path))

    assert errors == []
