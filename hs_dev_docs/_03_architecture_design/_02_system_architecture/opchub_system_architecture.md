# OpcHub 系统架构设计规范说明书 (System Architecture Design)

> **Document Type**: Phase 2 System Architecture & Domain Blueprint  
> **Metadata**: `intent=BUILD`, `phase=2`, `status=PROPOSED`, `version=v1.0.0`  
> **Inherits**: `/DESIGN.md`, `hs_dev_docs/_03_architecture_design/_01_tech_selection/tech_selection_plan.md`  
> **Core Feature**: 元数据驱动的低代码前后端兼容框架（应对信息高频变动与多源多格式接入）

---

## [VIBE_CONTRACT] 架构执行契约 (Machine-Actionable Architecture)
```yaml
architecture_contract:
  system_name: "OpcHub"
  paradigm:
    backend_tier: "B2_Modular_Monolith_With_Metadata_Engine"
    frontend_tier: "F2_Feature_Driven_With_Dynamic_Schema_Renderer"
  
  directory_structure:
    backend_root: "backend/src"
    backend_modules:
      core_engine: "backend/src/core"             # 配置、安全、异常、底座
      metadata_engine: "backend/src/metadata"     # 低代码元数据与动态 Schema 引擎
      domains:
        policy: "backend/src/domains/policy"       # 政策中心与补贴计算
        perk: "backend/src/domains/perk"           # 算力与基础设施装备包
        gallery: "backend/src/domains/gallery"     # 产品展示橱窗与打榜
        marketplace: "backend/src/domains/market"  # 需求集市与服务撮合
        sop: "backend/src/domains/sop"             # 全生命周期流程向导
        forum: "backend/src/domains/forum"         # 创客社区与复盘
    frontend_root: "frontend/src"
    frontend_modules:
      schema_engine: "frontend/src/core/schema"   # 低代码动态表单/卡片渲染引擎
      features: "frontend/src/features"           # 业务特性组件

dependency_rules:
  - "RULE: 实体核心不变属性（ID, Code, Status, CreatedAt）严格走强类型 ORM，多变扩展业务属性统一收敛进 JSONB 载荷并由 Schema 引擎校验"
  - "RULE: 模块间禁止跨库越权直接篡改数据，统一经由模块 Service 契约或领域事件流转"
  - "RULE: 前端组件必须解耦，所有卡片展示、表单录入、列表筛选器均由后端吐出的 Schema 动态驱动，严禁将多变业务字段硬编码写死在 Vue 模板中"
```

---

## 0. 范式选型与权衡 (Paradigm Selection)

| 维度 | 架构设定 | 决策理由与权衡依据 |
| :--- | :--- | :--- |
| **产品规模** | 小型团队 / 独立全栈（1人~小队） | 严禁过度微服务化，避免分布式 RPC 与运维死锁 |
| **后端范式** | **B2：模块化单体 + 元数据引擎** | 业务高频演进、信息多变，通过内部清晰包隔离结合动态 Schema，单进程运行但未来可随时剥离 |
| **前端范式** | **F2：Feature 驱动 + 动态 Schema 渲染器** | 保持“薄前端”敏捷性，卡片与表单全部支持组件化插拔，新增字段免改前端代码秒级上线 |
| **为何不选微服务** | 现阶段团队属于一人公司/小团队，微服务网络开销与运维复杂度将吞噬业务开发精力 |
| **为何不选纯 CRUD** | 政策、Perks、橱窗等信息格式极度异构，传统硬编码表结构会导致频繁 `ALTER TABLE`，极易引发迁移事故 |

---

## 1. 系统上下文与边界设计 (System Context & Boundaries) [ARCH-01]

```mermaid
graph TD
    User["OPC 创客 / 独立开发者"]
    Vendor["生态服务商 (财税所/外包)"]
    Partner["B端算力厂商 (SiliconFlow/云厂商)"]
    GovAPI["政府公开政务数据网 / 资讯爬虫源"]

    subgraph OpcHub_Boundary["OpcHub 平台核心边界"]
        Gateway["FastAPI API-First 统一网关"]
        SchemaCore["元数据驱动引擎 (Schema Engine)"]
        DomainServices["六大业务模块 (Policy, Perk, Gallery, Market, SOP, Forum)"]
        SearchHub["多维搜索与语义匹配中枢 (ES + pgvector)"]
        MainDB["PostgreSQL 16+ 主库 (ACID + JSONB)"]
    end

    User -->|HTTPS / RESTful API| Gateway
    Vendor -->|入驻认证 / 申请对接| Gateway
    GovAPI -.->|定期采集 ETL / LLM 提炼| DomainServices
    Partner -.->|API 返佣回调 / 专属 Deals 验证| DomainServices

    Gateway --> SchemaCore
    Gateway --> DomainServices
    DomainServices --> SearchHub
    DomainServices --> MainDB
```

- **系统职责边界**：
  - **在职责内**：政策智能提炼清洗、补贴精准测算、算力优惠直通返佣、产品橱窗展示打榜、外包需求与认证服务商轻量撮合、SOP向导；
  - **在职责外 (明确不承担)**：不承担任何线下实体孵化、不自研重型 ERP 代账系统、不托管大额外包资金资金池（无二清合规风险）。

---

## 2. 核心领域与数据所有权划分 (Bounded Contexts) [ARCH-02]

平台将高内聚业务严格切分为六大领域上下文，每个上下文拥有明确的数据所有权：

| 领域上下文 | 英文标识 | 核心聚合根 (Aggregate Root) | 负责职责与数据所有权 |
| :--- | :--- | :--- | :--- |
| **政策中心域** | `PolicyContext` | `PolicyItem` (政策条目) | 负责政策全文解析、多维度标签、白话提炼、补贴测算算法。拥有政策主表与向量表写入权。 |
| **算力装备域** | `PerkContext` | `PerkItem` (装备包权益) | 负责厂商折扣、专属优惠码、返佣外链转化埋点跟踪 (`PerkClickLog`)。 |
| **产品橱窗域** | `GalleryContext` | `GalleryProduct` (橱窗产品) | 负责创客独立产品提交、付费审核状态机、Upvote 点赞计数、打榜排序。 |
| **需求集市域** | `MarketContext` | `ServiceDemand` / `Vendor` | 负责外包需求发布、服务商资质认证、线索安全交换与撮合记录。 |
| **向导追踪域** | `SOPContext` | `SOPPlan` / `SOPProgress` | 负责 6 阶段标准任务树模板维护及创客进度持久化。 |
| **基础设施域** | `MetaContext` | `SchemaDefinition` (动态元数据) | **核心基石**：负责所有动态 Schema、字段约束、表单布局、卡片视图元数据版本化管理。 |

---

## 3. 核心突破：元数据驱动与低代码底层框架设计 (Low-Code Schema Engine)

为了解决**“信息变动大、格式多变、政策/福利结构各异”**的问题，前后端设计一套统一的**低代码元数据引擎**：

```mermaid
sequenceDiagram
    participant Admin as 平台运营 / AI爬虫
    participant MetaDB as 元数据引擎 (Schema Registry)
    participant CoreAPI as 业务 API (FastAPI)
    participant VueClient as 薄前端渲染引擎 (Vue 3)

    Admin->>MetaDB: 1. 发布/热更新 PolicyCardSchema (v1.2)<br/>新增字段: "申报绿色通道URL", "退税计算器参数"
    Note over MetaDB: 零数据库 DDL 改动，仅存入 JSON Schema 元数据
    VueClient->>CoreAPI: 2. GET /api/v1/policies?city=hangzhou
    CoreAPI->>VueClient: 3. 返回数据包: { schema_ref: "policy_v1.2", items: [ { id, jsonb_payload } ] }
    VueClient->>VueClient: 4. <DynamicCardRenderer :schema="schema" :data="item" /> 自动动态渲染新字段与新交互组件
    Note over VueClient: 前端无需重新发版编译，新字段即时上线
```

### 3.1 后端元数据底座架构 (Backend Engine)
1. **实体持久化双层模型 (Dual-Layer Entity Pattern)**：
   - **基础不变层 (System Invariants)**：`id`, `entity_code`, `status`, `created_at`, `updated_at`, `version` 采用物理数据库列；
   - **动态扩展层 (Dynamic Payload)**：`attributes` 列（PostgreSQL `JSONB`），支持任意深度嵌套结构，并通过 GIN 索引保障查询性能；
2. **Schema 校验器与注册表 (Schema Registry)**：
   - 采用标准 JSON Schema (Draft-07 / 2020-12) 定义每种实体的字段类型（`text`, `number`, `currency`, `date`, `countdown`, `tag`, `action_button`）；
   - 在写入/更新时，FastAPI 动态拉取对应版本的 Schema 进行严格校验（利用 `jsonschema` 或 Pydantic 动态 Type Adapter）；
3. **低代码接口输出约定 (Contract)**：
   - 接口返回不仅包含数据本身，还包含其对应的**渲染元数据**（UI Metadata Hints：组件类型、标签文案、变现标记、布局栅格占比）。

### 3.2 前端低代码组件渲染器 (Frontend Schema Renderer)
1. **原子小部件注册中心 (Atomic Widget Registry)**：
   - 前端维护一套高内聚、纯粹遵循 Anthropic 风格的原子组件库：
     - `BadgeWidget` (变现与分类徽章)
     - `CountdownWidget` (政策截止倒计时)
     - `WhitepaperQuoteWidget` (100字白话带左侧珊瑚红边框)
     - `ClipboardButtonWidget` (一键复制代码并弹窗)
     - `DrawerLinkWidget` (呼出侧边抽屉)
2. **低代码容器组件**：
   - `<DynamicCardRenderer :schema="meta.card" :data="data" />`
   - `<DynamicFilterBar :schema="meta.filters" @change="onFilterChange" />`
   - `<DynamicFormModal :schema="meta.form" v-model="formData" @submit="onSubmit" />`
3. **实现价值**：
   - 当政府出台一种全新形式的“先投后补”或“算力抵用券”，后端只要录入新的 Schema 与数据，**前端不需要修改一行代码、不需要重新打包构建，页面即自动渲染出全新结构的卡片与操作按钮！**

---

## 4. 关键运行场景与数据协同流转 (Runtime & Synchronization) [ARCH-03]

### 4.1 核心读写分离与数据管道 (PG ➔ pgvector ➔ ES)
```text
[ 用户提交 / AI 爬虫导入 ] 
        │
        ▼ (强事务写入)
  [ PostgreSQL 16+ 主库 ] ────(保存结构化主数据与 JSONB 属性)
        │
   (异步事件 Hook / 后台任务)
        ├──► [ 生成 Embedding 向量 ] ──► 写入 pgvector 列并构建 HNSW 索引
        └──► [ 生成搜索 Document ]  ──► 批量推送到 Elasticsearch 8.x (IK 中文分词)
```

- **搜索查询路由**：
  - **常规页面与详情拉取**：直接走 PostgreSQL（命中主键或二级索引，耗时 < 5ms）；
  - **画像智能测算与语义推荐**：走 `pgvector`（余弦距离计算，毫秒级召回相关度前 10 条）；
  - **全局快捷键 Cmd+K 全文长文检索**：走 Elasticsearch（IK 分词 + 词频打分 + 高亮返回）。

---

## 5. 部署与环境配置视图 (Deployment View) [ARCH-04]

针对一人公司极其重视的**轻量化与低运维成本**原则，全栈提供单机全容器化编排支持（Docker Compose）：

```yaml
# 极客极简单机编排拓扑 (docker-compose.yml 逻辑)
services:
  opchub-web:
    image: opchub-frontend:latest
    ports: ["80:80"] # Nginx 反代静态资源并转发 /api 至后端
  
  opchub-api:
    image: opchub-backend:latest
    environment:
      - DATABASE_URL=postgresql+asyncpg://opc_user:pass@opchub-db:5432/opchub
      - ELASTICSEARCH_URL=http://opchub-es:9200
    depends_on: [opchub-db, opchub-es]

  opchub-db:
    image: pgvector/pgvector:pg16 # 内置 PostgreSQL 16 + pgvector 扩展
    volumes: ["pgdata:/var/lib/postgresql/data"]

  opchub-es:
    image: elasticsearch:8.12.0 # 挂载 analysis-ik 中文分词插件
    environment: ["discovery.type=single-node", "ES_JAVA_OPTS=-Xms512m -Xmx512m"]
    volumes: ["esdata:/usr/share/elasticsearch/data"]
```

---

## 6. 质量、安全与风控约束 [ARCH-05]

1. **变现与交易风控防线**：
   - 所有返佣跳转与外包线索对接均在服务端记录完整的 Audit Log，包含防刷机制（单 IP / 单用户频率限制）；
2. **轻量认证与无资金池合规**：
   - 彻底避免资金在平台内部形成资金池，仅做线索对接，规避二清金融风险；
3. **内容安全沙箱**：
   - 论坛与橱窗产品提交入口集成敏感词与违规 URL 黑名单过滤，防止黑灰产污染。

---

## 7. 架构权衡与风险 (Architecture Risks) [ARCH-06]

| 潜在风险 / 技术债 | 发生概率 | 缓解策略与架构防线 |
| :--- | :--- | :--- |
| **ES 与 PG 数据最终一致性延迟** | 低 | 写入后异步刷新，查询详情一律回表 PG，即使 ES 存在秒级延迟也不影响主业务交互； |
| **动态 Schema 复杂度过载** | 中 | 严格限制低代码嵌套深度不超过 3 层，只做字段与布局的动态渲染，复杂业务逻辑依然保持在后端领域服务代码中； |
| **单机资源水位告警** | 低 | 限制 ES 内存堆（512M），初期单台 2核4G 或 4核8G 云服务器即可流畅运行全套微型单体架构。 |
