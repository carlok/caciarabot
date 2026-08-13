# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app
COPY locales ./locales

RUN uv sync --no-dev --no-editable

FROM python:3.12-slim AS runtime

RUN groupadd --gid 1000 caciarabot \
    && useradd --uid 1000 --gid caciarabot --create-home --shell /usr/sbin/nologin caciarabot

WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/locales /app/locales

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data && chown caciarabot:caciarabot /data

USER caciarabot

# Invoke the venv's python interpreter directly rather than the
# `caciarabot` console-script shim: uv bakes an absolute shebang path
# into that shim at build time (/build/.venv/...), which breaks once
# the venv is copied to its runtime location (/app/.venv/...).
ENTRYPOINT ["/app/.venv/bin/python", "-m", "caciarabot.main"]

# --- dev target -------------------------------------------------------
# Editable install at the same path (/app/app) that compose.dev.yaml
# bind-mounts the source tree over, so code edits take effect on
# `podman compose restart` with no image rebuild. Not used by default;
# select it with `podman compose -f compose.yaml -f compose.dev.yaml up`.
FROM python:3.12-slim AS dev

RUN pip install --no-cache-dir uv \
    && groupadd --gid 1000 caciarabot \
    && useradd --uid 1000 --gid caciarabot --create-home --shell /bin/bash caciarabot

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY locales ./locales

RUN uv sync

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data && chown caciarabot:caciarabot /data

USER caciarabot

ENTRYPOINT ["/app/.venv/bin/python", "-m", "caciarabot.main"]
