CREATE TABLE IF NOT EXISTS chat_members (
    chat_id      INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    last_seen_at REAL NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
