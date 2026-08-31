from pathlib import Path

from caciarabot.config.reactions import load_reaction_file


def test_valid_jsonl_loads_without_errors(tmp_path: Path):
    jsonl_path = tmp_path / "reactions.jsonl"
    jsonl_path.write_text(
        '{"id":"buongiorno","category":"greetings","match":{"type":"word","values":["buongiorno"]},'
        '"probability":0.5,"responses":[{"type":"text","value":"Eh.","weight":1}]}\n'
    )

    rules, errors = load_reaction_file(jsonl_path)

    assert errors == []
    assert len(rules) == 1
    assert rules[0].id == "buongiorno"


def test_malformed_json_reports_exact_line_number(tmp_path: Path):
    jsonl_path = tmp_path / "reactions.jsonl"
    jsonl_path.write_text(
        '{"id":"buongiorno","category":"greetings","match":{"type":"word","values":["buongiorno"]},'
        '"probability":0.5,"responses":[{"type":"text","value":"Eh.","weight":1}]}\n'
        "{this is not valid json}\n"
    )

    rules, errors = load_reaction_file(jsonl_path)

    assert len(rules) == 1
    assert len(errors) == 1
    assert errors[0].line == 2
    assert str(jsonl_path) == errors[0].file


def test_schema_violation_reports_field_and_record_id(tmp_path: Path):
    jsonl_path = tmp_path / "reactions.jsonl"
    jsonl_path.write_text(
        '{"id":"buongiorno","category":"greetings","match":{"type":"word","values":["buongiorno"]},'
        '"probability":2.5,"responses":[{"type":"text","value":"Eh.","weight":1}]}\n'
    )

    rules, errors = load_reaction_file(jsonl_path)

    assert rules == []
    assert len(errors) == 1
    assert errors[0].record_id == "buongiorno"
    assert errors[0].line == 1


def test_one_bad_line_does_not_block_the_rest(tmp_path: Path):
    jsonl_path = tmp_path / "reactions.jsonl"
    jsonl_path.write_text(
        "{not valid}\n"
        '{"id":"disastro","category":"general","match":{"type":"word","values":["disastro"]},'
        '"responses":[{"type":"text","value":"Eh.","weight":1}]}\n'
    )

    rules, errors = load_reaction_file(jsonl_path)

    assert len(errors) == 1
    assert len(rules) == 1
    assert rules[0].id == "disastro"


def test_missing_media_file_is_detected_by_the_validator_helper(tmp_path: Path):
    from caciarabot.validate import _check_media

    jsonl_path = tmp_path / "reactions.jsonl"
    jsonl_path.write_text(
        '{"id":"buongiorno","category":"greetings","match":{"type":"word","values":["buongiorno"]},'
        '"responses":[{"type":"photo","path":"images/missing.jpg","weight":1}]}\n'
    )
    rules, errors = load_reaction_file(jsonl_path)
    assert errors == []

    media_errors, media_files, _skipped = _check_media(tmp_path, rules)

    assert len(media_errors) == 1
    assert "missing.jpg" in media_errors[0].message
    assert media_files == set()
