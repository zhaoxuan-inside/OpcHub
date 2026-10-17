# TASK-019 开发计划与执行日志 (TASK-019 Plan Log)

- **任务编号**：`TASK-019`
- **任务名称**：P11创客中心微内核DAG编排流水线与收费权益激活
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **重构直调旁路为微内核编排**：
   - 将现有 `user.profile` 和 `user.entitlements.activate` 从服务直调重构为由底层微内核 DAG 编排流水线（`OPC_USER_PROFILE_PIPELINE` 与 `OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向事务补偿**：
   - `user.profile.guard`：校验用户 ID 格式与访问权限。
   - `user.profile.load`：原子加载创客主体认证信息、信用代码及权益矩阵。
   - `user.entitlement.activate.guard`：校验待激活收费权益有效性与重复激活拦截。
   - `user.entitlement.activate.persist`：执行权益原子激活，生成防伪发票流水号，挂载 Saga 逆向补偿 `user.entitlement.activate.persist_compensate`（下游度量失败时回滚撤销权益激活）。
   - `user.telemetry.incr`：原子自增创客中心档案访问与权益购买转化度量指标，支持 `simulate_downstream_failure` 触发 Saga 逆向补偿。
3. **网关适配器挂载与配置驱动**：
   - 编写 `user_profile_adapter` 与 `user_entitlement_activate_adapter`，调用 `orchestration_service.execute_scenario()`。
   - 更新 `backend/config/gateway_routes.yaml` 对应场景路由。
4. **前端原型交互与 UI 规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P11 创客中心（View 8 / view-user）中展示 `DAG: OPC_USER_PROFILE_PIPELINE` 编排标签。
   - 严格维护按钮文字 $\le 4$ 汉字，0 换行。
5. **严密测试集与质量门禁**：
   - 编写 `backend/tests/test_user_dag_pipeline.py`，覆盖档案检索、权益激活、Saga 逆向补偿回滚、Guard 校验。
   - 全量回归测试必须 100% 通过（0 报错）。
   - 门禁 `verify_consistency.py` 全绿通过。
