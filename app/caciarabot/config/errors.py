"""Structured configuration errors carrying enough detail to fix the file."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfigError:
    file: str
    message: str
    line: int | None = None
    field: str | None = None
    record_id: str | None = None

    def __str__(self) -> str:
        location = self.file
        if self.line is not None:
            location += f":{self.line}"
        parts = [location]
        if self.record_id is not None:
            parts.append(f"id={self.record_id}")
        if self.field is not None:
            parts.append(f"field={self.field}")
        parts.append(self.message)
        return " ".join(parts)


class ConfigValidationError(Exception):
    """Raised when one or more configuration files fail validation."""

    def __init__(self, errors: list[ConfigError]):
        self.errors = errors
        super().__init__("\n".join(str(e) for e in errors))
