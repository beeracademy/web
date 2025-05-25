FROM node:22-alpine AS builder

WORKDIR /build

COPY /svelte .

RUN ./build_components

FROM python:3.13

WORKDIR /app

COPY --from=builder /build/static /app/svelte/static
COPY --from=builder /build/templates/svelte_include_generated.html /app/svelte/templates/svelte_include_generated.html

COPY --from=ghcr.io/astral-sh/uv:0.7.8 /uv /uvx /bin/
COPY pyproject.toml uv.lock .
RUN uv sync --frozen --no-install-project --no-dev

COPY . /app
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

ENV DJANGO_SETTINGS_MODULE=academy.settings.production
ENV PYTHONUNBUFFERED=1

ARG GIT_COMMIT_HASH
ENV GIT_COMMIT_HASH="$GIT_COMMIT_HASH"

CMD ["./setup_and_run"]
