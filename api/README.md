# API

FastAPI service, Python 3.12 or 3.13.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # editable install with test and dev extras
export DATABASE_URL=postgresql+psycopg://skincare:skincare@localhost:5432/skincare
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload
```

| Setting | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `rules` | `vertex` calls Gemini; `rules` uses the catalogue explainer only |
| `STORAGE_BACKEND` | `local` | `gcs` issues signed Cloud Storage upload URLs |
| `CORS_ORIGINS` | `http://localhost:3000` | comma-separated |
| `MAX_INGREDIENTS_PER_REQUEST` | `100` | larger lists get 413 |

Checks: `ruff format --check . && ruff check . && mypy app && pytest --cov=app`.
