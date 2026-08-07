"""Renders a Decision (text or local photo) back to Telegram, using the file_id cache."""

from __future__ import annotations

from pathlib import Path

from aiogram.types import FSInputFile, Message

from caciarabot.config.models import PhotoResponse, RandomPhotoResponse, TextResponse
from caciarabot.engine.decision import Decision
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import get_cached_file_id, set_cached_file_id
from caciarabot.telegram.media import compute_fingerprint, pick_random_photo


def _resolve_photo_path(runtime: Runtime, response: PhotoResponse | RandomPhotoResponse) -> Path:
    if isinstance(response, PhotoResponse):
        return runtime.media_dir / response.path
    return pick_random_photo(runtime.media_dir, response.directory)


async def send_decision(message: Message, runtime: Runtime, decision: Decision) -> None:
    response = decision.response

    if isinstance(response, TextResponse):
        await message.answer(response.value)
        return

    try:
        path = _resolve_photo_path(runtime, response)
    except FileNotFoundError as exc:
        log_event("reaction_send_failed", chat_id=message.chat.id, reason=str(exc))
        return

    fingerprint = compute_fingerprint(path)
    cached_file_id = get_cached_file_id(runtime.db, fingerprint)
    photo = cached_file_id or FSInputFile(path)

    sent = await message.answer_photo(photo=photo)

    if not cached_file_id and sent.photo:
        set_cached_file_id(runtime.db, fingerprint, sent.photo[-1].file_id, "photo", str(path))
