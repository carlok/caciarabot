# Local media

Drop image files here to back the `randomPhoto` responses referenced
from `config/packs/*/*.jsonl`.

Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`.

- `images/buongiorno/` — used by the `buongiorno` reaction.
- `images/disastro/` — used by the `disastro` reaction.

This directory is mounted read-only into the container. Add or replace
files directly; the bot re-uploads a file to Telegram only once and
caches the resulting `file_id` keyed by path + size + modification
time, so replacing a file invalidates the cache automatically.
