-- OpcHub canonical PostgreSQL DDL (UUID identity edition)
-- Generated from SQLAlchemy metadata. Every column named id / *_id is UUID.
-- Human-readable business identifiers live in code / key / handle columns.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS audit_logs (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	actor_uid VARCHAR(64) NOT NULL, 
	actor_role VARCHAR(32) NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	resource_type VARCHAR(64) NOT NULL, 
	resource_key VARCHAR(64) NOT NULL, 
	permission VARCHAR(64) NOT NULL, 
	result VARCHAR(16) NOT NULL, 
	ip_address VARCHAR(64) NOT NULL, 
	trace_code VARCHAR(64) NOT NULL, 
	detail_encrypted TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_uid ON audit_logs (actor_uid);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_key ON audit_logs (resource_key);
CREATE INDEX IF NOT EXISTS ix_audit_logs_result ON audit_logs (result);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);

CREATE TABLE IF NOT EXISTS audit_logs_archive (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	actor_uid VARCHAR(64) NOT NULL, 
	actor_role VARCHAR(32) NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	resource_type VARCHAR(64) NOT NULL, 
	resource_key VARCHAR(64) NOT NULL, 
	permission VARCHAR(64) NOT NULL, 
	result VARCHAR(16) NOT NULL, 
	ip_address VARCHAR(64) NOT NULL, 
	trace_code VARCHAR(64) NOT NULL, 
	detail_encrypted TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	archived_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_archive_action ON audit_logs_archive (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_archive_actor_uid ON audit_logs_archive (actor_uid);
CREATE INDEX IF NOT EXISTS ix_audit_logs_archive_created_at ON audit_logs_archive (created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_archive_resource_key ON audit_logs_archive (resource_key);

CREATE TABLE IF NOT EXISTS content_moderation_logs (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	target_type VARCHAR(32) NOT NULL, 
	target_key VARCHAR(64) NOT NULL, 
	author_uid VARCHAR(64) NOT NULL, 
	violation_type VARCHAR(64) NOT NULL, 
	snippet_content TEXT NOT NULL, 
	action_type VARCHAR(32) NOT NULL, 
	reason VARCHAR(255) NOT NULL, 
	moderator_uid VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_content_moderation_logs_author_uid ON content_moderation_logs (author_uid);
CREATE INDEX IF NOT EXISTS ix_content_moderation_logs_target_type ON content_moderation_logs (target_type);
CREATE INDEX IF NOT EXISTS ix_content_moderation_logs_target_key ON content_moderation_logs (target_key);

CREATE TABLE IF NOT EXISTS domain_snapshots (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	domain VARCHAR(64) NOT NULL, 
	entity_key VARCHAR(160) NOT NULL, 
	payload JSONB NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_domain_snapshot_entity UNIQUE (domain, entity_key)
);

CREATE INDEX IF NOT EXISTS ix_domain_snapshots_domain ON domain_snapshots (domain);

CREATE TABLE IF NOT EXISTS entitlements (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	description TEXT, 
	annual_price NUMERIC(10, 2) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_entitlements_code ON entitlements (code);

CREATE TABLE IF NOT EXISTS policies (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	summary_plain TEXT NOT NULL, 
	region VARCHAR(64) NOT NULL, 
	max_subsidy_amount NUMERIC(12, 2) NOT NULL, 
	eligibility_rules JSONB NOT NULL, 
	source_url TEXT, 
	is_active BOOLEAN NOT NULL, 
	embedding VECTOR(128), 
	published_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_policies_code ON policies (code);
CREATE INDEX IF NOT EXISTS ix_policies_region ON policies (region);

CREATE TABLE IF NOT EXISTS rag_vectors (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	collection VARCHAR(128) NOT NULL, 
	doc_key VARCHAR(128) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	content TEXT NOT NULL, 
	metadata_payload JSONB NOT NULL, 
	embedding VECTOR(128), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rag_collection_doc UNIQUE (collection, doc_key)
);


CREATE TABLE IF NOT EXISTS sop_templates (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	stage INTEGER NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	category VARCHAR(64) NOT NULL, 
	description TEXT NOT NULL, 
	template_content TEXT NOT NULL, 
	required_fields JSONB NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE INDEX IF NOT EXISTS ix_sop_templates_stage ON sop_templates (stage);

CREATE TABLE IF NOT EXISTS users (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	handle VARCHAR(64) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	nickname VARCHAR(100) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	company_name VARCHAR(255), 
	unified_social_credit_code VARCHAR(64), 
	password_hash VARCHAR(255), 
	is_active BOOLEAN NOT NULL, 
	metadata_payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_handle ON users (handle);

CREATE TABLE IF NOT EXISTS dag_pipeline_configs (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	scenario_code VARCHAR(128) NOT NULL, 
	version VARCHAR(32) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	topology_graph JSONB NOT NULL, 
	compiled_hash VARCHAR(64) NOT NULL, 
	created_by UUID, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_scenario_version UNIQUE (scenario_code, version), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_dag_pipeline_configs_scenario_code ON dag_pipeline_configs (scenario_code);

CREATE TABLE IF NOT EXISTS demands (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	creator_id UUID NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	budget_cny NUMERIC(12, 2) NOT NULL, 
	category VARCHAR(64) NOT NULL, 
	bidders_count INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	deadline_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(creator_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_demands_status ON demands (status);

CREATE TABLE IF NOT EXISTS forum_threads (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	category_code VARCHAR(64) NOT NULL, 
	author_id UUID NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	content TEXT NOT NULL, 
	embedding VECTOR(128), 
	view_count INTEGER NOT NULL, 
	upvote_count INTEGER NOT NULL, 
	comment_count INTEGER NOT NULL, 
	bookmark_count INTEGER NOT NULL, 
	is_pinned BOOLEAN NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_forum_threads_author_id ON forum_threads (author_id);
CREATE INDEX IF NOT EXISTS ix_forum_threads_category_code ON forum_threads (category_code);

CREATE TABLE IF NOT EXISTS forum_upvotes (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	user_id UUID NOT NULL, 
	target_type VARCHAR(32) NOT NULL, 
	target_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_forum_upvote_target UNIQUE (user_id, target_type, target_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_forum_upvotes_target_id ON forum_upvotes (target_id);
CREATE INDEX IF NOT EXISTS ix_forum_upvotes_user_id ON forum_upvotes (user_id);

CREATE TABLE IF NOT EXISTS perks (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	partner_name VARCHAR(128) NOT NULL, 
	perk_type VARCHAR(64) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	nominal_value_usd NUMERIC(10, 2) NOT NULL, 
	remaining_quota INTEGER NOT NULL, 
	total_quota INTEGER NOT NULL, 
	required_entitlement_id UUID, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(required_entitlement_id) REFERENCES entitlements (id)
);


CREATE TABLE IF NOT EXISTS product_showcases (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	author_id UUID NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	tagline VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(64) NOT NULL, 
	pricing_model VARCHAR(32) NOT NULL, 
	price_cny NUMERIC(10, 2) NOT NULL, 
	demo_url VARCHAR(512), 
	icon_url VARCHAR(512), 
	version VARCHAR(64), 
	official_url VARCHAR(512), 
	download_url VARCHAR(512), 
	author_name VARCHAR(128), 
	screenshots JSONB, 
	upvote_count INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_product_showcases_category ON product_showcases (category);
CREATE INDEX IF NOT EXISTS ix_product_showcases_author_id ON product_showcases (author_id);

CREATE TABLE IF NOT EXISTS sop_documents (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	template_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	document_title VARCHAR(255) NOT NULL, 
	form_data JSONB NOT NULL, 
	rendered_content TEXT NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	compliance_passed BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(template_id) REFERENCES sop_templates (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_sop_documents_template_id ON sop_documents (template_id);
CREATE INDEX IF NOT EXISTS ix_sop_documents_user_id ON sop_documents (user_id);

CREATE TABLE IF NOT EXISTS user_entitlements (
	user_id UUID NOT NULL, 
	entitlement_id UUID NOT NULL, 
	activated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	status VARCHAR(32) NOT NULL, 
	PRIMARY KEY (user_id, entitlement_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(entitlement_id) REFERENCES entitlements (id) ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS demand_bids (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	demand_id UUID NOT NULL, 
	bidder_id UUID NOT NULL, 
	bid_amount_cny NUMERIC(12, 2) NOT NULL, 
	delivery_days INTEGER NOT NULL, 
	proposal_text TEXT NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_demand_bid UNIQUE (demand_id, bidder_id), 
	FOREIGN KEY(demand_id) REFERENCES demands (id) ON DELETE CASCADE, 
	FOREIGN KEY(bidder_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_demand_bids_demand_id ON demand_bids (demand_id);
CREATE INDEX IF NOT EXISTS ix_demand_bids_bidder_id ON demand_bids (bidder_id);

CREATE TABLE IF NOT EXISTS forum_bookmarks (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	user_id UUID NOT NULL, 
	thread_id UUID NOT NULL, 
	folder_name VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_forum_bookmark UNIQUE (user_id, thread_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(thread_id) REFERENCES forum_threads (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_forum_bookmarks_thread_id ON forum_bookmarks (thread_id);
CREATE INDEX IF NOT EXISTS ix_forum_bookmarks_user_id ON forum_bookmarks (user_id);

CREATE TABLE IF NOT EXISTS forum_comments (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	thread_id UUID NOT NULL, 
	author_id UUID NOT NULL, 
	content TEXT NOT NULL, 
	parent_id UUID, 
	root_id UUID, 
	reply_to_user_id UUID, 
	materialized_path VARCHAR(1024) NOT NULL, 
	depth INTEGER NOT NULL, 
	upvote_count INTEGER NOT NULL, 
	is_accepted BOOLEAN NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(thread_id) REFERENCES forum_threads (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(parent_id) REFERENCES forum_comments (id) ON DELETE CASCADE, 
	FOREIGN KEY(root_id) REFERENCES forum_comments (id) ON DELETE CASCADE, 
	FOREIGN KEY(reply_to_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_forum_comments_materialized_path ON forum_comments (materialized_path);
CREATE INDEX IF NOT EXISTS ix_forum_comments_thread_id ON forum_comments (thread_id);
CREATE INDEX IF NOT EXISTS ix_forum_comments_author_id ON forum_comments (author_id);

CREATE TABLE IF NOT EXISTS perk_claims (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	perk_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	voucher_code VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_perk_user_claim UNIQUE (perk_id, user_id), 
	FOREIGN KEY(perk_id) REFERENCES perks (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (voucher_code)
);

CREATE INDEX IF NOT EXISTS ix_perk_claims_user_id ON perk_claims (user_id);
