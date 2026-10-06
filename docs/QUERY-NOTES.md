# Query notes

Measured on PostgreSQL 16.15 in a local development container, with the seed data loaded
(137 ingredients, 7 conflict rules) and `ANALYZE` run first. Timings are from single runs on that
machine and will differ elsewhere; the plan shapes are the point.

## Fuzzy ingredient match

The matcher's fallback query (from `app/parser.py`):

```sql
SELECT * FROM ingredients
WHERE name % 'niacinamid' AND similarity(name, 'niacinamid') >= 0.45
ORDER BY similarity(name, 'niacinamid') DESC
LIMIT 1;
```

The `%` operator is what lets PostgreSQL use the GIN trigram index `ix_ingredients_name_trgm`
(created in migration `0001_initial`). A plain `similarity(...) > x` filter alone cannot use it.

**At the real catalogue size (137 rows)** the planner correctly prefers a sequential scan, because the
whole table fits in one page:

```
Seq Scan on ingredients  (actual time=0.078..0.328 rows=1 loops=1)
  Filter: (((name)::text % 'niacinamid'::text) AND (similarity(...) >= '0.45'))
  Rows Removed by Filter: 136
Execution Time: 0.387 ms
```

With `SET enable_seqscan = off` the same query uses the index, which confirms the index matches the
query shape:

```
Bitmap Heap Scan on ingredients  (actual time=0.046..0.046 rows=1 loops=1)
  Recheck Cond: ((name)::text % 'niacinamid'::text)
  ->  Bitmap Index Scan on ix_ingredients_name_trgm  (actual time=0.031..0.031 rows=1 loops=1)
Execution Time: 0.133 ms
```

**At a larger catalogue size** the index matters. On a scratch table of 50,001 generated names
(catalogue names with random suffixes, plus `niacinamide`), dropped afterwards:

| | Plan | Execution time |
|---|---|---|
| No trigram index | Seq Scan, 50,000 rows removed by filter | 224.2 ms |
| With `gin (name gin_trgm_ops)` | Bitmap Index Scan | 0.165 ms |

## Routine items

`routine_items` has indexes on `routine_id` and `product_id` (migration `0001_initial`), and a unique
constraint on `(routine_id, product_id)`. With a handful of rows the planner uses a sequential scan:

```
Seq Scan on routine_items  (actual time=0.005..0.006 rows=2 loops=1)
  Filter: (routine_id = 1)
Execution Time: 0.036 ms
```

Routine pages load items, products and their ingredients with SQLAlchemy `selectinload`, which issues
one `IN (...)` query per relationship level instead of one query per product.

## Reproduce

```bash
docker compose up -d db
cd api && DATABASE_URL=postgresql+psycopg://skincare:skincare@localhost:5432/skincare \
  sh -c "alembic upgrade head && python -m app.seed"
psql postgresql://skincare:skincare@localhost:5432/skincare -c "ANALYZE" -c "EXPLAIN ANALYZE ..."
```
