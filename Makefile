.PHONY: help install install-dev lint format typecheck test test-ml test-fast \
        docker-up docker-down docker-build docker-logs \
        dd-api dd-ui \
        train train-debug \
        data-pull data-push \
        mlflow-ui \
        clean

PYTHON := python
PIP    := pip
PYTEST := pytest
DC     := docker compose -f infrastructure/docker/docker-compose.yml

# ── Help ─────────────────────────────────────────────────────────────────────

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' | sort

# ── Setup ────────────────────────────────────────────────────────────────────

install: ## Install production dependencies
	$(PIP) install -r requirements-api.txt -r requirements-ml.txt
	$(PIP) install -e .

install-dev: install ## Install + dev tools (pre-commit, linters)
	$(PIP) install ruff mypy pytest pytest-cov pytest-asyncio pre-commit
	pre-commit install
	pre-commit install --hook-type commit-msg

# ── Code Quality ─────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	ruff check src/ tests/

format: ## Auto-format with ruff
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck: ## Run mypy type checking
	mypy --explicit-package-bases src/ --ignore-missing-imports

# ── Testing ──────────────────────────────────────────────────────────────────

test: ## Run all tests with coverage
	$(PYTEST) tests/ --cov=src --cov-report=term-missing -q

test-ml: ## Run only ML tests
	$(PYTEST) tests/ml/ -q

test-fast: ## Run tests excluding slow/integration tests
	$(PYTEST) tests/ -m "not slow and not integration" -q

test-validation: ## Run physics validation tests
	$(PYTEST) tests/validation/ -q

# ── Docker ───────────────────────────────────────────────────────────────────

docker-up: ## Start all local services (API, Postgres, Redis, MinIO, MLflow)
	$(DC) up -d
	@echo "Services:"
	@echo "  API:     http://localhost:8000"
	@echo "  MLflow:  http://localhost:5000"
	@echo "  MinIO:   http://localhost:9001  (user: minioadmin / minioadmin)"

docker-down: ## Stop all local services
	$(DC) down

docker-build: ## Rebuild all Docker images
	$(DC) build --no-cache

docker-logs: ## Tail logs from all services
	$(DC) logs -f

docker-ps: ## Show running containers
	$(DC) ps

# ── DD Laminate Research UI ─────────────────────────────────────────────────

dd-api: ## Run standalone DD laminate prediction API
	uvicorn src.backend.dd_laminate_app:app --reload --port 8000

dd-ui: ## Serve standalone DD laminate predictor UI
	python3 -m http.server 3000 --directory src/frontend/dd-laminate

# ── ML Training ──────────────────────────────────────────────────────────────

train: ## Run training with default config (set CFG= to override)
	$(PYTHON) -m src.ml.train $(CFG)

train-debug: ## Run training with debug config (fast, small data)
	$(PYTHON) -m src.ml.train +experiment=debug

# ── Data ─────────────────────────────────────────────────────────────────────

data-pull: ## Pull datasets from DVC remote
	dvc pull

data-push: ## Push new datasets to DVC remote
	dvc push

data-status: ## Show DVC data status
	dvc status

# ── MLflow ───────────────────────────────────────────────────────────────────

mlflow-ui: ## Open MLflow UI (requires docker-up)
	@echo "MLflow is running at http://localhost:5000"
	open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null || true

# ── Database ─────────────────────────────────────────────────────────────────

db-migrate: ## Run Alembic migrations
	alembic upgrade head

db-rollback: ## Roll back last migration
	alembic downgrade -1

# ── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts, caches, coverage reports
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.py[cod]" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
	rm -f coverage.xml .coverage

clean-docker: ## Remove Docker volumes (WARNING: deletes local DB and MinIO data)
	$(DC) down -v
