# Academy Web Server

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
