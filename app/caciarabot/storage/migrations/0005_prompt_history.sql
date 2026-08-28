CREATE TABLE IF NOT EXISTS prompt_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pool        TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    used_at     REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompt_history_pool_id ON prompt_history (pool, id DESC);
