#!/usr/bin/env bash
# One-command update: pull, fix bind-mount permissions, rebuild, restart.
#
# The chmod step exists because of a recurring rootless-Podman gotcha: the
# container's non-root user (UID 1000) doesn't map to your host user, so
# freshly git-pulled files under config/ and media/ need to be explicitly
# made world-readable, or the bot fails at startup with
# `PermissionError: [Errno 13] Permission denied: ...`. See README.md's
# "Bind mount permissions" section for the underlying cause and a
# permanent per-account fix (correcting your shell's umask) -- this script
# is the pragmatic workaround for as long as that isn't fixed.
#
# Usage: ./deploy/update.sh [--no-cache]

set -euo pipefail
cd "$(dirname "$0")/.."

NOCACHE_FLAG=""
if [[ "${1:-}" == "--no-cache" ]]; then
    NOCACHE_FLAG="--no-cache"
fi

echo "==> git pull"
git pull

# config/bot.jsonc is gitignored (per-deployment settings); only the
# template is tracked. Create it on first run so a fresh clone works.
if [[ ! -f config/bot.jsonc ]]; then
    echo "==> config/bot.jsonc missing, creating it from config/bot.jsonc.example"
    cp config/bot.jsonc.example config/bot.jsonc
fi

echo "==> fixing bind-mount permissions"
chmod -R o+rX config media
chmod 600 .env

echo "==> podman compose build $NOCACHE_FLAG"
podman compose build $NOCACHE_FLAG

echo "==> podman compose up -d"
podman compose up -d

echo "==> done"
podman compose logs --tail 10
