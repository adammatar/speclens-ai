FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/api/pyproject.toml /app/services/api/pyproject.toml
COPY services/api/app /app/services/api/app
COPY services/api/migrations /app/services/api/migrations
COPY services/api/alembic.ini /app/services/api/alembic.ini

WORKDIR /app/services/api
RUN pip install --upgrade pip && pip install .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
