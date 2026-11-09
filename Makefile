# --env-file .env injects Gemini/OpenAI settings into Compose ${VAR} interpolation.
COMPOSE := docker compose --env-file .env -f infra/compose.yaml
COMPOSE_PROD := docker compose --env-file .env -f infra/compose.prod.yaml
PYTHON ?= python3
API_DIR := services/api

.PHONY: help up up-prod down logs build migrate test lint typecheck format contracts smoke clean install-dev eval web web-build demo-reset portfolio-media

help:
	@echo "SpecLens AI developer targets"
	@echo "  make up         Start Compose stack (postgres, redis, api, worker)"
	@echo "  make up-prod    Production-style Compose including React web (:8080)"
	@echo "  make down       Stop Compose stack"
	@echo "  make migrate    Run Alembic migrations against Compose Postgres"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run ruff check + format check"
	@echo "  make typecheck  Run mypy"
	@echo "  make contracts  Generate OpenAPI + TypeScript stub types"
	@echo "  make smoke      Compose up + health/ready smoke checks"
	@echo "  make eval       Run offline evaluation harness (JSON + HTML reports)"
	@echo "  make web        Run React+Vite dev server"
	@echo "  make web-build  Production build of apps/web"
	@echo "  make demo-reset Reset default workspace and re-seed sample.md"
	@echo "  make portfolio-media  Playwright screenshots + demo video"
	@echo "  make install-dev Install local Python dev dependencies"

install-dev:
	$(PYTHON) -m pip install -e "$(API_DIR)[dev]"
	$(PYTHON) -m pip install -e "workers[dev]"

up:
	@test -f .env || cp .env.example .env
	$(COMPOSE) up -d --build

up-prod:
	@test -f .env || cp .env.example .env
	$(COMPOSE_PROD) up -d --build

down:
	@test -f .env || cp .env.example .env
	$(COMPOSE) down -v

logs:
	@test -f .env || cp .env.example .env
	$(COMPOSE) logs -f

build:
	@test -f .env || cp .env.example .env
	$(COMPOSE) build

migrate:
	@test -f .env || cp .env.example .env
	$(COMPOSE) run --rm api alembic upgrade head

test:
	$(PYTHON) -m pytest

lint:
	ruff check services/api workers evals scripts
	ruff format --check services/api workers evals scripts

typecheck:
	mypy --config-file=pyproject.toml

format:
	ruff check --fix services/api workers evals scripts
	ruff format services/api workers evals scripts

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

eval:
	PYTHONPATH=. $(PYTHON) -m evals.harness $(if $(EVAL_ENFORCE),--enforce,)

web:
	cd apps/web && npm install && npm run dev

web-build:
	cd apps/web && npm install && npm run build

demo-reset:
	./scripts/demo_reset.sh

portfolio-media:
	cd apps/web && npx playwright install chromium
	$(PYTHON) -c "print('Ensure web preview on :4173 then capturing…')"
	node scripts/capture_portfolio_media.mjs

clean:
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE_PROD) down -v --remove-orphans || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
