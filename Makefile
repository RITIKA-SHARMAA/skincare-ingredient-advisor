.PHONY: up down api-test web-test lint format
up:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build

down:
	docker compose down -v

api-test:
	cd api && pytest -q

web-test:
	cd web && npm test -- --run

lint:
	cd api && ruff check . && mypy app
	cd web && npm run lint && npm run typecheck

format:
	cd api && ruff format .
	cd web && npm run format
