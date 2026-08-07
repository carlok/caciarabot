"""Minimal JSONC support: strip `//` and `/* */` comments, then parse as JSON.

Comments are stripped by scanning character-by-character so that `//` or
`/*` occurring inside a JSON string literal is left untouched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from caciarabot.config.errors import ConfigError, ConfigValidationError


def strip_jsonc_comments(text: str) -> str:
    result: list[str] = []
    i = 0
    length = len(text)
    in_string = False
    escape_next = False

    while i < length:
        ch = text[i]

        if in_string:
            result.append(ch)
            if escape_next:
                escape_next = False
            elif ch == "\\":
                escape_next = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < length and text[i + 1] == "/":
            while i < length and text[i] not in ("\n", "\r"):
                i += 1
            continue

        if ch == "/" and i + 1 < length and text[i + 1] == "*":
            i += 2
            while i + 1 < length and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] in ("\n", "\r"):
                    result.append(text[i])
                i += 1
            i += 2
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def load_jsonc(path: Path) -> Any:
    raw_text = path.read_text(encoding="utf-8")
    stripped = strip_jsonc_comments(raw_text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(
            [ConfigError(file=str(path), line=exc.lineno, message=f"invalid JSON: {exc.msg}")]
        ) from exc
