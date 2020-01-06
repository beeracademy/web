FROM node:12-alpine as builder

COPY /svelte .

RUN npm install
RUN npx rollup -c

FROM python:3.7

RUN pip install poetry
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-dev --no-interaction

COPY . /app
COPY --from=builder static /app/svelte/static

ENV DJANGO_SETTINGS_MODULE=academy.settings.production
CMD ["./setup_and_run"]
