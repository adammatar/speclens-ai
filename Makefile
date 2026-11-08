COMPOSE := docker compose -f infra/compose.yaml
PYTHON ?= python3
API_DIR := services/api

.PHONY: help up down logs build migrate test lint typecheck format contracts smoke clean install-dev

help:
	@echo "SpecLens AI developer targets"
	@echo "  make up         Start Compose stack (postgres, redis, api, worker)"
	@echo "  make down       Stop Compose stack"
	@echo "  make migrate    Run Alembic migrations against Compose Postgres"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run ruff check + format check"
	@echo "  make typecheck  Run mypy"
	@echo "  make contracts  Generate OpenAPI + TypeScript stub types"
	@echo "  make smoke      Compose up + health/ready smoke checks"
	@echo "  make install-dev Install local Python dev dependencies"

install-dev:
	$(PYTHON) -m pip install -e "$(API_DIR)[dev]"
	$(PYTHON) -m pip install -e "workers[dev]"

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build

migrate:
	$(COMPOSE) run --rm api alembic upgrade head

test:
	$(PYTHON) -m pytest

lint:
	ruff check services/api workers
	ruff format --check services/api workers

typecheck:
	mypy --config-file=pyproject.toml

format:
	ruff check --fix services/api workers
	ruff format services/api workers

contracts:
	$(PYTHON) scripts/export_openapi.py
	cd packages/contracts && npm install && npm run generate

smoke: up
	@echo "Waiting for API..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
		if curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null; then break; fi; \
		sleep 2; \
	done
	curl -sf http://127.0.0.1:8000/api/v1/health | grep -q '"status":"ok"'
	curl -sf http://127.0.0.1:8000/api/v1/ready | grep -q '"status":"ok"'
	@echo "Smoke checks passed"

clean:
	$(COMPOSE) down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
