FROM python:3.7

ENV DJANGO_SETTINGS_MODULE=academy.settings.production

RUN pip install poetry

WORKDIR /app
COPY poetry.lock pyproject.toml /app/

RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-interaction

COPY . /app

CMD ["./setup_and_run"]
