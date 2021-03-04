FROM node:12-alpine as builder

COPY /svelte .

RUN ./build_components

FROM python:3.9

WORKDIR /app

COPY --from=builder static /app/svelte/static

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV DJANGO_SETTINGS_MODULE=academy.settings.production

ARG GIT_COMMIT_HASH
ENV GIT_COMMIT_HASH $GIT_COMMIT_HASH

CMD ["./setup_and_run"]
