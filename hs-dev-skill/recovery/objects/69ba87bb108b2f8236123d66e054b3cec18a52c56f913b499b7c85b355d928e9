# TASK-017 开发计划与执行日志 (TASK-017 Plan Log)

- **任务编号**：`TASK-017`
- **任务名称**：P09内容治理微内核DAG编排流水线与全网下架管控
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **重构直调旁路为微内核编排**：
   - 将现有 `moderation.takedown` 和 `moderation.restore` 从单层直调重构为由底层微内核 DAG 编排流水线（`OPC_MODERATION_TAKEDOWN_PIPELINE` 与 `OPC_MODERATION_RESTORE_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向事务补偿**：
   - `moderation.takedown.guard`：校验待下架违规目标 ID 存在性、操作员权限与下架原因合规性。
   - `moderation.takedown.persist`：执行内容状态变更为 `TAKEN_DOWN`，记录下架原因、下架时间及封禁标记，挂载 Saga 逆向补偿 `moderation.takedown.persist_compensate`（当下游度量失败时回滚内容状态为原有状态 `FLAGGED` 并清除下架时间）。
   - `moderation.restore.guard`：校验待恢复言论存在性及处于已下架状态。
   - `moderation.restore.persist`：执行内容状态恢复为 `NORMAL`，记录撤销时间，挂载 Saga 逆向补偿 `moderation.restore.persist_compensate`（回退为 `TAKEN_DOWN`）。
   - `moderation.telemetry.incr`：原子自增内容治理与安全拦截度量指标，支持 `simulate_downstream_failure` 触发 Saga 逆向补偿。
3. **网关适配器挂载与配置驱动**：
   - 编写 `moderation_takedown_adapter` 与 `moderation_restore_adapter`，调用 `orchestration_service.execute_scenario()`。
   - 更新 `backend/config/gateway_routes.yaml` 对应场景路由。
4. **前端原型交互与 UI 规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P09 内容治理（View 12）中展示 `DAG: OPC_MODERATION_TAKEDOWN_PIPELINE` 编排标签。
   - 严格维护按钮文字 $\le 4$ 汉字，0 换行。
5. **严密测试集与质量门禁**：
   - 编写 `backend/tests/test_moderation_dag_pipeline.py`，覆盖下架成功、Saga 下架回滚、恢复成功、Saga 恢复回滚、Guard 校验阻断。
   - 全量回归测试必须 100% 通过（0 报错）。
   - 门禁 `verify_consistency.py` 全绿通过。
