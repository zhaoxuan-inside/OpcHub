# 任务详细设计与执行记录：TASK-009

- **任务名称**：P01首页地图全景微内核DAG编排与全域指标聚合
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P0
- **负责人**：agent
- **开始时间**：`2026-10-17T05:32:06Z`
- **最后更新**：`2026-10-17T05:34:54Z`

---

## 1. 任务背景与目标
通过底层微内核DAG编排框架实现P01首页地图全景指标采集与地图装配流水线

---

## 2. 验收标准
home.overview完全由微内核DAG流水线执行返回，前端动态渲染指标与快捷入口，单测全绿100%通过

---

## 3. 执行步骤 (Checklist)
- [x] 1. 在 AtomicRegistry 中注册首页原子算子 (home.metrics.collector, home.sitemap.builder, home.overview.aggregator)
- [x] 2. 在 OrchestrationService 预置 OPC_HOME_OVERVIEW_PIPELINE DAG 拓扑
- [x] 3. 在 gateway_routes.yaml 中配置 home.overview 由微内核编排流水线驱动
- [x] 4. 前端原型对接 home.overview 动态渲染全景指标与快捷地图
- [x] 5. 编写单元与编排测试 (test_home_overview_dag_pipeline.py 2/2 PASS)
- [x] 6. 全量测试通过 (73/73 PASS) 并执行质量门禁自检

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
backend/src/core/microkernel/registry.py
backend/src/domains/orchestration/service.py
backend/src/core/gateway/adapters.py
hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html
backend/tests/test_home_overview_dag_pipeline.py
```

---

## 5. 验证与门禁记录
- 单测覆盖率：`100% (73/73 PASS)`
- 编排执行验证：`PASS` (验证 OPC_HOME_OVERVIEW_PIPELINE 3 节点拓扑顺序执行并聚合输出)
- 契约比对：`PASS`
