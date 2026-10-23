# 架构决策记录 (ADR)：核心开发技术栈与架构模式选型

- **编号**：ADR-001
- **状态**：ACCEPTED
- **日期**：2026-10-16
- **作者**：hardstone & Antigravity

---

## [VIBE_CONTRACT] 架构决策契约 (Machine-Actionable Decision)
```yaml
adr_decision_contract:
  adr_id: "ADR-001"
  status: "ACCEPTED"
  scope: "全仓系统架构 / 核心技术栈"
  locked_decision: "后端采用 Python 3.11+ + FastAPI 构建高性能异步 API-First 架构；前端采用 Vue 3 + Vite 构建轻量多端响应式展示层"

tech_stack_versions:
  backend_runtime: "Python >= 3.11"
  backend_framework: "FastAPI >= 0.110.0"
  backend_asgi: "Uvicorn >= 0.28.0"
  backend_validation: "Pydantic >= 2.6.0"
  frontend_runtime: "Node.js >= 20.x"
  frontend_framework: "Vue 3.4+ (Composition API)"
  frontend_build: "Vite >= 5.x"
  frontend_state: "Pinia >= 2.1"
  frontend_router: "Vue Router >= 4.3"
  frontend_styling: "TailwindCSS >= 3.4 (遵循 /DESIGN.md Anthropic 规范)"

guardrails:
  - "MUST: 后端所有对外接口必须严格遵循 RESTful 规范并由 Pydantic v2 Schema 驱动自动生成 OpenAPI 契约"
  - "MUST: 前端严格定位为'薄前端'，所有核心业务判断、状态机校验、变现规则计算必须全部收敛于后端"
  - "FORBIDDEN: 严禁在前端硬编码政策匹配算法或变现抽成比例"
```

---

## [HUMAN_RATIONALE] 决策背景与多方案论证 (Human Rationale & Options)

### 1. 背景与问题阐述 (Context)
OpcHub 的核心定位是“重后端、薄前端、API-First 多端适配”的一人公司赋能生态平台。后端不仅需要承载常规的用户、社区、订单等业务，更需要承担 AI 政策抓取与结构化清洗（ETL）、LLM 总结、向量匹配算法等重型计算。前端需要轻量、极速响应、并具备向微信小程序、移动端、插件端低成本迁移的能力。

### 2. 备选方案权衡 (Options Considered)

| 维度 | 方案 A：Python (FastAPI) + Vue 3 (最终采纳) | 方案 B：Go (Gin/Fiber) + React | 方案 C：Node.js (NestJS) + Vue 3 |
| :--- | :--- | :--- | :--- |
| **AI/LLM 生态契合度** | **极高**。Python 是全球 AI/数据处理事实标准，与 LangChain、OpenAI/DeepSeek SDK、NumPy 原生无缝集成 | **中**。Go 生态的 AI 工具链较弱，需频繁跨语言调用或自行封装 | **中**。Node.js 在数据分析与本地 Embedding 批量处理上生态逊于 Python |
| **开发效能与单人维护** | **极高**。FastAPI + Pydantic v2 自动生成文档，单人全栈开发心智负担极低 | **中**。Go 语言工程严谨但样板代码多，迭代速度稍慢 | **高**。NestJS 结构重，样板文件多，适合大型企业团队分工 |
| **前端轻量与易维护性** | **Vue 3 极致轻量**。SFC 单文件组件开发敏捷，打包体积小，极易适配小程序与跨端 | React 生态庞大但心智包袱较重（Hooks 闭包与复杂渲染陷阱） | Vue 3 优势相同 |

### 3. 决策结果与详细理由 (Decision & Rationale)
经综合权衡，采纳 **方案 A (Python + FastAPI + Vue 3)**：
1. **Python 生态对 AI 原生支持**：OpcHub 政策中心严重依赖 AI 抓取、大白话提炼与清洗，FastAPI 异步架构能够与 Python 强大的数据/AI 库原生结合；
2. **极速 OpenAPI 契约**：FastAPI 原生生成 OpenAPI (Swagger) 文档，为薄前端（Vue 3）和未来全端（小程序/CLI/插件）提供精确的机器交互契约；
3. **符合一人公司开发心智**：Vue 3 Composition API + Vite 启动与构建秒级完成，大幅降低前端维护开销。
