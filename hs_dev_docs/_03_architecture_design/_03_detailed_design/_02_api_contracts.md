# 阶段 3 详细设计：RESTful API 契约与接口规格 (API Contracts)

- **协议**：`HTTP/2 & HTTP/3 RESTful`
- **契约标准**：`OpenAPI 3.1 / Pydantic v2`
- **阶段**：`Phase 3 (契约六元组)`

> ⚠️ **架构变更提示（TASK-031，2026-10）— 单一统一入口**
>
> 依据框架详细设计 §3.3「统一入站网关与场景动态路由规约」，本文件下述**按 URL 分节的业务 REST 路径已全部移除**（历史契约，仅供参考用语义）。
> 当前全平台业务请求**唯一入口**为：
>
> ```http
> POST /api/welcom/opc_world        # 别名: /api/welcome/opc_world, /api/v1/dispatch, /api/v1/gateway/dispatch
> Content-Type: application/json
>
> {
>   "scenario": "products.publish",   # 业务场景码（见 backend/config/gateway_routes.yaml）
>   "version":  "v1.0.0",
>   "payload":  { /* 场景入参 */ },
>   "context":  { /* 可选：client_env / client_ip / trace_id 等 */ },
>   "token":    "可选：会话 Token（或置于 Authorization: Bearer 头）"
> }
> ```
>
> - **响应信封**：HTTP 恒为 `200`，业务结果以信封 `code` 表达（`200` 成功 / `400` 参数 / `401` 未登录 / `403` 越权 / `404` 不存在 / `500` 内部错误）。
> - **鉴权**：身份来自 `Authorization: Bearer`、`context.token` 或 `payload.token`；RBAC/ABAC 由网关统一执行，`context.user_id` 不被信任。
> - **场景清单 / 写操作权限**：见 `backend/config/gateway_routes.yaml`（54 个业务场景）。
> - **仅保留的平台/管理端点**：统一网关入口、系统探针（`/livez` `/readyz` `/healthz` `/health`）、微内核自省（`/microkernel/methods` `/microkernel/dag/execute` `/microkernel/sandbox/validate`）、动态算子管理（`/scripts/*`，ADMIN）、安全审计（`/admin/audit/*`，ADMIN）、落地页（`/`、`/app`）。
>
> 变更记录见 [TASK-031_plan.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_06_dev_process/_01_plan_log/TASK-031_plan.md)。

---

## [VIBE_CONTRACT] API 接口定义与错误码契约 (Machine-Actionable API Contract)
```yaml
api_contract:
  base_url: "/api/v1"
  content_type: "application/json"
  auth_header: "Authorization: Bearer <token>"
  
  error_envelope:
    error_code: "STRING (e.g. ENTITLEMENT_REQUIRED)"
    message: "STRING (Human readable explanation)"
    status_code: "INTEGER (HTTP status)"
    timestamp: "ISO8601"

  endpoints:
    # 1. 运营数据大盘 (Ops Intelligence)
    - path: "/ops/dashboard"
      method: "GET"
      auth: "ADMIN"
      summary: "获取全域 DAU/UV/PV、转化留存与三端流量渗透数据"

    # 2. 微内核 DAG 编排 (Microkernel Engine)
    - path: "/microkernel/dag/execute"
      method: "POST"
      auth: "OPTIONAL"
      summary: "执行编译就绪的 DAG 拓扑链路"

    - path: "/microkernel/sandbox/validate"
      method: "POST"
      auth: "ADMIN"
      summary: "AST 静态安全检测与函数签名签发"

    # 3. 政策雷达与测算 (Policy Radar)
    - path: "/policies/match"
      method: "POST"
      auth: "OPTIONAL"
      summary: "基于小微纳税主体信息测算免税与补贴资格"

    # 4. SOP 流程材料生成 (SOP Generator)
    - path: "/sop/document/export"
      method: "POST"
      auth: "AUTHENTICATED"
      summary: "根据创客填报字段生成标准个体户申请书"

    # 5. 创客论坛讨论帖与多级问答树 (Forum Engine)
    - path: "/forum/threads"
      method: "POST"
      auth: "AUTHENTICATED"
      summary: "发布创客讨论帖 (publish_post)"

    - path: "/forum/threads"
      method: "GET"
      auth: "OPTIONAL"
      summary: "分页检索论坛讨论帖列表"

    - path: "/forum/threads/{thread_id}"
      method: "GET"
      auth: "OPTIONAL"
      summary: "获取讨论帖详情及全量多级问答递归嵌套树"

    - path: "/forum/threads/{thread_id}/comments"
      method: "POST"
      auth: "AUTHENTICATED"
      summary: "发表顶级回答或多级楼中楼回复 (reply_comment)"

    - path: "/forum/upvote"
      method: "POST"
      auth: "AUTHENTICATED"
      summary: "帖子或回复认同点赞原子切换 (toggle_upvote)"

    - path: "/forum/bookmark"
      method: "POST"
      auth: "AUTHENTICATED"
      summary: "讨论帖收藏归档原子切换 (toggle_bookmark)"
```

---

## 1. 核心接口详细规格

### 1.1 运营大盘实时数据接口 (`GET /api/v1/ops/dashboard`)
- **请求方法**：`GET`
- **权限要求**：`ROLE: ADMIN`
- **响应 Schema**：
```json
{
  "timestamp": "2026-10-16T13:51:00Z",
  "is_live": true,
  "dau": { "label": "DAU 日活跃创客", "value": "14,820", "delta_percent": 12.4, "trend": "UP", "sub_text": "昨日 13,180" },
  "uv": { "label": "UV 今日独立访客", "value": "89,540", "delta_percent": 18.6, "trend": "UP", "sub_text": "移动端 68.4%" },
  "pv": { "label": "PV 页面总浏览量", "value": "628,300", "delta_percent": 24.1, "trend": "UP", "sub_text": "人均 7.01 页" },
  "mau": { "label": "MAU 月活创客数", "value": "182,450", "delta_percent": 8.2, "trend": "UP", "sub_text": "渗透率 41%" },
  "retention": { "label": "次日 / 7日留存率", "value": "64.2% / 48.5%", "delta_percent": 4.82, "trend": "UP", "sub_text": "黑钻4,316人" },
  "api_throughput": { "label": "微内核 API 吞吐", "value": "12.8M 次/日", "delta_percent": 0.0, "trend": "UP", "sub_text": "P99: 28ms" },
  "daily_trends": [
    { "date": "10-16", "pv": 628300, "uv": 89540, "dau": 14820 }
  ],
  "terminal_distribution": {
    "ios_percentage": 46.2,
    "android_percentage": 35.8,
    "desktop_web_percentage": 18.0
  }
}
```

### 1.2 微内核 DAG 编排执行接口 (`POST /api/v1/microkernel/dag/execute`)
- **请求载荷**：
```json
{
  "config": {
    "version": "v1.0.4-draft",
    "scenario_code": "tax.calculate_vat_exemption",
    "execution_graph": {
      "topology": "DAG",
      "entry_node": "dnode-1",
      "nodes": [
        { "id": "dnode-1", "action_handler": "gateway_ingress", "type": "GATEWAY" },
        { "id": "dnode-2", "action_handler": "auth_guard", "type": "GUARD" },
        { "id": "dnode-3", "action_handler": "invoice_tax_calc", "type": "BIZ" },
        { "id": "dnode-4", "action_handler": "es_audit_sync", "type": "STORAGE" }
      ],
      "edges": [
        { "from": "dnode-1", "to": "dnode-2" },
        { "from": "dnode-2", "to": "dnode-3" },
        { "from": "dnode-3", "to": "dnode-4" }
      ]
    }
  },
  "inputs": {
    "quarterly_income": 280000.0,
    "auth_token": "valid_token"
  }
}
```
- **响应 Schema**：
```json
{
  "pipeline_id": "pipe_3a9f182e",
  "version": "v1.0.4-draft",
  "scenario_code": "tax.calculate_vat_exemption",
  "status": "SUCCESS",
  "total_duration_ms": 12.45,
  "entry_node": "dnode-1",
  "node_traces": [
    { "node_id": "dnode-1", "action_handler": "gateway_ingress", "status": "SUCCESS", "duration_ms": 1.2 },
    { "node_id": "dnode-2", "action_handler": "auth_guard", "status": "SUCCESS", "duration_ms": 2.1 },
    { "node_id": "dnode-3", "action_handler": "invoice_tax_calc", "status": "SUCCESS", "duration_ms": 4.8 },
    { "node_id": "dnode-4", "action_handler": "es_audit_sync", "status": "SUCCESS", "duration_ms": 3.9 }
  ],
  "final_output": {
    "vat_exemption_eligible": true,
    "applicable_tax_rate": 0.0,
    "estimated_tax_payable": 0.0,
    "legal_basis": "财政部 税务总局公告 2023年第12号"
  }
}
```

### 1.3 创客论坛讨论帖与多级问答树接口 (`GET/POST /api/v1/forum/...`)

#### 1.3.1 发帖接口 (`POST /api/v1/forum/threads`)
- **请求载荷**：
```json
{
  "category_code": "DEV",
  "author_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "一人公司基于 Claude 3.5 Sonnet 与 AST 沙箱自动化重构实践",
  "content": "详细复盘独立创客如何在 3 小时内实现自动化安全检测引擎..."
}
```
- **响应 Schema**：返回 `ForumThreadResponse`，含自增 `view_count`, `upvote_count`, `comment_count`, `bookmark_count` 初始值 0 与状态 `PUBLISHED`。

#### 1.3.2 发表回答与多级楼中楼回复 (`POST /api/v1/forum/threads/{thread_id}/comments`)
- **请求载荷**：
```json
{
  "author_id": "7ca85f64-5717-4562-b3fc-2c963f66afb7",
  "content": "请问沙箱对于内置 `__builtins__` 的动态导入是否有深层拦截？",
  "parent_id": "optional-uuid-of-parent-comment",
  "reply_to_user_id": "optional-uuid-of-replied-maker"
}
```
- **响应 Schema**：返回 `ForumCommentResponse`，由后端自动计算 `root_id`、`materialized_path`（如 `/root_id/parent_id/comment_id`）与 `depth`。

#### 1.3.3 获取帖子详情与完整递归嵌套树 (`GET /api/v1/forum/threads/{thread_id}`)
- **响应 Schema** (`ThreadDetailResponse`)：
```json
{
  "thread": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "category_code": "DEV",
    "title": "一人公司基于 Claude 3.5 Sonnet 实践",
    "content": "...",
    "upvote_count": 42,
    "comment_count": 18,
    "bookmark_count": 15,
    "created_at": "2026-10-16T15:00:00Z"
  },
  "comments": [
    {
      "id": "c-root-1",
      "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "author_id": "maker-1",
      "content": "顶级回答：AST 静态分析是第一道防线...",
      "parent_id": null,
      "root_id": "c-root-1",
      "materialized_path": "/c-root-1",
      "depth": 0,
      "upvote_count": 12,
      "children": [
        {
          "id": "c-sub-1",
          "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "author_id": "maker-2",
          "content": "二级楼中楼回复：同意，配合 ptrace 效果更好",
          "parent_id": "c-root-1",
          "root_id": "c-root-1",
          "reply_to_user_id": "maker-1",
          "materialized_path": "/c-root-1/c-sub-1",
          "depth": 1,
          "upvote_count": 3,
          "children": []
        }
      ]
    }
  ]
}
```

### 1.4 认同点赞与收藏归档原子操作接口

#### 1.4.1 认同点赞切换 (`POST /api/v1/forum/upvote`)
- **请求载荷**：
```json
{
  "user_id": "user-uuid",
  "target_type": "THREAD", // 或 "COMMENT"
  "target_id": "target-uuid"
}
```
- **响应 Schema** (`UpvoteResponse`)：
```json
{
  "is_upvoted": true,
  "upvote_count": 43,
  "target_type": "THREAD",
  "target_id": "target-uuid"
}
```

#### 1.4.2 收藏归档切换 (`POST /api/v1/forum/bookmark`)
- **请求载荷**：
```json
{
  "user_id": "user-uuid",
  "thread_id": "thread-uuid",
  "folder_name": "默认收藏夹"
}
```
- **响应 Schema** (`BookmarkResponse`)：
```json
{
  "is_bookmarked": true,
  "bookmark_count": 16,
  "thread_id": "thread-uuid",
  "folder_name": "默认收藏夹"
}
```

### 1.5 流程文书模板库与申报材料生成接口 (`/api/v1/sop/...`)

#### 1.5.1 获取 SOP 全阶段及预置标准模板 (`GET /api/v1/sop/templates`)
- **响应 Schema**：
```json
{
  "stages": [
    { "stage": 1, "name": "阶段 01: 主体定名与税种选型", "code": "STAGE_TAX_ENTITY" },
    { "stage": 2, "name": "阶段 02: 银行基本户与发票授信", "code": "STAGE_BANK_INVOICE" },
    { "stage": 3, "name": "阶段 03: 软著申报与技术入库", "code": "STAGE_IP_COPYRIGHT" },
    { "stage": 4, "name": "阶段 04: 跨境结汇通道配置", "code": "STAGE_CROSS_BORDER" }
  ],
  "templates": [
    {
      "id": "tpl_individual_biz_reg",
      "stage": 1,
      "code": "INDIVIDUAL_BIZ_REG",
      "name": "个体工商户设立登记标准申请书",
      "category": "TAX",
      "description": "标准政务规范设立登记表，支持免实际租约商务秘书集群地址",
      "required_fields": [
        { "key": "company_name", "label": "拟定经营主体字号", "type": "string" },
        { "key": "founder_name", "label": "法定代表创客姓名及身份证", "type": "string" },
        { "key": "biz_scope", "label": "主营经营范围代码", "type": "string" },
        { "key": "address_type", "label": "注册地址类型", "type": "select" }
      ]
    }
  ]
}
```

#### 1.5.2 提交申报表单并由后端渲染保存材料 (`POST /api/v1/sop/documents`)
- **请求载荷**：
```json
{
  "template_id": "tpl_individual_biz_reg",
  "user_id": "usr_2026_opc_9981",
  "form_data": {
    "company_name": "极客视界（杭州）信息技术工作室",
    "founder_name": "赵玄 (33010619920101XXXX)",
    "biz_scope": "软件开发；信息技术咨询服务；人工智能应用软件开发",
    "address_type": "集群租赁商务秘书地址 (免实际租赁)"
  }
}
```
- **响应 Schema**：
```json
{
  "id": "doc_9f81a7bc-28b3-4611",
  "template_id": "tpl_individual_biz_reg",
  "document_title": "个体工商户设立登记申请书 - 极客视界（杭州）信息技术工作室",
  "rendered_content": "个体工商户设立登记申请书\n---------------------------------------------\n登记机关：市场监督管理局\n...",
  "compliance_passed": true,
  "status": "READY",
  "created_at": "2026-10-16T15:15:00Z"
}
```

### 1.6 独立产品橱窗接口 (`GET/POST /api/v1/products`)
- `GET /api/v1/products?category=AI`: 获取创客独立产品列表。
- `POST /api/v1/products`: 提交产品橱窗展示。

### 1.7 政策雷达与智能测算接口 (`GET/POST /api/v1/policies/...`)
- `GET /api/v1/policies`: 获取全国及地方扶持补贴政策列表。
- `POST /api/v1/policies/match`:
  - **请求载荷**：`{ "quarterly_income": 280000, "maker_type": "INDIVIDUAL", "region": "杭州" }`
  - **响应 Schema**：`{ "eligible": true, "applicable_tax_rate": 0.0, "estimated_tax_savings": 8400.0, "matched_policies": [...] }`

### 1.8 需求集市与竞标接口 (`GET/POST /api/v1/demands/...`)
- `GET /api/v1/demands`: 获取企业委托需求集市列表。
- `POST /api/v1/demands`: 企业或创客发布委托需求。
- `POST /api/v1/demands/{demand_id}/bids`: 创客提交竞标方案与报价。

### 1.9 开发者生态特权接口 (`GET/POST /api/v1/perks/...`)
- `GET /api/v1/perks`: 获取算力与基础设施特权权益清单。
- `POST /api/v1/perks/claim`: 领取/兑换专属特权，返回核销凭据与卡密。

### 1.10 用户档案与收费权益中心 (`GET/POST /api/v1/user/...`)
- `GET /api/v1/user/profile`: 获取创客档案、当前 VIP 会员等级与特权状态。
- `POST /api/v1/user/entitlements/activate`: 购买/激活高级门禁收费权益凭据。

### 1.11 编排配置持久化接口 (`POST/GET /api/v1/microkernel/dag/configs`, `/frontend/layouts`)
- `POST /api/v1/microkernel/dag/configs`: 保存 DAG 流程图版本配置并自动热载。
- `GET /api/v1/microkernel/dag/configs`: 按工作版本获取已生效的微内核 DAG 拓扑图。
- `POST /api/v1/frontend/layouts`: 保存前端 24 栅格低代码画布布局配置。
- `GET /api/v1/frontend/layouts`: 加载最新发布的前端画布布局配置。

### 1.12 管理员网页违规言论处理与下架接口 (`GET/POST /api/v1/admin/moderation/...`)
- `GET /api/v1/admin/moderation/items`: 管理员查询全站被举报或系统监测标记的待审言论清单。
  - **响应 Schema**：`List[ModerationItemResponse]` (含 item_id, target_type, target_id, author_id, author_name, snippet_content, violation_type, status, reported_at)
- `POST /api/v1/admin/moderation/takedown`: 执行违规言论下架处置。
  - **请求载荷**：`{ "item_id": "mod-1", "reason": "涉嫌商业机密泄露与灰产倒卖", "moderator_id": "admin_001", "ban_author": false }`
  - **响应 Schema**：`{ "item_id": "mod-1", "status": "TAKEN_DOWN", "moderated_at": "2026-10-17T00:30:00Z", "note": "言论已全站下架" }`
- `POST /api/v1/admin/moderation/restore`: 撤销下架处罚，恢复正常展示。
  - **请求载荷**：`{ "item_id": "mod-1", "moderator_id": "admin_001" }`
  - **响应 Schema**：`{ "item_id": "mod-1", "status": "NORMAL", "moderated_at": "2026-10-17T00:30:00Z" }`


