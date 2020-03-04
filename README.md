# Academy Web Server

[![Build and Deploy](https://github.com/beeracademy/web/workflows/Build%20and%20Deploy/badge.svg?branch=master)](https://github.com/beeracademy/web/actions)

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
