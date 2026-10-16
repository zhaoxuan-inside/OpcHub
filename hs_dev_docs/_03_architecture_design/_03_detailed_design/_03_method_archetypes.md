# 阶段 3 详细设计：方法类型七分类与抗爆炸契约 (Method Archetypes)

- **模块**：`Engineering Design Standards`
- **阶段**：`Phase 3 (契约六元组)`
- **规约**：`hs-dev-skill Anti-Method-Explosion Protocol`

---

## [VIBE_CONTRACT] 方法类型分类与测试分级契约 (Machine-Actionable Method Spec)
```yaml
method_archetypes_contract:
  anti_explosion_rules:
    - "RULE: 编写通用方法前必须执行意图检索，重合度 >= 80% 强制复用，严禁新增影子方法"
    - "RULE: 单次临时转换逻辑强制内联，禁止提炼为公共函数"
    - "RULE: 纯计算与校验方法必须做到无外部 I/O 依赖，100% 覆盖独立单测"

  archetype_matrix:
    - type: "CALCULATE"
      io_free: true
      test_strategy: "Parameterized Unit Test (DDT)"
      examples: ["invoice_tax_calc", "calculate_vat_exemption"]

    - type: "GUARD"
      io_free: false
      test_strategy: "Boundary & Negative Assertion Test"
      examples: ["auth_guard", "validate_python_code"]

    - type: "ORCHESTRATOR"
      io_free: false
      test_strategy: "Integration Pipeline E2E Test"
      examples: ["execute_dag", "topological_sort"]

    - type: "PERSISTENCE"
      io_free: false
      test_strategy: "Transactional Rollback Test"
      examples: ["save_user_profile", "record_gateway_log"]

    - type: "ADAPTER"
      io_free: false
      test_strategy: "Mock Contract Testing"
      examples: ["stripe_offshore_client", "aws_activate_client"]
```

---

## 1. 七大方法原型详细契约

| 方法原型 | 命名规范 | 纯度 (Purity) | 异常策略 | 核心测试重点 |
|:---|:---|:---:|:---|:---|
| **1. CALCULATE** | `calculate_*` / `compute_*` | 纯函数 (零副作用) | 抛出 ValueError | 极值输入、浮点精度、免税分界线边界 (30万) |
| **2. GUARD** | `validate_*` / `check_*` / `*_guard` | 幂等 | 抛出 PermissionError / ValidationError | 非法字符、违规命令注入、恶意 AST 语法树 |
| **3. ORCHESTRATOR** | `execute_*` / `orchestrate_*` | 协调多节点 | 捕获并记录节点失败 Trace | 拓扑图环路检测、超时间隔熔断、原子回滚 |
| **4. TRANSFORM** | `to_*` / `parse_*` | 纯函数 | 抛出 ParseError | Schema 结构对齐、JSONB 映射完整性 |
| **5. PERSISTENCE** | `save_*` / `get_*` / `update_*` | I/O 副作用 | 抛出 RepositoryError | 事务一致性、外键级联与唯一键冲突 |
| **6. ADAPTER** | `*_client` / `fetch_*_deal` | 外部 I/O | 熔断重试 | 网络丢包重试、第三方厂商鉴权过期 |
| **7. DISPATCH** | `route_*` / `dispatch_*` | 分发路由 | 默认兜底 | 协议路由命中率、三端设备特性自适应分发 |
