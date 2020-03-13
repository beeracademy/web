FROM node:12-alpine as builder

COPY /svelte .

RUN yarn install && yarn build

FROM python:3.8

RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-dev --no-interaction

COPY . /app
COPY --from=builder static /app/svelte/static

ENV DJANGO_SETTINGS_MODULE=academy.settings.production
CMD ["./setup_and_run"]
