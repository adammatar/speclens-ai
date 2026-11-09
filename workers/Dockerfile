FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY workers/pyproject.toml /app/workers/pyproject.toml
COPY workers/speclens_worker /app/workers/speclens_worker

WORKDIR /app/workers
RUN pip install --upgrade pip && pip install .

CMD ["celery", "-A", "speclens_worker.celery_app:app", "worker", "--loglevel=INFO"]
