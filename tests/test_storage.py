from pathlib import Path

from caciarabot.storage import (
    connect,
    disable_category,
    enable_category,
    get_awake_chat_ids,
    get_disabled_categories,
    is_chat_awake,
    set_chat_awake,
    touch_chat,
)


def _db(tmp_path: Path):
    return connect(tmp_path / "test.db")


def test_chat_awake_by_default(tmp_path: Path):
    conn = _db(tmp_path)
    touch_chat(conn, 1)
    assert is_chat_awake(conn, 1) is True


def test_unknown_chat_defaults_to_awake(tmp_path: Path):
    conn = _db(tmp_path)
    assert is_chat_awake(conn, 999) is True


def test_set_chat_awake_false_then_true(tmp_path: Path):
    conn = _db(tmp_path)
    touch_chat(conn, 1)
    set_chat_awake(conn, 1, False)
    assert is_chat_awake(conn, 1) is False
    set_chat_awake(conn, 1, True)
    assert is_chat_awake(conn, 1) is True


def test_get_awake_chat_ids_excludes_sleeping_chats(tmp_path: Path):
    conn = _db(tmp_path)
    touch_chat(conn, 1)
    touch_chat(conn, 2)
    touch_chat(conn, 3)
    set_chat_awake(conn, 2, False)

    awake = set(get_awake_chat_ids(conn))
    assert awake == {1, 3}


def test_disabled_categories_empty_by_default(tmp_path: Path):
    conn = _db(tmp_path)
    assert get_disabled_categories(conn, 1) == set()


def test_disable_then_enable_category(tmp_path: Path):
    conn = _db(tmp_path)
    disable_category(conn, 1, "technology")
    assert get_disabled_categories(conn, 1) == {"technology"}

    enable_category(conn, 1, "technology")
    assert get_disabled_categories(conn, 1) == set()


def test_disabled_categories_are_per_chat(tmp_path: Path):
    conn = _db(tmp_path)
    disable_category(conn, 1, "technology")
    assert get_disabled_categories(conn, 1) == {"technology"}
    assert get_disabled_categories(conn, 2) == set()


def test_disable_category_is_idempotent(tmp_path: Path):
    conn = _db(tmp_path)
    disable_category(conn, 1, "technology")
    disable_category(conn, 1, "technology")
    assert get_disabled_categories(conn, 1) == {"technology"}


def test_prompt_history_returns_most_recent_first(tmp_path: Path):
    from caciarabot.storage import get_recent_prompt_hashes, record_prompt_use

    conn = _db(tmp_path)
    for h in ("h1", "h2", "h3", "h4"):
        record_prompt_use(conn, "daily", h)

    assert get_recent_prompt_hashes(conn, "daily", 2) == {"h3", "h4"}
    assert get_recent_prompt_hashes(conn, "daily", 10) == {"h1", "h2", "h3", "h4"}


def test_prompt_history_is_per_pool(tmp_path: Path):
    from caciarabot.storage import get_recent_prompt_hashes, record_prompt_use

    conn = _db(tmp_path)
    record_prompt_use(conn, "daily", "mood")
    record_prompt_use(conn, "daily_depth", "depth")

    assert get_recent_prompt_hashes(conn, "daily", 5) == {"mood"}
    assert get_recent_prompt_hashes(conn, "daily_depth", 5) == {"depth"}


def test_prompt_history_zero_limit_returns_empty(tmp_path: Path):
    from caciarabot.storage import get_recent_prompt_hashes, record_prompt_use

    conn = _db(tmp_path)
    record_prompt_use(conn, "daily", "h1")
    assert get_recent_prompt_hashes(conn, "daily", 0) == set()
