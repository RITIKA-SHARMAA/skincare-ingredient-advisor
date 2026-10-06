.PHONY: up down api-test web-test e2e lint format check

up:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build

down:
	docker compose down -v

# Needs TEST_DATABASE_URL, or Docker for Testcontainers.
api-test:
	cd api && pytest --cov=app

web-test:
	cd web && npm test

# Needs DATABASE_URL pointing at a PostgreSQL database the API can migrate.
e2e:
	cd web && npm run e2e

lint:
	cd api && ruff format --check . && ruff check . && mypy app
	cd web && npm run format:check && npm run lint && npm run typecheck

format:
	cd api && ruff format . && ruff check --fix .
	cd web && npm run format

check: lint api-test web-test
