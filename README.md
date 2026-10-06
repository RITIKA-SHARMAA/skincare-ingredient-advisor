# Skincare Ingredient Advisor

[![CI](https://github.com/RITIKA-SHARMAA/skincare-ingredient-advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/RITIKA-SHARMAA/skincare-ingredient-advisor/actions/workflows/ci.yml)

Paste a product's ingredient list, or upload a photo of the label, and get a plain-language
explanation of each ingredient, irritant flags for your skin type, and warnings when products in
your routine clash.

**Stack:** Next.js 15 (App Router, TypeScript, Tailwind) · FastAPI · PostgreSQL 16 with `pg_trgm` ·
Gemini on Vertex AI · Cloud Run, Cloud SQL, Cloud Storage, Secret Manager · Terraform ·
GitHub Actions with Workload Identity Federation.

> The ingredient catalogue, irritant levels and conflict rules are illustrative. This is a
> portfolio project, not medical or dermatological advice.

## How it works

```mermaid
flowchart LR
  Browser -->|paste list| Web[Next.js]
  Browser -->|PUT photo, signed URL| GCS[(Cloud Storage)]
  Web --> API[FastAPI]
  API --> Parser[Parser + matcher]
  Parser --> PG[(PostgreSQL + pg_trgm)]
  API --> Explain{Explainer}
  Explain -->|LLM_PROVIDER=vertex| Gemini[Gemini on Vertex AI]
  Explain -->|rules, or Gemini output rejected| Rules[Catalogue rules]
  API --> GCS
```

1. **Parse.** The list is split on commas, semicolons, bullets and newlines, then normalised
   (case, punctuation, `(CI 77891)`-style annotations).
2. **Match.** Each name is matched to the catalogue by exact name, then by alias (`aqua` → water),
   then by trigram similarity using the `pg_trgm` index (`niacinamid` → niacinamide, minimum
   similarity 0.45). Anything still unmatched is returned with its position, never dropped.
3. **Explain.** With `LLM_PROVIDER=vertex`, Gemini receives only the catalogue facts for the matched
   ingredients and must return a JSON array. The output is rejected if it is not valid JSON, fails the
   Pydantic schema, or names a different set of ingredients than was sent (an invented, missing or
   duplicated ingredient). A rejected answer is retried once; a second failure falls back to the
   rule-based explainer and the result is marked `ai_status: "fallback"`.
4. **Routines.** Products saved to a routine are compared pairwise within the same slot (morning or
   evening) against rules stored in the `conflict_rules` table, for example an acid exfoliant with a
   retinoid. The most severe matching rule is reported per pair.
5. **Label photos.** The browser asks the API for a signed Cloud Storage `PUT` URL, uploads the
   image directly to the bucket, then asks the API to read it. Gemini extracts the ingredient text,
   which then goes through the same pipeline. Locally the "signed URL" points at the API itself.

## Run it locally

Requirements: Docker with Compose.

```bash
make up            # copies .env.example to .env, then docker compose up --build
```

Open http://localhost:3000. API docs (OpenAPI) are at http://localhost:8000/docs.

The default `LLM_PROVIDER=rules` needs no GCP account. To use Gemini locally, run
`gcloud auth application-default login`, then set `LLM_PROVIDER=vertex` and
`GOOGLE_CLOUD_PROJECT` in `.env`. Label photo reading only works with the Vertex provider.

## Tests

| Suite | What it covers | Result on the last local run |
|---|---|---|
| API, pytest against real PostgreSQL | parser, alias and trigram matching, LLM output validation, retry and fallback, products, routines, conflicts, label upload and extraction, error documents | 50 passed, 89% line coverage |
| Web, Vitest + React Testing Library | API client and problem-detail errors, analyse form validation and errors, label upload, analysis view, routine page | 20 passed |
| End to end, Playwright + axe | paste → analyse → save two products → routine → conflict shown; validation; WCAG 2 A/AA scan on three pages, desktop and mobile viewports | 4 passed |

Tests never call Vertex AI: the LLM is replaced by a scripted fake that can return valid JSON,
invalid JSON, invented ingredients or errors.

```bash
# API: point at any PostgreSQL 16 database, or leave unset to start one with Testcontainers
cd api && TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/test pytest --cov=app
cd web && npm test
cd web && DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/dev npm run e2e
```

CI runs all three suites, lint (ruff, ESLint, Prettier), type checks (mypy strict, `tsc`) and both
Docker image builds on every push and pull request.

## Deploying to GCP

`infra/` holds Terraform for everything the app needs: Artifact Registry, Cloud SQL for PostgreSQL 16
(smallest tier), a private label bucket with CORS and a one-day lifecycle rule, Secret Manager for the
database URL, one service account per service with only the roles it uses, two Cloud Run services,
a Cloud Run job for migrations, a budget alert, and Workload Identity Federation so GitHub Actions
deploys without a service-account key. See [infra/README.md](infra/README.md).

The `Deploy to Cloud Run` workflow is manual (`workflow_dispatch`). It builds both images, runs the
migration job, then deploys both services.

**Status:** this project has not been deployed. The Terraform has not been applied and the GCP code
paths (signed Cloud Storage URLs and Vertex AI calls) have only been exercised through test fakes.

## Query notes

Indexes and measured query plans are in [docs/QUERY-NOTES.md](docs/QUERY-NOTES.md). Architecture
and trade-offs are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Known limits

- The catalogue has about 140 common cosmetic ingredients with hand-assigned, illustrative irritant
  levels. It is not a dermatological database.
- There are no user accounts; products and routines are shared by everyone using one deployment.
- Conflict detection compares ingredient functions, not concentrations or formulation.
- Fuzzy matching can still pick a wrong ingredient for unusual names; results show the match type so
  it is visible.
