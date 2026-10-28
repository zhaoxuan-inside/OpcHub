-- ============================================================================
-- OpcHub UUID identity migration (2026-10-28)
--
-- Goal: every database column named `id` or `*_id` is a real PostgreSQL UUID.
-- Human-readable identifiers are moved to non-ID columns:
--   users.uid                 -> users.handle
--   entitlements.id           -> entitlements.code + new UUID id
--   sop_templates.id          -> new UUID id (business `code` already exists)
--   domain_snapshots.entity_id-> domain_snapshots.entity_key + new UUID id
--   rag_vectors.doc_id        -> rag_vectors.doc_key + new UUID id
--   audit_logs.*              -> actor_uid / resource_key / trace_code
--   content_moderation_logs.* -> target_key / author_uid / moderator_uid
--
-- Run exactly once against an existing database. For a fresh database, use
-- schema_uuid.sql instead.
-- ============================================================================

BEGIN;

-- 0. Drop dependent FKs before changing referenced primary keys.
ALTER TABLE user_entitlements DROP CONSTRAINT IF EXISTS user_entitlements_entitlement_id_fkey;
ALTER TABLE perks DROP CONSTRAINT IF EXISTS perks_required_entitlement_fkey;
ALTER TABLE sop_documents DROP CONSTRAINT IF EXISTS sop_documents_template_id_fkey;

-- 1. Rename non-identity reference columns so no `*_id` remains non-UUID.
ALTER TABLE users RENAME COLUMN uid TO handle;

ALTER TABLE domain_snapshots RENAME COLUMN entity_id TO entity_key;
ALTER TABLE rag_vectors RENAME COLUMN doc_id TO doc_key;

ALTER TABLE content_moderation_logs RENAME COLUMN target_id TO target_key;
ALTER TABLE content_moderation_logs RENAME COLUMN author_id TO author_uid;
ALTER TABLE content_moderation_logs RENAME COLUMN moderator_id TO moderator_uid;

ALTER TABLE audit_logs RENAME COLUMN actor_id TO actor_uid;
ALTER TABLE audit_logs RENAME COLUMN resource_id TO resource_key;
ALTER TABLE audit_logs RENAME COLUMN trace_id TO trace_code;

ALTER TABLE audit_logs_archive RENAME COLUMN actor_id TO actor_uid;
ALTER TABLE audit_logs_archive RENAME COLUMN resource_id TO resource_key;
ALTER TABLE audit_logs_archive RENAME COLUMN trace_id TO trace_code;

-- 2. entitlements: old business id becomes code, new UUID primary key.
ALTER TABLE entitlements RENAME COLUMN id TO code;
ALTER TABLE entitlements ADD COLUMN id uuid;
UPDATE entitlements SET id = md5(code)::uuid WHERE id IS NULL;
ALTER TABLE entitlements ALTER COLUMN id SET NOT NULL;
ALTER TABLE entitlements DROP CONSTRAINT IF EXISTS entitlements_pkey;
ALTER TABLE entitlements ADD PRIMARY KEY (id);
ALTER TABLE entitlements ADD CONSTRAINT uq_entitlements_code UNIQUE (code);

-- 3. user_entitlements.entitlement_id -> UUID FK.
ALTER TABLE user_entitlements DROP CONSTRAINT IF EXISTS user_entitlements_pkey;
ALTER TABLE user_entitlements ADD COLUMN entitlement_id_uuid uuid;
UPDATE user_entitlements ue
SET entitlement_id_uuid = e.id
FROM entitlements e
WHERE e.code = ue.entitlement_id;
ALTER TABLE user_entitlements DROP COLUMN entitlement_id;
ALTER TABLE user_entitlements RENAME COLUMN entitlement_id_uuid TO entitlement_id;
ALTER TABLE user_entitlements ALTER COLUMN entitlement_id SET NOT NULL;
ALTER TABLE user_entitlements ADD PRIMARY KEY (user_id, entitlement_id);
ALTER TABLE user_entitlements
  ADD CONSTRAINT user_entitlements_entitlement_id_fkey
  FOREIGN KEY (entitlement_id) REFERENCES entitlements(id) ON DELETE RESTRICT;

-- 4. perks.required_entitlement -> UUID FK + human-readable code.
ALTER TABLE perks RENAME COLUMN required_entitlement TO required_entitlement_code;
ALTER TABLE perks ADD COLUMN required_entitlement_id uuid;
UPDATE perks p
SET required_entitlement_id = e.id
FROM entitlements e
WHERE e.code = p.required_entitlement_code;
ALTER TABLE perks
  ADD CONSTRAINT perks_required_entitlement_fkey
  FOREIGN KEY (required_entitlement_id) REFERENCES entitlements(id);

-- 5. sop_templates: replace business id with UUID primary key.
ALTER TABLE sop_templates ADD COLUMN id_uuid uuid;
UPDATE sop_templates SET id_uuid = md5(id)::uuid WHERE id_uuid IS NULL;
ALTER TABLE sop_templates DROP CONSTRAINT IF EXISTS sop_templates_pkey;
ALTER TABLE sop_templates DROP COLUMN id;
ALTER TABLE sop_templates RENAME COLUMN id_uuid TO id;
ALTER TABLE sop_templates ALTER COLUMN id SET NOT NULL;
ALTER TABLE sop_templates ADD PRIMARY KEY (id);

-- 6. sop_documents.template_id -> UUID FK (same md5 mapping as the template id).
ALTER TABLE sop_documents ADD COLUMN template_id_uuid uuid;
UPDATE sop_documents SET template_id_uuid = md5(template_id)::uuid WHERE template_id_uuid IS NULL;
ALTER TABLE sop_documents DROP COLUMN template_id;
ALTER TABLE sop_documents RENAME COLUMN template_id_uuid TO template_id;
ALTER TABLE sop_documents ALTER COLUMN template_id SET NOT NULL;
ALTER TABLE sop_documents
  ADD CONSTRAINT sop_documents_template_id_fkey
  FOREIGN KEY (template_id) REFERENCES sop_templates(id);

-- 7. domain_snapshots: UUID surrogate key, business entity key retained.
ALTER TABLE domain_snapshots ADD COLUMN id uuid;
UPDATE domain_snapshots SET id = gen_random_uuid() WHERE id IS NULL;
ALTER TABLE domain_snapshots ALTER COLUMN id SET NOT NULL;
ALTER TABLE domain_snapshots DROP CONSTRAINT IF EXISTS domain_snapshots_pkey;
ALTER TABLE domain_snapshots ADD PRIMARY KEY (id);
ALTER TABLE domain_snapshots
  ADD CONSTRAINT uq_domain_snapshot_entity UNIQUE (domain, entity_key);

-- 8. rag_vectors: UUID surrogate key, caller document key retained.
ALTER TABLE rag_vectors ADD COLUMN id uuid;
UPDATE rag_vectors SET id = gen_random_uuid() WHERE id IS NULL;
ALTER TABLE rag_vectors ALTER COLUMN id SET NOT NULL;
ALTER TABLE rag_vectors DROP CONSTRAINT IF EXISTS rag_vectors_pkey;
ALTER TABLE rag_vectors ADD PRIMARY KEY (id);
ALTER TABLE rag_vectors
  ADD CONSTRAINT uq_rag_collection_doc UNIQUE (collection, doc_key);

-- 9. Give every UUID `id` column a database-side default, so raw inserts and
--    future tables never depend on the application to supply an identity.
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND column_name = 'id'
      AND data_type = 'uuid'
  LOOP
    EXECUTE format(
      'ALTER TABLE %I ALTER COLUMN %I SET DEFAULT gen_random_uuid()',
      r.table_name, r.column_name
    );
  END LOOP;
END $$;

COMMIT;
