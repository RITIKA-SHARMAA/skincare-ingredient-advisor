# Architecture

## Components

| Part | Where | Responsibility |
|---|---|---|
| `web/` | Next.js 15 on Cloud Run | Pages, forms, label upload. Server components fetch from the API through `API_INTERNAL_BASE_URL`; the browser uses `NEXT_PUBLIC_API_BASE_URL`. |
| `api/app/main.py` | FastAPI on Cloud Run | HTTP layer, RFC 7807 errors, request IDs, dependency injection of the database, LLM and storage. |
| `api/app/parser.py` | API | Splitting, normalisation, exact / alias / trigram matching. |
| `api/app/analysis.py` | API | The analysis pipeline: match, explain, validate, retry, fall back, persist. |
| `api/app/llm.py` | API | `LLMClient` protocol, Gemini implementation, output validation, rule-based explainer. |
| `api/app/storage.py`, `gcp.py` | API | Label storage: local directory in development, signed Cloud Storage URLs in GCP. |
| `api/app/conflicts.py` | API | Same-slot pairwise conflict detection against `conflict_rules`. |
| PostgreSQL 16 | Cloud SQL | Catalogue, conflict rules, products, routines, analyses. |

## Data model

- `ingredients`: name (unique, GIN trigram index), pipe-separated aliases, function, irritant level
  0 to 5 (check constraint).
- `conflict_rules`: a pair of ingredient functions, severity (`low`, `medium`, `high`), reason.
  Unique per pair. Adding a rule is a data change, not a code change.
- `products` ↔ `ingredients` through `product_ingredients`, which keeps each ingredient's position in
  the original list (unique per product).
- `routines` → `routine_items`, each pointing at a product with a `morning` / `evening` slot
  (check constraint, one row per product per routine).
- `analyses`: the request and the full JSON result, so a result page can be reloaded by id.

Migrations are Alembic (`api/alembic/versions`). Seed data is loaded from `api/data/*.csv` and is
idempotent.

## Why the LLM output is validated, not trusted

Gemini is asked for one object per supplied ingredient. Even with a JSON response type, models can
return extra ingredients, skip one, or produce invalid values. `parse_explanations` therefore checks
three things before anything reaches the user: the text parses as JSON, every object passes the
Pydantic schema (including the `morning` / `evening` slot and a non-empty explanation), and the set of
returned names equals the set sent. One retry handles transient problems; after that the rule-based
explainer answers and `ai_status` says so. The catalogue facts (function, irritant level) always come
from the database, never from the model.

## Trade-offs

- **Cloud Run** keeps both services stateless and scale-to-zero, which suits a demo. Cold starts are
  the cost.
- **Cloud SQL over the connector socket** avoids exposing the database to any network; the public IP
  has no authorised networks.
- **Signed upload URLs** keep image bytes off the API on Cloud Run. Signing uses IAM `signBlob`, so the
  API service account needs Token Creator on itself.
- **Trigram matching** is cheap and needs no extra service, but it is lexical: it fixes typos, not
  synonyms. Synonyms are aliases in the catalogue.
- **No authentication** keeps the demo simple; routines are shared per deployment.
