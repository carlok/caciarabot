"""JSON Schema validation against the schemas bundled in the caciarabot package.

Schemas live inside the package itself (rather than a top-level
`schemas/` directory) so this path resolution keeps working whether
the package is run from source or installed as a wheel into
site-packages.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

from caciarabot.config.errors import ConfigError

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


@lru_cache(maxsize=None)
def _load_schema(schema_filename: str) -> dict:
    import json

    return json.loads((_SCHEMAS_DIR / schema_filename).read_text(encoding="utf-8"))


def validate_instance(
    instance: Any, schema_filename: str, source_file: str, record_id: str | None = None
) -> list[ConfigError]:
    schema = _load_schema(schema_filename)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)

    errors: list[ConfigError] = []
    for error in validator.iter_errors(instance):
        field_path = ".".join(str(p) for p in error.absolute_path) or None
        errors.append(
            ConfigError(
                file=source_file,
                message=error.message,
                field=field_path,
                record_id=record_id,
            )
        )
    return errors
