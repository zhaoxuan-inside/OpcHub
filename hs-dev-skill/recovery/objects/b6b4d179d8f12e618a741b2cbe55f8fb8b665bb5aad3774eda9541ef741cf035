# TASK-016 开发计划与执行日志 (TASK-016 Plan Log)

- **任务编号**：`TASK-016`
- **任务名称**：P08合规指南微内核DAG编排流水线与上线自检雷达
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **重构直调旁路为微内核编排**：
   - 将现有 `compliance.audit` 从服务直调重构为由底层微内核 DAG 编排流水线（`OPC_COMPLIANCE_AUDIT_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向补偿**：
   - `compliance.audit.guard`：校验自检项目输入格式有效性及前置安全门禁。
   - `compliance.evaluate_audit`：执行六维合规防线自检打分，严格支持 CRITICAL 等级高危阻断。
   - `compliance.audit.compensate`：下游度量失败时逆向回滚会话状态，保证无副作用。
   - `compliance.telemetry.incr`：原子自增合规自检评测度量指标，支持 `simulate_downstream_failure` 触发 Saga 补偿。
3. **网关适配器挂载与配置驱动**：
   - 编写 `compliance_audit_adapter`，调用 `orchestration_service.execute_scenario("OPC_COMPLIANCE_AUDIT_PIPELINE", ...)`。
   - 更新 `backend/config/gateway_routes.yaml`。
4. **前端原型交互与 UI 规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P08 合规指南（View 13）中展示 `DAG: OPC_COMPLIANCE_AUDIT_PIPELINE` 编排标签。
   - 严格维护按钮文字 $\le 4$ 汉字，0 换行。
5. **严密测试集与质量门禁**：
   - 编写 `backend/tests/test_compliance_dag_pipeline.py`，覆盖正常评分、高危评分阻断、Saga 逆向补偿。
   - 全量回归测试必须 100% 通过（0 报错）。
   - 门禁 `verify_consistency.py` 全绿通过。
