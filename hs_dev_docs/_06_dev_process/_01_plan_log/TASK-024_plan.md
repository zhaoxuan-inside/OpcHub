# TASK-024 实施计划日志 (Plan Log)

- **任务ID**：TASK-024
- **标题**：SQLite轻量向量检索与RAG引擎实现及政策雷达与互助圈子语义赋能
- **分级**：`M`
- **当前状态**：`IN_PROGRESS`
- **目标**：
  1. 设计并实现零外部重依赖的轻量嵌入与余弦相似度检索模块 (`backend/src/core/rag/`)，支持 SQLite 向量持久化与轻量内存相似度索引。
  2. 实现向量 Embedding 适配器，支持调用 SiliconFlow 真实通用嵌入接口 (`BAAI/bge-large-zh-v1.5` 或 `BAAI/bge-m3`)，并在离线环境提供确定性 TF-IDF/Hash 语义特征降维编码作为 Mock/Fallback 保证系统 100% 独立可用。
  3. 为 P04 政策雷达与 P05 互助圈子提供 RAG 语义混合检索服务 (`PolicyRagService` / `ForumRagService`)。
  4. 在 `gateway_routes.yaml` 中注册 RAG 场景路由 (`external.rag.policy_search`, `external.rag.forum_qa`)。
  5. 在前端单文件控制台 `opchub_all_pages_demo.html` 的 P04 政策雷达与 P05 互助圈子接入交互，严格遵守按钮字数 $\le 4$ 汉字规范（如“语义检索”、“智能问答”）。
  6. 编写全量测试，验证向量检索精准度、混合排序、大模型回答生成及降级容灾，100% 通过测试与一致性门禁。

---

## 执行步骤清单

- [x] **步骤 1**：创建 `backend/src/core/rag/vector_store.py` 与 `backend/src/core/rag/embeddings.py`，实现轻量向量存储、余弦相似度检索与文本分块。
- [x] **步骤 2**：在 `backend/src/infrastructure/external_gateway/ai_gateway.py` 中扩展 SiliconFlow 向量嵌入接口 `get_embeddings()`。
- [x] **步骤 3**：实现 RAG 业务服务层（政策雷达向量混合检索与论坛圈子经验问答与推荐）并在 `backend/src/core/gateway/adapters.py` 实现适配器。
- [x] **步骤 4**：在 `backend/config/gateway_routes.yaml` 注册场景路由 `external.rag.policy_search` 与 `external.rag.forum_qa`。
- [x] **步骤 5**：升级 `opchub_all_pages_demo.html` 中的 P04 政策雷达与 P05 互助圈子前端交互，并同步至 artifact。
- [x] **步骤 6**：编写针对轻量向量引擎与 RAG 链路的单元测试与端到端测试，全量运行 pytest。
- [x] **步骤 7**：执行 `doc_index_db.py` 重建索引与 `verify_consistency.py` 质量门禁，完成任务状态流转与本地 Git 提交。
