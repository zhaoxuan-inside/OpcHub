# 任务计划与总结：TASK-034 框架能力增强 · 微内核多版本文件感知与动态热加载体系

- **任务编号**：TASK-034
- **任务分级**：`M` (Medium)
- **优先级**：`P0`
- **执行人**：agent
- **意图**：`BUILD / FRAMEWORK_ENHANCEMENT`（落地实现增强框架的热重载能力：检测到新增、修改或删除 .py 文件后框架自动感知并隔离暂存，跟随版本控制安全加载到内存中正式生效，实现零宕机平滑演进）
- **关联设计与标准**：
  - [_04_framework_detailed_design.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_04_framework_detailed_design.md) §3.2 动态算子与安全沙箱
  - [_04_framework_detailed_design.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_04_framework_detailed_design.md) §3.3 统一入站网关与版本治理
  - [opchub_composable_framework_architecture.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_composable_framework_architecture.md)

---

## 1. 核心需求与设计理念

用户明确提出的架构需求：
> “框架应该支持热重载，检测到新增，修改或者删除 .py 文件框架会感知到，但是不会直接使用，应该跟随版本走加载到内存中，正式生效。”

传统热重载（如 uvicorn `--reload` 或 watchdog 杀进程重启）在长连接、复杂 DAG 算子流水线及分布式 Saga 事务场景下存在致命缺陷（导致正在处理的事务被强杀、连接中断、无法多版本平滑过渡）。
本项目落地 **“版本化微内核动态热装载体系 (Version-Gated Hot Ingestion Architecture)”**：

1. **变动感知（Sensing & Watching）**：
   - 框架内置轻量级跨平台文件监听感知引擎，监控核心业务代码（`src/domains/`、`src/core/` 等）；
   - 感知到 `.py` 文件的增、删、改变动并提取内容指纹（SHA256）；
2. **隔离暂存（Stage & Quarantine）**：
   - **关键准则**：感知到变动后，代码进入 `STAGED`（待发布）状态，**严禁直接覆盖当前正在运行的内存实例**，线上活跃请求继续走稳定运行版本；
3. **版本对齐与元数据提取（Version Association）**：
   - 支持从代码 AST 中静态提取 `__version__` 或 `@versioned` 标识，亦可直接与统一网关声明的版本（如 `v1.0.0`, `v1.1.0`）及场景路由绑定；
4. **受控载入内存与原子生效（Atomic In-Memory Activation）**：
   - 随版本激活指令（如网关重载接口或显式版本激活端点）触发；
   - 执行语法树编译预检，安全清理 `sys.modules` 旧引用，利用 `importlib` 与动态命名空间将新版本逻辑装载至内存；
   - 刷新 `ScenarioRouter` 与微内核 `AtomicRegistry`；若新代码存在语法或导入错误，触发安全熔断保护，旧版内存毫无受损；
   - 记录结构化审计日志并下发已激活状态报表。

---

## 2. 改造方案与实现清单

### ① 微内核版本感知引擎 (`src/core/microkernel/watcher.py`)
- `FileChangeType` 枚举：`ADDED`, `MODIFIED`, `DELETED`；
- `ChangeStatus` 枚举：`DETECTED`, `STAGED`, `ACTIVATED`, `FAILED`；
- `FileChangeRecord` 模型：完整记录文件路径、所属模块、哈希、版本声明、检测与激活时间；
- `VersionedHotReloadEngine` 类：
  - `scan_changes()`：比对本地代码文件修改时间与指纹；
  - `detect_version_from_ast()`：利用 AST 静态解析提取代码文件中的 `__version__` / `__operator_version__`；
  - `activate_version()`：版本激活流水线（语法预检 → 缓存失效 → 模块重新导入 → 路由与算子挂载 → 标记激活）；
  - `get_status()`：向管理层与控制台输出全生命周期感知与加载报表。

### ② 网关配置加载器与路由联动升级 (`config_loader.py` & `main.py`)
- 增强 `_import_symbol` 与 `reload_scenario_routes`：在动态载入时协同版本热加载引擎刷新内存模块；
- 暴露自省管理端点：
  - `GET /api/v1/framework/hot-reload/status`：自省当前感知与版本装载池；
  - `POST /api/v1/framework/hot-reload/scan`：主动触发文件感知；
  - `POST /api/v1/framework/hot-reload/activate`：跟随指定版本将暂存模块正式载入内存生效；
  - `POST /api/welcom/opc_world/reload`：一键联动刷新 YAML 路由与已感知代码模块。

### ③ 自动化测试与验证 (`tests/test_versioned_hot_reload.py`)
- 验证 `.py` 文件变动被准确捕获为 `STAGED`；
- 验证未激活前线上调用维持原内存行为；
- 验证随版本调用 `activate` 后，新代码原子生效；
- 验证语法错误文件被安全拦截，不破坏内存运行态；
- 验证全量 220+ 项回归测试无缝通过。
