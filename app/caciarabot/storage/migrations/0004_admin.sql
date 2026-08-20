CREATE TABLE IF NOT EXISTS chat_disabled_categories (
    chat_id  INTEGER NOT NULL,
    category TEXT NOT NULL,
    PRIMARY KEY (chat_id, category)
);
