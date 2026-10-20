# TASK-020 开发计划与执行日志 (TASK-020 Plan Log)

- **任务编号**：`TASK-020`
- **任务名称**：P12编排控制台微内核DAG流程图可视化管理与部署
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **重构直调旁路为微内核编排**：
   - 将现有 `orchestration.operators.list` 和 `orchestration.dag.save` 从服务单层直调重构为由底层微内核 DAG 编排流水线（`OPC_ORCHESTRATION_OPERATORS_LIST_PIPELINE` 与 `OPC_ORCHESTRATION_CONTROL_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向事务补偿**：
   - `orchestration.control.guard`：校验拓扑配置参数完整性、版本号及 DAG 无环有向图结构。
   - `orchestration.control.persist`：编译 SHA-256 拓扑哈希、原子持久化与热载部署生效。
   - `orchestration.control.persist_compensate`：下游度量失败时逆向回滚撤销新注册拓扑配置。
   - `orchestration.control.telemetry.incr`：原子自增编排控制台部署度量打点，支持 `simulate_downstream_failure` 触发 Saga 逆向补偿。
   - `orchestration.operators.guard` 与 `orchestration.operators.collect`：原子化枚举并聚合跨 12 个业务领域的全量微内核算子描述符元数据。
3. **网关适配器挂载与配置驱动**：
   - 编写 `save_dag_config_adapter` 与 `list_operators_adapter`，调用 `orchestration_service.execute_scenario()`。
   - 更新 `backend/config/gateway_routes.yaml` 对应场景路由。
4. **前端原型交互与 UI 规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P12 编排控制台（View 9 / view-backend-orch）中展示 `DAG: OPC_ORCHESTRATION_CONTROL_PIPELINE` 编排标签。
   - 严格维护按钮文字 $\le 4$ 汉字，0 换行。
5. **严密测试集与质量门禁**：
   - 编写 `backend/tests/test_orch_console_dag_pipeline.py`，覆盖全域算子列表检索、拓扑编译部署、Saga 逆向补偿回滚、Guard 校验。
   - 全量回归测试必须 100% 通过（0 报错）。
   - 门禁 `verify_consistency.py` 全绿通过。
