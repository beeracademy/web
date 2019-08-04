# Academy Web Server

Frontend and api server for Academy.

## Installation

Install Python 3.7 and [Pipenv](https://docs.pipenv.org/).

To install the python dependencies run:

```sh
pipenv install
```

Then apply the database migrations:

```sh
pipenv run ./manage.py migrate
```

## Running

To start the server locally run:

```sh
pipenv run ./manage.py runserver
```
