CREATE TABLE IF NOT EXISTS digest_sent (
    url_hash TEXT PRIMARY KEY,
    url      TEXT NOT NULL,
    title    TEXT NOT NULL,
    source   TEXT NOT NULL,
    sent_at  REAL NOT NULL
);
