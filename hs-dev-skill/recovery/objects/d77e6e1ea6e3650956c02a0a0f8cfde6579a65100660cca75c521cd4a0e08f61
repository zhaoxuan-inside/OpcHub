# 任务详细设计与执行记录：TASK-007

- **任务名称**：低代码可组合微内核双模调度器与全域领域算子聚合流水线
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P0
- **负责人**：hardstone
- **开始时间**：`2026-10-17T02:10:00Z`
- **完成时间**：`2026-10-17T02:20:00Z`
- **最后更新**：`2026-10-17T02:20:00Z`

---

## 1. 任务背景与目标
- 落实用户架构诉求与 `opchub_composable_framework_architecture.md`：
  1. **低代码服务组合**：将业务各模块能力抽象为原子算子（Atomic Operators），支持通过低代码平台将算子组合为场景流水线（DAG Pipeline）。
  2. **双模调度器 (DualModeDispatcher)**：初期为单体架构，采用进程内直接方法调用（`IN_PROCESS`，零网络延迟）；预留未来解耦为独立微服务时的 HTTP 远程调用（`HTTP_REMOTE`），实现 0 领域代码改动的平滑微服务演进。
  3. **统一外部服务出站网关整合**：将已建成的 `external_gateway`（AI、支付、短信、政务爬虫）作为原子算子接入微内核，供低代码流水线调用。
  4. **全域领域算子自动装配**：`policies`、`sop`、`compliance`、`moderation` 等核心业务能力统一注册至 `AtomicRegistry`。
  5. **API 与前端大盘联动**：提供场景流水线执行接口 `/api/v1/orchestration/scenarios/execute`，在前端微内核编排控制台（View 10）实时展示算子库与执行动效。

---

## 2. 验收标准
1. 单元测试 100% 通过（新增双模调度与低代码场景单测，全量测试 $\ge 50$ 且全部 PASS）。
2. `DualModeDispatcher` 支持在 `IN_PROCESS` 模式下直接执行已注册领域算子，在 `HTTP_REMOTE` 模式下预留并测试远程请求派发。
3. 暴露场景流水线聚合执行接口 `/api/v1/orchestration/scenarios/execute`，支持端到端运行 `OPC_COMPLIANCE_STARTUP_FLOW` 等多节点流水线。
4. 全站按钮文本严格遵守 $\le 4$ 汉字，0 换行。
5. 前端编排控制台（View 10）支持查看算子库、切换调度模式并在界面上触发执行场景流水线。
6. `verify_consistency.py` 质量门禁 0 Error, 0 Warning。

---

## 3. 执行步骤 (Checklist)
- [x] 1. 编写任务三件套 (`_00_task.idx`, `_01_task_brief_001.md`, `_00_task_detail.md`, `_00_context_pack.md`, `TASK-007_plan.md`)
- [x] 2. 实现微内核双模调度器 `DualModeDispatcher` (`backend/src/core/microkernel/dispatcher.py`)
- [x] 3. 扩展算子注册中心，接入全域领域算子与外部网关算子 (`backend/src/core/microkernel/registry.py`)
- [x] 4. 重构微内核引擎 `MicrokernelEngine` 支持基于 Dispatcher 调度节点执行 (`backend/src/core/microkernel/engine.py`)
- [x] 5. 在 FastAPI (`backend/src/main.py`) 增加算子清单与低代码场景流水线执行端点
- [x] 6. 编写全覆盖单测 (`backend/tests/test_composable_microkernel_dispatcher.py`)，验证单体直接调用、Trace 透传及场景执行
- [x] 7. 在 `opchub_all_pages_demo.html` View 9 增加低代码流水线组合与双模调度执行面板
- [x] 8. 运行全量测试与一致性门禁检查，完成验收并归档

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
backend/src/core/microkernel/dispatcher.py
backend/src/core/microkernel/engine.py
backend/src/core/microkernel/registry.py
backend/src/main.py
backend/tests/test_composable_microkernel_dispatcher.py
hs_dev_docs/_00_project_foundation/_02_dictionary/_02_project_word.dict.yaml
hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html
hs_dev_docs/_03_acceptance/task_007_acceptance.md
hs_dev_docs/_05_task_orchestration/_00_task.idx
hs_dev_docs/_05_task_orchestration/_01_task_brief/_01_task_brief_001.md
hs_dev_docs/_05_task_orchestration/_02_task_detail/_01_TASK-007/_00_task_detail.md
hs_dev_docs/_05_task_orchestration/_03_task_context_pack/_01_TASK-007/_00_context_pack.md
hs_dev_docs/_06_dev_process/_01_plan_log/TASK-007_plan.md
```
