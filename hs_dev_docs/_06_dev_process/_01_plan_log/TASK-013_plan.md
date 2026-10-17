# TASK-013 开发计划与执行日志 (TASK-013 Plan Log)

- **任务编号**：`TASK-013`
- **任务名称**：P05需求集市微内核DAG编排流水线与创客竞标撮合
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **彻底消除直调与旁路逻辑**：
   - 将现有 `demands.publish` 与 `demands.bid` 从简单直接调用重构成由底层微内核 DAG 编排流水线（`OPC_DEMAND_PUBLISH_PIPELINE` 与 `OPC_DEMAND_BID_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向补偿**：
   - 需求发布流水线：
     - `demand.publish.guard`：校验需求标题、描述、预算（非负）、分类（DEV/AI/TAX/LEGAL/BIZ）、合规文本敏感词防刷检测。
     - `demand.publish.persist`：安全入库，生成唯一需求 ID、截止日期与初始状态。
     - `demand.publish.persist_compensate`：下游度量节点或外部存管失败时，物理撤销删除需求，保证零脏数据。
     - `demand.telemetry.incr`：原子累加活跃需求度量指标。
   - 竞标方案提交流水线：
     - `demand.bid.guard`：校验需求是否存在且为 OPEN 状态、竞标金额与交付周期有效性、创客资质、防刷检测。
     - `demand.bid.persist`：安全写入竞标提案，原子递增需求的 `bidders_count += 1`。
     - `demand.bid.persist_compensate`：下游度量节点失败时，物理撤销竞标记录，原子回退 `bidders_count -= 1`。
     - `demand.telemetry.incr`：原子累加竞标撮合度量指标。
3. **网关适配器挂载与配置驱动**：
   - 编写 `demand_publish_adapter` 与 `demand_bid_adapter`，接入 `orchestration_service.execute_scenario()`。
   - 在 `backend/config/gateway_routes.yaml` 中更新 `demands.publish` 与 `demands.bid` 路由。
4. **前端原型交互与 UI 规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P05 需求集市中显示 `DAG: OPC_DEMAND_PUBLISH_PIPELINE` 和 `DAG: OPC_DEMAND_BID_PIPELINE` 编排标签。
   - 严格维护按钮文字 $\le 4$ 汉字，0 换行。
5. **严密测试集与质量门禁**：
   - 编写 `backend/tests/test_demand_dag_pipeline.py`，覆盖正常流、敏感词拦截阻断、Saga 逆向回滚。
   - 全量回归测试必须 100% 通过（0 报错）。
   - 门禁 `verify_consistency.py` 全绿通过。
