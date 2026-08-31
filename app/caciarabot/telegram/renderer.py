"""Renders a Decision (text or local media) back to Telegram, using the file_id cache."""

from __future__ import annotations

from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, Message, ReactionTypeEmoji

from caciarabot.config.models import MediaResponse, RandomMediaResponse, TextResponse
from caciarabot.engine.decision import Decision
from caciarabot.logging_utils import log_event
from caciarabot.runtime import Runtime
from caciarabot.storage import get_cached_file_id, set_cached_file_id
from caciarabot.telegram.media import compute_fingerprint, media_kind, pick_random_media


def _resolve_media_path(runtime: Runtime, response: MediaResponse | RandomMediaResponse) -> Path:
    if isinstance(response, MediaResponse):
        return runtime.media_dir / response.path
    return pick_random_media(runtime.media_dir, response.directory)


async def _send_media(message: Message, kind: str, media: str | FSInputFile) -> Message:
    if kind == "video":
        return await message.answer_video(video=media)
    if kind == "animation":
        return await message.answer_animation(animation=media)
    return await message.answer_photo(photo=media)


def _sent_file_id(sent: Message, kind: str) -> str | None:
    if kind == "video":
        return sent.video.file_id if sent.video else None
    if kind == "animation":
        return sent.animation.file_id if sent.animation else None
    # Photos come back as a ladder of sizes; the last one is the largest.
    return sent.photo[-1].file_id if sent.photo else None


async def send_decision(message: Message, runtime: Runtime, decision: Decision) -> None:
    response = decision.response

    if isinstance(response, TextResponse):
        await message.answer(response.value)
        return

    try:
        path = _resolve_media_path(runtime, response)
    except FileNotFoundError as exc:
        log_event("reaction_send_failed", chat_id=message.chat.id, reason=str(exc))
        return

    # Derived from the extension rather than read back from the cache: a
    # file_id minted by sendPhoto cannot be replayed through sendVideo,
    # so the kind has to be a property of the file, not of the row.
    kind = media_kind(path)
    fingerprint = compute_fingerprint(path)
    cached_file_id = get_cached_file_id(runtime.db, fingerprint)

    try:
        sent = await _send_media(message, kind, cached_file_id or FSInputFile(path))
    except TelegramAPIError as exc:
        log_event(
            "reaction_send_failed", chat_id=message.chat.id, path=str(path), reason=str(exc)
        )
        return

    if not cached_file_id:
        file_id = _sent_file_id(sent, kind)
        if file_id:
            set_cached_file_id(runtime.db, fingerprint, file_id, kind, str(path))


async def send_emoji_reaction(bot: Bot, message: Message, emoji: str) -> None:
    try:
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
        )
    except TelegramAPIError as exc:
        log_event("emoji_reaction_failed", chat_id=message.chat.id, reason=str(exc))
