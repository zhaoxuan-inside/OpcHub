# 阶段 3 详细设计：数据库结构与 DDL 迁移契约 (Database Schema Spec)

- **模块**：`Storage & Data Architecture`
- **版本**：`v1.0.0`
- **阶段**：`Phase 3 (契约六元组)`
- **基线**：PostgreSQL 16+ / SQLAlchemy 2.0 / Alembic

---

## [VIBE_CONTRACT] 数据库结构与迁移契约 (Machine-Actionable Schema Contract)
```yaml
schema_contract:
  engine: "PostgreSQL >= 16.0"
  orm: "SQLAlchemy >= 2.0"
  naming_conventions:
    table: "snake_case_plural"
    column: "snake_case"
    timestamp: "*_at (TIMESTAMPTZ)"
    boolean: "is_* / has_*"
    json_payload: "JSONB with GIN index"
  
  core_tables:
    - name: "users"
      primary_key: "id (UUID)"
      business_key: "uid (VARCHAR(64), UNIQUE)"
    - name: "entitlements"
      primary_key: "id (VARCHAR(64))"
    - name: "user_entitlements"
      primary_key: "(user_id, entitlement_id)"
    - name: "policies"
      primary_key: "id (UUID)"
    - name: "perks"
      primary_key: "id (UUID)"
    - name: "demands"
      primary_key: "id (UUID)"
    - name: "sop_templates"
      primary_key: "id (VARCHAR(64))"
    - name: "sop_documents"
      primary_key: "id (UUID)"
    - name: "product_showcases"
      primary_key: "id (UUID)"
    - name: "demand_bids"
      primary_key: "id (UUID)"
    - name: "perk_claims"
      primary_key: "id (UUID)"
    - name: "dag_pipeline_configs"
      primary_key: "id (UUID)"
    - name: "forum_threads"
      primary_key: "id (UUID)"
    - name: "forum_comments"
      primary_key: "id (UUID)"
    - name: "forum_upvotes"
      primary_key: "id (UUID)"
    - name: "forum_bookmarks"
      primary_key: "id (UUID)"
```

---

## 1. 核心表结构 DDL 规范与 SQL 定义

### 1.1 创客用户表 (`users`)
```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uid VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'MAKER', -- 'ADMIN', 'MAKER', 'GUEST'
    company_name VARCHAR(255),
    unified_social_credit_code VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_uid ON users(uid);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_metadata_gin ON users USING GIN (metadata_payload);
```

### 1.2 权益字典与关联表 (`entitlements` / `user_entitlements`)
```sql
CREATE TABLE IF NOT EXISTS entitlements (
    id VARCHAR(64) PRIMARY KEY, -- e.g. 'ENT_VIP', 'ENT_POL_VIP', 'ENT_STRIPE_PERK'
    name VARCHAR(128) NOT NULL,
    description TEXT,
    annual_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_entitlements (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entitlement_id VARCHAR(64) NOT NULL REFERENCES entitlements(id) ON DELETE RESTRICT,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    PRIMARY KEY (user_id, entitlement_id)
);

CREATE INDEX idx_user_entitlements_lookup ON user_entitlements(user_id, status);
```

### 1.3 扶持政策表 (`policies`)
```sql
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    summary_plain TEXT NOT NULL, -- 大白话提炼
    region VARCHAR(64) NOT NULL DEFAULT 'CN_YANGTZE', -- 长三角/全国/地区
    max_subsidy_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    eligibility_rules JSONB NOT NULL DEFAULT '{}'::jsonb, -- 结构化规则
    source_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    published_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_policies_region ON policies(region);
CREATE INDEX idx_policies_rules_gin ON policies USING GIN (eligibility_rules);
```

### 1.4 算力与基础设施特权表 (`perks`)
```sql
CREATE TABLE IF NOT EXISTS perks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_name VARCHAR(128) NOT NULL,
    perk_type VARCHAR(64) NOT NULL, -- 'CLOUD_VOUCHER', 'API_ROUTE', 'OFFSHORE_PAY'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    nominal_value_usd NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    remaining_quota INT NOT NULL DEFAULT 50,
    total_quota INT NOT NULL DEFAULT 50,
    required_entitlement VARCHAR(64) REFERENCES entitlements(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 1.5 需求集市表 (`demands`)
```sql
CREATE TABLE IF NOT EXISTS demands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    budget_cny NUMERIC(12, 2) NOT NULL,
    category VARCHAR(64) NOT NULL,
    bidders_count INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'BIDDING', 'CLOSED'
    deadline_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_demands_status ON demands(status);
```

### 1.6 微内核 DAG 编排版本化配置表 (`dag_pipeline_configs`)
```sql
CREATE TABLE IF NOT EXISTS dag_pipeline_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_code VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL, -- 'v1.0.4-draft', 'v1.0.3-prod'
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'ACTIVE', 'ARCHIVED'
    topology_graph JSONB NOT NULL, -- 节点与边集合
    compiled_hash VARCHAR(64) NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (scenario_code, version)
);

CREATE INDEX idx_dag_configs_lookup ON dag_pipeline_configs(scenario_code, status);
```

### 1.7 创客论坛讨论帖表 (`forum_threads`)
```sql
CREATE TABLE IF NOT EXISTS forum_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_code VARCHAR(64) NOT NULL DEFAULT 'DEV', -- 'DEV', 'BIZ', 'TAX', 'AGENTS'
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    view_count INT NOT NULL DEFAULT 0,
    upvote_count INT NOT NULL DEFAULT 0,
    comment_count INT NOT NULL DEFAULT 0,
    bookmark_count INT NOT NULL DEFAULT 0,
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL DEFAULT 'PUBLISHED', -- 'PUBLISHED', 'ARCHIVED', 'DELETED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_forum_threads_cat_created ON forum_threads(category_code, created_at DESC);
CREATE INDEX idx_forum_threads_author ON forum_threads(author_id);
```

### 1.8 论坛多级问答回复表 (`forum_comments` · 物化路径模型)
```sql
CREATE TABLE IF NOT EXISTS forum_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    -- 物化路径与层级结构: 支持无限层级“回答以及对回答的回答”
    parent_id UUID REFERENCES forum_comments(id) ON DELETE CASCADE, -- NULL表示顶级回答
    root_id UUID REFERENCES forum_comments(id) ON DELETE CASCADE,   -- 属于哪一个顶级回答（便于楼中楼二级聚合）
    reply_to_user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- 被回复的创客UID
    materialized_path VARCHAR(1024) NOT NULL,                      -- 物化路径，如 "/root_id/parent_id/id"
    depth INT NOT NULL DEFAULT 0,                                  -- 嵌套深度，0为顶级回答，1为回答的回答
    upvote_count INT NOT NULL DEFAULT 0,
    is_accepted BOOLEAN NOT NULL DEFAULT FALSE,                    -- 问答场景采纳标识
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 单表极速索引：通过物化路径或 thread_id+path 一次索引扫描召回整个评论树
CREATE INDEX idx_forum_comments_thread_path ON forum_comments(thread_id, materialized_path);
CREATE INDEX idx_forum_comments_root_created ON forum_comments(root_id, created_at ASC);
CREATE INDEX idx_forum_comments_parent ON forum_comments(parent_id);
```

### 1.9 认同点赞表 (`forum_upvotes` · 防重唯一索引)
```sql
CREATE TABLE IF NOT EXISTS forum_upvotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(32) NOT NULL, -- 'THREAD' 或 'COMMENT'
    target_id UUID NOT NULL,          -- 对应的 thread_id 或 comment_id
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 严格防重：同一创客对同一帖子或评论只允许点赞一次
    CONSTRAINT uq_forum_upvote_target UNIQUE (user_id, target_type, target_id)
);

CREATE INDEX idx_forum_upvotes_user ON forum_upvotes(user_id);
CREATE INDEX idx_forum_upvotes_target ON forum_upvotes(target_type, target_id);
```

### 1.10 创客收藏归档表 (`forum_bookmarks` · 防重唯一索引)
```sql
CREATE TABLE IF NOT EXISTS forum_bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
    folder_name VARCHAR(64) NOT NULL DEFAULT '默认收藏夹',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 严格防重：同一创客对同一帖子只收藏一次
    CONSTRAINT uq_forum_bookmark UNIQUE (user_id, thread_id)
);

CREATE INDEX idx_forum_bookmarks_user ON forum_bookmarks(user_id, created_at DESC);
```

### 1.11 流程文书模板表 (`sop_templates`)
```sql
CREATE TABLE IF NOT EXISTS sop_templates (
    id VARCHAR(64) PRIMARY KEY, -- 'tpl_individual_biz_reg', 'tpl_opc_charter', 'tpl_soft_copyright'
    stage INT NOT NULL DEFAULT 1, -- 1: 主体定名与税种, 2: 银行与发票, 3: 软著申报, 4: 跨境结汇
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL, -- 'TAX', 'LEGAL', 'IP', 'FINANCE'
    description TEXT NOT NULL,
    template_content TEXT NOT NULL, -- 包含变量占位符的模板正文 (e.g. ${company_name})
    required_fields JSONB NOT NULL DEFAULT '[]'::jsonb, -- 必填字段定义元数据
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sop_templates_stage ON sop_templates(stage, is_active);
```

### 1.12 创客生成申报材料表 (`sop_documents`)
```sql
CREATE TABLE IF NOT EXISTS sop_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id VARCHAR(64) NOT NULL REFERENCES sop_templates(id),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_title VARCHAR(255) NOT NULL,
    form_data JSONB NOT NULL, -- 创客填报的关键业务字段 (company_name, founder_name, etc.)
    rendered_content TEXT NOT NULL, -- 后端微内核模板引擎渲染并持久化的完整申报材料
    status VARCHAR(32) NOT NULL DEFAULT 'READY', -- 'DRAFT', 'READY', 'SUBMITTED', 'ARCHIVED'
    compliance_passed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sop_documents_user ON sop_documents(user_id, created_at DESC);
CREATE INDEX idx_sop_documents_template ON sop_documents(template_id);
```

### 1.13 独立产品橱窗表 (`product_showcases`)
```sql
CREATE TABLE IF NOT EXISTS product_showcases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    tagline VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(64) NOT NULL DEFAULT 'AI', -- 'AI', 'SAAS', 'DEV', 'DEV_OPS'
    pricing_model VARCHAR(32) NOT NULL DEFAULT 'SUBSCRIPTION', -- 'FREE', 'ONE_TIME', 'SUBSCRIPTION'
    price_cny NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    demo_url VARCHAR(512),
    upvote_count INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'PUBLISHED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_showcases_category ON product_showcases(category, created_at DESC);
CREATE INDEX idx_product_showcases_author ON product_showcases(author_id);
```

### 1.14 需求竞标出价表 (`demand_bids`)
```sql
CREATE TABLE IF NOT EXISTS demand_bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id UUID NOT NULL REFERENCES demands(id) ON DELETE CASCADE,
    bidder_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bid_amount_cny NUMERIC(12, 2) NOT NULL,
    delivery_days INT NOT NULL,
    proposal_text TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED', -- 'SUBMITTED', 'ACCEPTED', 'REJECTED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_demand_bid UNIQUE (demand_id, bidder_id)
);

CREATE INDEX idx_demand_bids_demand ON demand_bids(demand_id);
CREATE INDEX idx_demand_bids_bidder ON demand_bids(bidder_id);
```

### 1.15 特权核销记录表 (`perk_claims`)
```sql
CREATE TABLE IF NOT EXISTS perk_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    perk_id UUID NOT NULL REFERENCES perks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voucher_code VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVATED', -- 'ACTIVATED', 'REDEEMED', 'EXPIRED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_perk_user_claim UNIQUE (perk_id, user_id)
);

CREATE INDEX idx_perk_claims_user ON perk_claims(user_id);
```


