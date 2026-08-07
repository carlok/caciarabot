CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    first_seen_at REAL NOT NULL,
    last_seen_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id INTEGER PRIMARY KEY REFERENCES chats (chat_id),
    locale TEXT NOT NULL DEFAULT 'it',
    activity REAL NOT NULL DEFAULT 1.0,
    awake INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS trigger_cooldowns (
    chat_id INTEGER NOT NULL,
    trigger_id TEXT NOT NULL,
    last_fired_at REAL NOT NULL,
    PRIMARY KEY (chat_id, trigger_id)
);

CREATE TABLE IF NOT EXISTS file_id_cache (
    fingerprint TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    media_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stats_counters (
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scope, key)
);
