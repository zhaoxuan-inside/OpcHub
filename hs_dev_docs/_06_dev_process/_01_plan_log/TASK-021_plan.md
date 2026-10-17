# TASK-021 实施计划日志 (Plan Log)

- **任务ID**：TASK-021
- **标题**：前端单文件交互控制台全面改接微内核统一网关与全域实时交互闭环
- **分级**：`M`
- **当前状态**：`COMPLETED`
- **目标**：在 `opchub_all_pages_demo.html` 中注入轻量微内核网关客户端 SDK（API Client），实现各页面异步通过 `fetch('/api/welcom/opc_world')` 交互，携带请求体代码版本号 `version: "v1.0.0"`，串联微内核 DAG 编排流水线与 Saga 回滚；并保持离线/无后端环境下的优雅 Fallback 降级机制。

---

## 执行步骤清单

- [x] **步骤 1**：在 `opchub_all_pages_demo.html` 中封装全局统一网关调用函数 `dispatchGateway(scenario, payload, context)`，内置动态探测网关地址、版本注入（`v1.0.0`）、防抖、请求加签与优雅 Fallback。
- [x] **步骤 2**：改接 P01 首页地图全景概览 (`home.overview`)，动态拉取 DAG 聚合的全域创客指标与地图气泡。
- [x] **步骤 3**：改接 P02 社区头脑风暴 (`forum.threads.list`, `forum.thread.publish`, `forum.comment.publish`, `forum.upvote`)，与后端物化路径树及 DAG 审查联动。
- [x] **步骤 4**：改接 P03 产品橱窗 (`products.list`, `products.publish`, `products.upvote`) 与 P04 政策雷达 (`policies.list`, `policies.match`) 动态测算。
- [x] **步骤 5**：改接 P05 需求集市 (`demands.list`, `demands.publish`, `demands.bid`)、P06 流程文书 (`sop.templates.list`, `sop.document.render`) 与 P07 生态特权 (`perks.list`, `perks.claim`)。
- [x] **步骤 6**：改接 P08 合规自检 (`compliance.checkpoints.list`, `compliance.audit.evaluate`) 与 P10 运营大盘 (`ops.dashboard.overview`) 实时遥测。
- [x] **步骤 7**：编写端到端自动化联调测试用例，运行 pytest 127/127 100% 绿灯，通过质量门禁并提交验收。
