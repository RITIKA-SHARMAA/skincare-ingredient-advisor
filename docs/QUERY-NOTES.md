# Query notes

No EXPLAIN ANALYZE measurements are claimed in this repository because Docker/PostgreSQL was not available in the build environment used to create it.

Run these locally against PostgreSQL after loading the seed data and record the actual output here:

```sql
EXPLAIN ANALYZE SELECT * FROM ingredients WHERE name ILIKE '%niacin%';
EXPLAIN ANALYZE SELECT r.id, r.name FROM routines r JOIN routine_items ri ON ri.routine_id=r.id WHERE r.id=1;
```

The `pg_trgm` GIN index is created by the initial migration for substring/name matching.
