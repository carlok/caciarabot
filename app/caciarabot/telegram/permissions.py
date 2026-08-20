"""Authorization for admin-only commands.

`get_chat_member` is injected (rather than importing aiogram's Bot
directly) so the authorization logic itself stays testable with a
plain stub callable, matching the project's convention of keeping
decision logic free of the Telegram transport.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

_ADMIN_STATUSES = ("administrator", "creator")


async def is_authorized(
    get_chat_member: Callable[[int, int], Awaitable[object]],
    chat_id: int,
    user_id: int,
    owner_id: int | None,
) -> bool:
    if owner_id is not None and user_id == owner_id:
        return True

    try:
        member = await get_chat_member(chat_id, user_id)
    except Exception:  # noqa: BLE001 - any Telegram API failure means "can't confirm admin"
        return False

    return getattr(member, "status", None) in _ADMIN_STATUSES
