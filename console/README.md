# OpcHub Console —— 三大支撑平台

基于 MicroFlow 的上层承载平台（框架 README："观测的汇聚、查询、看板、告警由上层承载"）。
适配+剪枝自开源项目（shadcn-admin / React Flow / SigNoz / jaeger-ui / Umami / GrowthBook /
Nacos3 模式），许可证均为 MIT/Apache-2.0；AGPL/公平代码项目仅借鉴交互模式。

## 子项目

| 目录 | 平台 | 状态 |
|---|---|---|
| `orchestration/` | 编排管理：算子/场景目录、版本回滚、发布审批、A/B 实验、配置管理 | M1 建设中 |
| `ops/` | 运维：运行记录/日志搜索/指标看板/瀑布图/调试 | M2 待建 |
| `bizops/` | 运营：业务埋点采集/漏斗留存/实验读出 | M3 待建（依赖主站 Flutter 埋点） |

共享：`packages/ui`（设计系统，token 与主站 Flutter 同源）、`packages/api`（统一网关客户端）。

## 开发

```bash
# 本机为 Samba 共享盘（不支持 symlink），一律 --no-bin-links + node 直调
npm install --prefix orchestration --no-bin-links
npm install --no-bin-links            # 根目录共享依赖（react/clsx 供 packages/ui 向上解析）
cd orchestration && node node_modules/vite/bin/vite.js   # dev（端口 4601，/api 代理到 3000）
node node_modules/vite/bin/vite.js build                 # build → dist/
```

构建产物由 `frontend/server.py` 挂载：`/console/orchestration`。
