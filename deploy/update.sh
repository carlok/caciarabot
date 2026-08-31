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

# Bot settings moved from config/bot.jsonc into .env, so a leftover copy
# is now both ignored by the bot and in the way of a clean pull. Convert
# it before pulling, while it is still there to convert.
if [[ -f config/bot.jsonc ]]; then
    echo "==> config/bot.jsonc is obsolete: bot settings now live in .env"
    echo "    Your settings, as environment variables:"
    echo
    python3 deploy/bot_jsonc_to_env.py config/bot.jsonc | sed 's/^/      /'
    echo
    echo "    Save the ones you want, then get the file out of git's way:"
    echo "      python3 deploy/bot_jsonc_to_env.py config/bot.jsonc >> .env"
    echo "      \$EDITOR .env   # drop anything you do not actually want"
    echo "      git checkout -- config/bot.jsonc 2>/dev/null || rm -f config/bot.jsonc"
    echo
    echo "    (checkout succeeds only while the file is still tracked, in which"
    echo "     case the pull removes it for you; otherwise it is untracked and"
    echo "     the rm handles it.) Then run this script again."
    exit 1
fi

echo "==> git pull"
git pull

echo "==> fixing bind-mount permissions"
chmod -R o+rX config media
chmod 600 .env

echo "==> podman compose build $NOCACHE_FLAG"
podman compose build $NOCACHE_FLAG

echo "==> podman compose up -d"
podman compose up -d

# `up -d` leaves a running container alone when its image did not change,
# so a config-only update (a new JSONL rule, an edited prompt, a media
# folder) would otherwise be invisible: config/ is a read-only bind mount
# that the bot reads once at startup. caciarabot-validate reads it live,
# which makes the mismatch especially confusing -- the validator sees the
# new rule while the running bot does not. The restart is a couple of
# seconds and removes the whole class of problem.
echo "==> podman compose restart (config is read at startup)"
podman compose restart

echo "==> done"
podman compose logs --tail 10
