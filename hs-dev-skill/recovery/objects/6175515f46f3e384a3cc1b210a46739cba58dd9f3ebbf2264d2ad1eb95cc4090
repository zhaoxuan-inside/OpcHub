# 阶段 3 详细设计：六元组标准化方法契约与 Saga 逆向补偿矩阵 (Six-Tuple Method Contracts)

- **模块**：`Microkernel Orchestration & Domain Methods`
- **阶段**：`Phase 3 (契约六元组)`
- **标准**：`hs-dev-skill Six-Tuple Architecture Specification`

---

## [VIBE_CONTRACT] 六元组运行时与衍生方法契约 (Machine-Actionable Six-Tuple Spec)

```yaml
six_tuple_contract:
  signature_model: "Method(input, output, context, isolate, metrics, recall) -> Exception"
  tuple_definitions:
    input: "只读业务载荷 (Read-Only Payload / DTO)"
    output: "可写业务结果容器 (Write-Only Result Map/Container)"
    context: "链路上下文 (trace_id, span_id, pipeline_id, last_exception)"
    isolate: "严格安全与租户隔离区 (tenant_id, user_id, auth_claims, role)"
    metrics: "可观测度量追加器 (execution_time, counter, gauge)"
    recall: "长事务挂起与状态机唤醒器 (suspend, resume, notify)"

  standard_exception_schema:
    code: "str (大写下划线语义错误码，如 OPERATOR_EXECUTION_TIMEOUT)"
    msg: "str (面向开发者/运维的简要排错描述)"
    retryable: "bool (是否允许幂等重试)"
    details: "dict (现场快照上下文)"

  derived_method_conventions:
    primary: "{method_name} -> 核心正向业务逻辑执行"
    fallback: "{method_name}_fallback -> 服务不可用时触发的兜底逻辑"
    compensate: "{method_name}_compensate -> 分布式事务 Saga 模式逆向回滚与锁释放"
    metrics: "{method_name}_metrics -> 专用度量与业务 SLA 统计"
    recall: "{method_name}_recall -> 异步任务回调或挂起唤醒"
```

---

## 1. 六元组模型架构与解耦机制

六元组将微内核算子与领域方法的关注点彻底正交解耦：

$$\text{Method}(Input, Output, Context, Isolate, Metrics, Recall) \to Exception$$

```text
       ┌───────────┐       ┌────────────┐
       │   Input   │       │   Output   │
       └─────┬─────┘       └─────▲──────┘
             │                   │
      ┌──────▼───────────────────┴──────┐
      │     Core Operator Method        │ ───► Exception (None on Success)
      └──────┬──────────┬────────┬──────┘
             │          │        │
       ┌─────▼─────┐ ┌──▼───┐ ┌──▼───┐
       │  Context  │ │Isolat│ │Recall│
       └───────────┘ └──────┘ └──────┘
             │
       ┌─────▼─────┐
       │  Metrics  │
       └───────────┘
```

---

## 2. 核心领域算子六元组契约与 Saga 逆向补偿矩阵

| 算子名称 (Operator Name) | 核心主方法 (`method_name`) | 逆向补偿方法 (`_compensate`) | 降级兜底方法 (`_fallback`) | 事务保证与回滚语义 |
| :--- | :--- | :--- | :--- | :--- |
| `products.publish` | 校验入参并写入产品橱窗仓库 | 从作品库下架撤销该商品，释放锁定标识 | 返回草稿暂存态或降级提示 | 补偿释放橱窗槽位 |
| `policies.match` | 计算减税额与企业资质匹配度 | 无状态纯计算（无需物理补偿） | 返回标准小微基础免征指引 | 降级兜底推荐保底政策 |
| `demands.bid` | 校验创客资质并冻结竞标保证金 | 解冻已扣减保证金，标记竞标记录撤回 | 提示人流过大转入异步排队队列 | 严格金融级资金双向回滚 |
| `sop.document.render` | 渲染 Jinja2 文档并写入持久化 | 物理标记该文书实例为作废 (VOIDED) | 返回纯文本空白模版 | 补偿软删除作废实例 |
| `compliance.audit` | 执行六维合规防线动态打分 | 无物理副作用，重置暂存打分会话 | 返回默认预警级检测报告 | 纯计算异常回滚 |
| `telemetry.dashboard` | 聚合全域创客、流水线与撮合指标 | 无状态度量查询 | 返回上一周期缓存快照 (Cache Stale) | 优雅容灾降级 |

---

## 3. 微内核 DAG 编排引擎 Saga 逆向补偿回滚算法规约

当一个 DAG 场景流水线（例如：`审核 -> 冻结保证金 -> 生成合同 -> 发布需求`）在第 $k$ 个节点执行失败或被安全守卫（Guard）拦截时：
1. **中断正向执行**：立即终止后续未执行节点；
2. **收集已完成节点栈**：反转已成功执行的节点列表 $[N_1, N_2, \dots, N_{k-1}]$ 为 $[N_{k-1}, \dots, N_2, N_1]$；
3. **依次触发补偿**：对每一个已成功节点，查找并调用其注册的 `{action_handler}_compensate` 补偿函数；
4. **补偿现场记录**：将逆向回滚的每一个节点的耗时、状态与输出完整记录在 `ExecutionResult.compensation_traces` 中；
5. **最终状态收敛**：若全部补偿成功，流水线状态置为 `ROLLED_BACK`；若补偿发生异常，置为 `COMPENSATION_FAILED` 并告警。
