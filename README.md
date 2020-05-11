# Academy Web Server

[![Build and Deploy](https://github.com/beeracademy/web/workflows/Build%20and%20Deploy/badge.svg?branch=master)](https://github.com/beeracademy/web/actions)

Frontend and api server for Academy.

## Installation

Install Python 3.8 and create a virtual environment:
```sh
python -mvenv ~/.cache/venvs/academy-web
```

Inside the virtual enviroment install [pip-tools](https://github.com/jazzband/pip-tools):

```sh
pip install pip-tools
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
