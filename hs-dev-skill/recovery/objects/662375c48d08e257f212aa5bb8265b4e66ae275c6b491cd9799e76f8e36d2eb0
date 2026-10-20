# TASK-015 开发计划与执行日志 (TASK-015 Plan Log)

- **任务编号**：`TASK-015`
- **任务名称**：P07生态特权微内核DAG编排流水线与福利核销
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **重构直调旁路为微内核编排**：
   - 将现有 `perks.claim` 与 `perks.publish` 重构为由底层微内核 DAG 编排流水线（`OPC_PERK_CLAIM_PIPELINE` 与 `OPC_PERK_PUBLISH_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向补偿与配额回补**：
   - `perk.claim.guard`：校验 perk_id 存在、剩余配额 > 0、用户非空。
   - `perk.claim.persist`：安全扣减配额 `quota_remaining -= 1`，签发激活凭据 `OPC-XXXX-2026` 并入库。
   - `perk.claim.persist_compensate`：下游度量失败时，物理撤销领用凭据，原子回补配额 `quota_remaining += 1`。
   - `perk.publish.guard`：校验特权名称、供应商、价值非负及敏感词合规风控。
   - `perk.publish.persist`：录入新特权入库。
   - `perk.publish.persist_compensate`：物理删除录入特权。
   - `perk.telemetry.incr`：度量打点，支持 `simulate_downstream_failure` 触发 Saga 补偿。
3. **网关适配器与路由配置**：
   - 编写 `perk_claim_adapter` 与 `perk_publish_adapter`，接入 `orchestration_service.execute_scenario()`。
   - 更新 `backend/config/gateway_routes.yaml`。
4. **前端原型与交互规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P07 生态特权中展示 `DAG: OPC_PERK_CLAIM_PIPELINE` 标签。
   - 确保特权领用与发布由统一网关 `/api/welcom/opc_world` 驱动。
   - 所有交互按钮字符严格 $\le 4$ 汉字，0 换行。
5. **单元测试与门禁验证**：
   - 编写 `backend/tests/test_perk_dag_pipeline.py`，全量测试 100% 通过。
   - 门禁 `verify_consistency.py` 全绿。
