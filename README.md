# Academy Web Server

[![Build, Test & Deploy](https://github.com/beeracademy/web/workflows/Build,%20Test%20&%20Deploy/badge.svg?branch=master)](https://github.com/beeracademy/web/actions)

Frontend and api server for Academy.

## Installation

Install [`uv`](https://docs.astral.sh/uv/) and run:
```sh
uv sync
```

Install pre-commit hook to ensure files are formatted correctly:

```sh
uv run pre-commit install
```

Then apply the database migrations:

```sh
uv run ./manage.py migrate
```

## Running

To start the server locally run:

```sh
uv run ./manage.py runserver
```

## Compiling Svelte components

Some views uses [Svelte](https://svelte.dev/) components, which needs to be compiled.
To do this, run the following:

```sh
cd svelte
./build_components
```

## Generating Facebook access token

- Create a Facebook app: https://developers.facebook.com/apps/ (Disable uBlock Origin)
- Open the Graph API explorer: https://developers.facebook.com/tools/explorer
- Generate a User Token with permission `pages_manage_posts`
- Run `./get_facebook_access_token` with the required arguments. It will output a Page Access Token that will never expire.
