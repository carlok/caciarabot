"""JSONL reaction record loading.

Each line is an independent JSON document. A malformed line is reported
with its exact file name and line number and does not prevent the rest
of the file (or other files) from loading — the caller collects every
error and decides whether the overall configuration is still usable.
"""

from __future__ import annotations

import json
from pathlib import Path

from caciarabot.config.errors import ConfigError
from caciarabot.config.models import (
    Match,
    PhotoResponse,
    PhraseMatch,
    RandomPhotoResponse,
    ReactionRule,
    Response,
    TextResponse,
    WordMatch,
    normalization_options_from_dict,
)
from caciarabot.config.validation import validate_instance


def _parse_match(data: dict) -> Match:
    match_type = data["type"]
    values = tuple(data["values"])
    if match_type == "word":
        return WordMatch(values=values)
    if match_type == "phrase":
        return PhraseMatch(values=values)
    raise ValueError(f"unsupported match type: {match_type!r}")


def _parse_response(data: dict) -> Response:
    response_type = data["type"]
    weight = float(data["weight"])
    if response_type == "text":
        return TextResponse(value=data["value"], weight=weight)
    if response_type == "photo":
        return PhotoResponse(path=data["path"], weight=weight)
    if response_type == "randomPhoto":
        return RandomPhotoResponse(directory=data["directory"], weight=weight)
    raise ValueError(f"unsupported response type: {response_type!r}")


def _parse_record(data: dict, source_file: str, line_number: int) -> ReactionRule:
    return ReactionRule(
        id=data["id"],
        category=data["category"],
        match=_parse_match(data["match"]),
        responses=tuple(_parse_response(r) for r in data["responses"]),
        probability=data.get("probability", 1.0),
        cooldown_seconds=data.get("cooldownSeconds", 0),
        priority=data.get("priority", 0),
        normalization_override=normalization_options_from_dict(data.get("normalization")),
        source_file=source_file,
        source_line=line_number,
    )


def load_reaction_file(path: Path) -> tuple[list[ReactionRule], list[ConfigError]]:
    rules: list[ReactionRule] = []
    errors: list[ConfigError] = []

    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    ConfigError(
                        file=str(path),
                        line=line_number,
                        message=f"invalid JSON: {exc.msg}",
                    )
                )
                continue

            record_id = data.get("id") if isinstance(data, dict) else None
            schema_errors = validate_instance(
                data, "reaction.schema.json", str(path), record_id=record_id
            )
            if schema_errors:
                for error in schema_errors:
                    errors.append(
                        ConfigError(
                            file=error.file,
                            line=line_number,
                            message=error.message,
                            field=error.field,
                            record_id=error.record_id,
                        )
                    )
                continue

            try:
                rules.append(_parse_record(data, str(path), line_number))
            except (KeyError, ValueError) as exc:
                errors.append(
                    ConfigError(
                        file=str(path),
                        line=line_number,
                        message=str(exc),
                        record_id=record_id,
                    )
                )

    return rules, errors


def load_reaction_pack(pack_dir: Path) -> tuple[list[ReactionRule], list[ConfigError]]:
    all_rules: list[ReactionRule] = []
    all_errors: list[ConfigError] = []

    for jsonl_file in sorted(pack_dir.glob("*.jsonl")):
        rules, errors = load_reaction_file(jsonl_file)
        all_rules.extend(rules)
        all_errors.extend(errors)

    return all_rules, all_errors
