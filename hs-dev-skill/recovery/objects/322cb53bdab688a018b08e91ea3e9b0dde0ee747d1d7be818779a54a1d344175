# TASK-018 开发计划与执行日志 (TASK-018 Plan Log)

- **任务编号**：`TASK-018`
- **任务名称**：P10运营大盘微内核DAG编排流水线与三端实时遥测
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **重构直调旁路为微内核编排**：
   - 将现有 `telemetry.dashboard` 和 `ops.dashboard` 从服务单层直调重构为由底层微内核 DAG 编排流水线（`OPC_OPS_DASHBOARD_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向事务补偿**：
   - `telemetry.dashboard.guard`：校验管理员鉴权凭证、时间窗口参数与终端过滤规则。
   - `telemetry.dashboard.collect`：原子聚合全域核心指标（DAU、UV、PV、MAU、留存率、API吞吐、7日趋势、业务模块热力图及三端分布）。
   - `telemetry.dashboard.audit`：生成大盘调阅脱敏签名与安全审计记录，挂载 Saga 逆向补偿 `telemetry.dashboard.audit_compensate`（下游度量失败时标记审计异常撤销）。
   - `telemetry.dashboard.telemetry.incr`：原子自增运营大盘调阅度量计数，支持 `simulate_downstream_failure` 触发 Saga 逆向补偿。
3. **网关适配器挂载与配置驱动**：
   - 编写 `ops_dashboard_adapter`，调用 `orchestration_service.execute_scenario("OPC_OPS_DASHBOARD_PIPELINE", ...)`。
   - 更新 `backend/config/gateway_routes.yaml` 对应场景路由。
4. **前端原型交互与 UI 规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P10 运营大盘（View 11）中展示 `DAG: OPC_OPS_DASHBOARD_PIPELINE` 编排标签。
   - 严格维护按钮文字 $\le 4$ 汉字，0 换行。
5. **严密测试集与质量门禁**：
   - 编写 `backend/tests/test_ops_dag_pipeline.py`，覆盖指标聚合正常输出、Saga 逆向补偿、Guard 校验。
   - 全量回归测试必须 100% 通过（0 报错）。
   - 门禁 `verify_consistency.py` 全绿通过。
