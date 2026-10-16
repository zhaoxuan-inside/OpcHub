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
    - name: "dag_pipeline_configs"
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
