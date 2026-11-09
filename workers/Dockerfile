FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Worker runs ingestion pipeline code from the API package.
COPY services/api/pyproject.toml /app/services/api/pyproject.toml
COPY services/api/app /app/services/api/app
COPY services/api/alembic.ini /app/services/api/alembic.ini
COPY services/api/migrations /app/services/api/migrations

COPY workers/pyproject.toml /app/workers/pyproject.toml
COPY workers/speclens_worker /app/workers/speclens_worker

RUN pip install --upgrade pip \
    && pip install /app/services/api \
    && pip install /app/workers

WORKDIR /app/workers

CMD ["celery", "-A", "speclens_worker.celery_app:app", "worker", "--loglevel=INFO"]
