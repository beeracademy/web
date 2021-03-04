# Academy Web Server

[![Build, Test & Deploy](https://github.com/beeracademy/web/workflows/Build,%20Test%20&%20Deploy/badge.svg?branch=master)](https://github.com/beeracademy/web/actions)

Frontend and api server for Academy.

## Installation

Install Python 3.9 and create a virtual environment:
```sh
python -mvenv ~/.cache/venvs/academy-web
```

Inside the virtual enviroment install [pip-tools](https://github.com/jazzband/pip-tools) and install our dependencies with `pip-sync`:

```sh
pip install pip-tools
pip-sync requirements.txt dev-requirements.txt
```

Install pre-commit hook to ensure files are formatted correctly:

```sh
pre-commit install
```

Then apply the database migrations:

```sh
./manage.py migrate
```

## Running

To start the server locally run:

```sh
./manage.py runserver
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
