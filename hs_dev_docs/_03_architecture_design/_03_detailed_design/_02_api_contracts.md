# 阶段 3 详细设计：RESTful API 契约与接口规格 (API Contracts)

- **协议**：`HTTP/2 & HTTP/3 RESTful`
- **契约标准**：`OpenAPI 3.1 / Pydantic v2`
- **阶段**：`Phase 3 (契约六元组)`

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
