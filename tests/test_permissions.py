from dataclasses import dataclass

from caciarabot.telegram.permissions import is_authorized


@dataclass
class _FakeMember:
    status: str


async def test_owner_is_always_authorized_regardless_of_membership():
    async def get_chat_member(chat_id, user_id):
        return _FakeMember(status="member")

    assert await is_authorized(get_chat_member, chat_id=1, user_id=42, owner_id=42) is True


async def test_administrator_is_authorized():
    async def get_chat_member(chat_id, user_id):
        return _FakeMember(status="administrator")

    assert await is_authorized(get_chat_member, chat_id=1, user_id=7, owner_id=None) is True


async def test_creator_is_authorized():
    async def get_chat_member(chat_id, user_id):
        return _FakeMember(status="creator")

    assert await is_authorized(get_chat_member, chat_id=1, user_id=7, owner_id=None) is True


async def test_plain_member_is_not_authorized():
    async def get_chat_member(chat_id, user_id):
        return _FakeMember(status="member")

    assert await is_authorized(get_chat_member, chat_id=1, user_id=7, owner_id=None) is False


async def test_api_failure_denies_authorization():
    async def get_chat_member(chat_id, user_id):
        raise RuntimeError("boom")

    assert await is_authorized(get_chat_member, chat_id=1, user_id=7, owner_id=None) is False


async def test_no_owner_configured_and_not_admin_denies():
    async def get_chat_member(chat_id, user_id):
        return _FakeMember(status="left")

    assert await is_authorized(get_chat_member, chat_id=1, user_id=7, owner_id=None) is False
