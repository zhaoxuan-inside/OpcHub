# TASK-014 开发计划与执行日志 (TASK-014 Plan Log)

- **任务编号**：`TASK-014`
- **任务名称**：P06流程文书微内核DAG编排流水线与文书即时生成
- **责任人**：`hardstone` / `agent`
- **当前状态**：`IN_PROGRESS`

---

## 一、需求与技术目标
1. **重构直调旁路为微内核编排**：
   - 将现有 `sop.document.render` 从服务直调重构成由底层微内核 DAG 编排流水线（`OPC_SOP_DOCUMENT_RENDER_PIPELINE`）驱动。
2. **算子原子化与 Saga 逆向补偿**：
   - `sop.document.validate_guard`：校验文书模版是否存在、表单必填字段是否完整、合规文本敏感词违规审查。
   - `sop.document.render_persist`：结合模版插值渲染标准化公文，签发安全流水号并安全持久化。
   - `sop.document.render_compensate`：下游度量节点或三方公证节点失败时，逆向物理删除/作废生成的文书实例，实现零数据污染。
   - `sop.telemetry.incr`：原子累加已生成公文实例度量打点，支持下游失败模拟触发 Saga 回滚。
3. **网关适配器与路由配置**：
   - 编写 `sop_document_render_adapter`，调用 `orchestration_service.execute_scenario("OPC_SOP_DOCUMENT_RENDER_PIPELINE", ...)`。
   - 更新 `backend/config/gateway_routes.yaml`。
4. **前端原型与交互规范**：
   - 在 `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html` 的 P06 流程文书视图中展示 `DAG: OPC_SOP_DOCUMENT_RENDER_PIPELINE` 标签。
   - 确保文书即时生成操作通过网关 `/api/welcom/opc_world` 驱动。
   - 界面所有按钮字符严格 $\le 4$ 汉字，0 换行。
5. **单元测试与门禁验证**：
   - 编写 `backend/tests/test_sop_dag_pipeline.py`，全量测试 100% 通过。
   - 门禁 `verify_consistency.py` 全绿。
