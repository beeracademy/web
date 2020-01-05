FROM python:3.7

RUN pip install poetry
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-dev --no-interaction

COPY . /app

ENV DJANGO_SETTINGS_MODULE=academy.settings.production
CMD ["./setup_and_run"]
