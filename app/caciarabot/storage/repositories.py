"""Small repository functions over the raw sqlite3 connection.

Kept as plain functions rather than an ORM/repository-class hierarchy:
the schema is five small tables and every query here is a single
statement, so an abstraction layer would add indirection without
buying anything.
"""

from __future__ import annotations

import sqlite3
import time


def touch_chat(conn: sqlite3.Connection, chat_id: int) -> None:
    now = time.time()
    conn.execute(
        """
        INSERT INTO chats (chat_id, first_seen_at, last_seen_at)
        VALUES (?, ?, ?)
        ON CONFLICT (chat_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
        """,
        (chat_id, now, now),
    )
    conn.execute(
        "INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)",
        (chat_id,),
    )


def get_chat_activity(conn: sqlite3.Connection, chat_id: int) -> float:
    row = conn.execute(
        "SELECT activity FROM chat_settings WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row["activity"] if row else 1.0


def get_chat_locale(conn: sqlite3.Connection, chat_id: int, default_locale: str) -> str:
    row = conn.execute(
        "SELECT locale FROM chat_settings WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row["locale"] if row else default_locale


def is_trigger_on_cooldown(
    conn: sqlite3.Connection, chat_id: int, trigger_id: str, cooldown_seconds: int
) -> bool:
    if cooldown_seconds <= 0:
        return False
    row = conn.execute(
        "SELECT last_fired_at FROM trigger_cooldowns WHERE chat_id = ? AND trigger_id = ?",
        (chat_id, trigger_id),
    ).fetchone()
    if row is None:
        return False
    return (time.time() - row["last_fired_at"]) < cooldown_seconds


def record_trigger_fired(conn: sqlite3.Connection, chat_id: int, trigger_id: str) -> None:
    conn.execute(
        """
        INSERT INTO trigger_cooldowns (chat_id, trigger_id, last_fired_at)
        VALUES (?, ?, ?)
        ON CONFLICT (chat_id, trigger_id) DO UPDATE SET last_fired_at = excluded.last_fired_at
        """,
        (chat_id, trigger_id, time.time()),
    )


def get_cached_file_id(conn: sqlite3.Connection, fingerprint: str) -> str | None:
    row = conn.execute(
        "SELECT file_id FROM file_id_cache WHERE fingerprint = ?", (fingerprint,)
    ).fetchone()
    return row["file_id"] if row else None


def set_cached_file_id(
    conn: sqlite3.Connection,
    fingerprint: str,
    file_id: str,
    media_type: str,
    source_path: str,
) -> None:
    conn.execute(
        """
        INSERT INTO file_id_cache (fingerprint, file_id, media_type, source_path, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (fingerprint) DO UPDATE SET
            file_id = excluded.file_id,
            media_type = excluded.media_type,
            source_path = excluded.source_path,
            created_at = excluded.created_at
        """,
        (fingerprint, file_id, media_type, source_path, time.time()),
    )


def increment_counter(conn: sqlite3.Connection, scope: str, key: str, amount: int = 1) -> None:
    conn.execute(
        """
        INSERT INTO stats_counters (scope, key, count)
        VALUES (?, ?, ?)
        ON CONFLICT (scope, key) DO UPDATE SET count = count + excluded.count
        """,
        (scope, key, amount),
    )


def get_counter(conn: sqlite3.Connection, scope: str, key: str) -> int:
    row = conn.execute(
        "SELECT count FROM stats_counters WHERE scope = ? AND key = ?", (scope, key)
    ).fetchone()
    return row["count"] if row else 0


def get_top_counters(conn: sqlite3.Connection, scope: str, limit: int = 5) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT key, count FROM stats_counters WHERE scope = ? ORDER BY count DESC LIMIT ?",
        (scope, limit),
    ).fetchall()


def get_all_chat_ids(conn: sqlite3.Connection) -> list[int]:
    return [row["chat_id"] for row in conn.execute("SELECT chat_id FROM chats")]


def record_digest_sent(conn: sqlite3.Connection, url_hash: str, url: str, title: str, source: str) -> None:
    conn.execute(
        """
        INSERT INTO digest_sent (url_hash, url, title, source, sent_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (url_hash) DO UPDATE SET sent_at = excluded.sent_at
        """,
        (url_hash, url, title, source, time.time()),
    )


def get_recent_digest_hashes(conn: sqlite3.Connection, within_days: int = 30) -> set[str]:
    cutoff = time.time() - within_days * 86400
    return {
        row["url_hash"]
        for row in conn.execute("SELECT url_hash FROM digest_sent WHERE sent_at >= ?", (cutoff,))
    }


def record_chat_member(conn: sqlite3.Connection, chat_id: int, user_id: int, display_name: str) -> None:
    conn.execute(
        """
        INSERT INTO chat_members (chat_id, user_id, display_name, last_seen_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET
            display_name = excluded.display_name,
            last_seen_at = excluded.last_seen_at
        """,
        (chat_id, user_id, display_name, time.time()),
    )


def get_chat_members(conn: sqlite3.Connection, chat_id: int) -> list[str]:
    return [
        row["display_name"]
        for row in conn.execute(
            "SELECT display_name FROM chat_members WHERE chat_id = ?", (chat_id,)
        )
    ]


def record_prompt_use(conn: sqlite3.Connection, pool: str, prompt_hash: str) -> None:
    conn.execute(
        "INSERT INTO prompt_history (pool, prompt_hash, used_at) VALUES (?, ?, ?)",
        (pool, prompt_hash, time.time()),
    )


def get_recent_prompt_hashes(conn: sqlite3.Connection, pool: str, limit: int) -> set[str]:
    if limit <= 0:
        return set()
    return {
        row["prompt_hash"]
        for row in conn.execute(
            "SELECT prompt_hash FROM prompt_history WHERE pool = ? ORDER BY id DESC LIMIT ?",
            (pool, limit),
        )
    }


def set_chat_awake(conn: sqlite3.Connection, chat_id: int, awake: bool) -> None:
    conn.execute(
        "UPDATE chat_settings SET awake = ? WHERE chat_id = ?", (1 if awake else 0, chat_id)
    )


def is_chat_awake(conn: sqlite3.Connection, chat_id: int) -> bool:
    row = conn.execute(
        "SELECT awake FROM chat_settings WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return bool(row["awake"]) if row else True


def get_awake_chat_ids(conn: sqlite3.Connection) -> list[int]:
    return [
        row["chat_id"]
        for row in conn.execute(
            """
            SELECT c.chat_id FROM chats c
            JOIN chat_settings s ON s.chat_id = c.chat_id
            WHERE s.awake = 1
            """
        )
    ]


def disable_category(conn: sqlite3.Connection, chat_id: int, category: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO chat_disabled_categories (chat_id, category) VALUES (?, ?)",
        (chat_id, category),
    )


def enable_category(conn: sqlite3.Connection, chat_id: int, category: str) -> None:
    conn.execute(
        "DELETE FROM chat_disabled_categories WHERE chat_id = ? AND category = ?",
        (chat_id, category),
    )


def get_disabled_categories(conn: sqlite3.Connection, chat_id: int) -> set[str]:
    return {
        row["category"]
        for row in conn.execute(
            "SELECT category FROM chat_disabled_categories WHERE chat_id = ?", (chat_id,)
        )
    }
