.PHONY: help build up down restart logs test clean migrate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start services
	docker-compose up -d

down: ## Stop services
	docker-compose down

restart: ## Restart services
	docker-compose restart

logs: ## Show logs
	docker-compose logs -f

test: ## Run tests
	docker-compose exec -e TEST_DATABASE_URL=postgresql://semantic_user:semantic_pass@db:5432/semantic_sql_test api pytest

coverage: ## Run tests with coverage
	docker-compose exec -e TEST_DATABASE_URL=postgresql://semantic_user:semantic_pass@db:5432/semantic_sql_test api pytest --cov=src --cov-report=html --cov-report=term


test-verbose: ## Run tests in verbose mode
	docker-compose exec -e TEST_DATABASE_URL=postgresql://semantic_user:semantic_pass@db:5432/semantic_sql_test api pytest -v

migrate: ## Run database migrations
	docker-compose exec api alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MESSAGE="description")
	docker-compose exec api alembic revision --autogenerate -m "$(MESSAGE)"

shell: ## Open Python shell
	docker-compose exec api python

db-shell: ## Open database shell
	docker-compose exec db psql -U semantic_user -d semantic_sql

clean: ## Remove containers and volumes
	docker-compose down -v

health: ## Check health status
	curl http://localhost:8000/health
