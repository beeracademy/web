# Academy Web Server

[![Docker Build Status](https://img.shields.io/docker/cloud/build/beeracademy/web?style=for-the-badge)](https://hub.docker.com/r/beeracademy/web)
[![Docker Pulls](https://img.shields.io/docker/pulls/beeracademy/web?style=for-the-badge)](https://hub.docker.com/r/beeracademy/web)

Frontend and api server for Academy.

## Installation

Install Python 3.7 and [Poetry](https://poetry.eustace.io/).

To install the python dependencies run:

```sh
poetry install
```

Then apply the database migrations:

```sh
poetry run ./manage.py migrate
```

## Running

To start the server locally run:

```sh
poetry run ./manage.py runserver
```

## Compiling Svelte components

Some views uses [Svelte](https://svelte.dev/) components, which needs to be compiled.
To do this, run the following:
```sh
cd svelte
npm install
npx rollup -c
```
