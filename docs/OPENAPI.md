# Typed API client

FastAPI publishes the source schema at `/openapi.json`. The web app keeps its request/response types in `web/lib/api.ts` so the UI has compile-time contracts without hand-written URL strings in components.

For a generated client in a connected development environment, install `openapi-typescript` and generate from the running API schema, then replace the mirrored types with the generated definitions.
