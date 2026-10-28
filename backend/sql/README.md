# OpcHub PostgreSQL UUID identity DDL

## Contract

Every database column whose name is `id` or ends with `_id` is a PostgreSQL `uuid`.

Human-readable identifiers are deliberately **not** identity columns:

| Human identifier | Column |
|---|---|
| User account handle | `users.handle` |
| Entitlement catalog code | `entitlements.code` |
| SOP template code | `sop_templates.code` |
| Domain aggregate key | `domain_snapshots.entity_key` |
| RAG document key | `rag_vectors.doc_key` |
| Audit actor handle | `audit_logs.actor_uid` |
| Audit resource key | `audit_logs.resource_key` |
| Audit trace code | `audit_logs.trace_code` |
| Moderation target key | `content_moderation_logs.target_key` |
| Moderation author/moderator handle | `content_moderation_logs.author_uid`, `moderator_uid` |

The API-facing business keys (e.g. `pol_...`, `perk_...`, `tpl_...`) are preserved in
domain payloads as `code` / `key` values; the database identity is always UUID.

## Fresh database

```bash
psql "$DATABASE_URL" -f backend/sql/schema_uuid.sql
```

`schema_uuid.sql` is generated from the SQLAlchemy metadata and contains all 21
tables, indexes and constraints.

## Existing database

Back up first:

```bash
pg_dump "$DATABASE_URL" > opchub_before_uuid.sql
```

Then run the one-time migration:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/sql/migrate_uuid_ids_20261028.sql
```

The migration:

1. Renames `users.uid` → `users.handle`, and all audit/moderation `*_id` reference
   columns to `*_key` / `*_uid` / `*_code`.
2. Converts `entitlements.id` and `sop_templates.id` to UUID, keeping business codes
   in `code`, and remaps their foreign keys.
3. Adds UUID surrogate keys to `domain_snapshots` and `rag_vectors` while keeping
   `entity_key` / `doc_key`.
4. Gives every UUID `id` a `gen_random_uuid()` database default.

## Verification

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (column_name = 'id' OR column_name LIKE '%\_id')
  AND data_type <> 'uuid';
-- expected: 0 rows
```

A pytest contract test (`test_every_id_column_is_uuid`) enforces the same rule at
the SQLAlchemy metadata level.
