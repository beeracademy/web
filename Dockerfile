FROM node:12-alpine as builder

COPY /svelte .

RUN yarn install --frozen-lockfile && yarn build

FROM python:3.8

WORKDIR /app

COPY --from=builder static /app/svelte/static

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app

ENV DJANGO_SETTINGS_MODULE=academy.settings.production
CMD ["./setup_and_run"]
