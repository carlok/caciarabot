# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS builder

# gcr.io/distroless/python3-debian12 ships Debian's Python 3.11. Build the
# production venv against the same interpreter path (/usr/bin/python3) that
# exists in that runtime image (see the symlink step below).
RUN pip install --no-cache-dir uv \
    && ln -sf /usr/local/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/local/bin/python3.11 /usr/bin/python3

ENV UV_PYTHON=/usr/bin/python3

WORKDIR /build
COPY pyproject.toml README.md uv.lock ./
COPY app ./app
COPY locales ./locales

RUN uv sync --frozen --no-dev --no-editable \
    && chmod -R a+rX /build

FROM python:3.11-slim-bookworm AS runtime-prep

RUN mkdir -p /data && chown 65532:65532 /data

# Public Distroless Python on Debian 12 (no extra registry auth in CI).
# Docker Hardened Images publish a drop-in alternative when your registry
# provides them without authentication.
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

COPY --from=runtime-prep --chown=65532:65532 /data /data
COPY --from=builder --chown=65532:65532 /build/.venv /app/.venv
COPY --from=builder --chown=65532:65532 /build/locales /app/locales

ENV PYTHONUNBUFFERED=1

# Invoke the venv interpreter directly rather than the `caciarabot`
# console-script shim: uv bakes an absolute shebang path into that shim at
# build time (/build/.venv/...), which breaks once the venv is copied to its
# runtime location (/app/.venv/...).
ENTRYPOINT ["/app/.venv/bin/python3", "-m", "caciarabot.main"]

# --- dev target -------------------------------------------------------
# Editable install at the same path (/app/app) that compose.dev.yaml
# bind-mounts the source tree over, so code edits take effect on
# `podman compose restart` with no image rebuild. Not used by default;
# select it with `podman compose -f compose.yaml -f compose.dev.yaml up`.
FROM python:3.12-slim-bookworm AS dev

RUN pip install --no-cache-dir uv \
    && groupadd --gid 1000 caciarabot \
    && useradd --uid 1000 --gid caciarabot --create-home --shell /bin/bash caciarabot

WORKDIR /app
COPY pyproject.toml README.md uv.lock ./
COPY app ./app
COPY locales ./locales

RUN uv sync --frozen

# See the identical step in the runtime stage above -- same reasoning.
# Note this only covers the image-baked copy; compose.dev.yaml's bind
# mount of the host ./app over /app/app at runtime still needs the host
# checkout itself to be readable (the general host-side fix covers this).
RUN chmod -R a+rX /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data && chown caciarabot:caciarabot /data

USER caciarabot

ENTRYPOINT ["/app/.venv/bin/python", "-m", "caciarabot.main"]
