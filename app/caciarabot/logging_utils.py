"""Structured-ish English log lines (spec section 32): `event key=value key=value`."""

from __future__ import annotations

import logging

logger = logging.getLogger("caciarabot")


def log_event(event: str, **fields: object) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("%s %s", event, rendered_fields)
