SHELL := /bin/bash
.DEFAULT_GOAL := help
export UV_CACHE_DIR ?= $(CURDIR)/.cache/uv

.PHONY: help setup dev build-index benchmark test lint docs-serve docs-build docker-up deploy-backend deploy-frontend

help:
	@awk 'BEGIN {FS = ":.*## "; printf "Vaaani commands:\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install locked Python and frontend dependencies
	uv sync --project backend --all-groups
	npm --prefix frontend install

dev: ## Run API and web application together
	@trap 'kill 0' INT TERM EXIT; \
	VAAANI_QDRANT_URL=$${VAAANI_QDRANT_URL:-:memory:} uv run --project backend uvicorn vaaani.main:app --reload --host 0.0.0.0 --port 8000 & \
	npm --prefix frontend run dev & \
	wait

build-index: ## Load MSMARCO-XI and rebuild the selected Qdrant index
	uv run --project backend python backend/scripts/build_index.py

benchmark: ## Benchmark the pipeline and write JSON + Markdown reports
	uv run --project backend python backend/scripts/run_benchmark.py

test: ## Run backend and frontend tests
	uv run --project backend pytest backend/tests
	npm --prefix frontend test

lint: ## Run Python and TypeScript linters
	uv run --project backend ruff check backend
	npm --prefix frontend run lint

docs-serve: ## Serve documentation locally
	uv run --project backend mkdocs serve

docs-build: ## Build the documentation site
	uv run --project backend mkdocs build --strict

docker-up: ## Start local Qdrant and API
	docker compose up --build

deploy-backend: ## Deploy the backend with Railway CLI
	@command -v railway >/dev/null || { echo 'Install: npm i -g @railway/cli'; exit 1; }
	railway up --service backend

deploy-frontend: ## Deploy the frontend with Vercel CLI
	@npx vercel --cwd frontend --prod
