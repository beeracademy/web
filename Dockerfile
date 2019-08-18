FROM python:3.7

RUN pip install poetry

WORKDIR /app
COPY poetry.lock pyproject.toml /app/

RUN poetry config settings.virtualenvs.create false
RUN poetry install --no-dev --no-interaction

COPY . /app

CMD ["./setup_and_run"]
